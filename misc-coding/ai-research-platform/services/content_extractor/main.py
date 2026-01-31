#!/usr/bin/env python3
"""
Content Extractor Service for Ideas Database
Handles URL content extraction, file parsing, and attachment processing
"""

import os
import asyncio
import structlog
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional
import uvicorn
import aiofiles
import tempfile
from pathlib import Path
import asyncpg
import httpx

# Import our file converter
from src.file_converter import FileConverter

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global variables for background tasks
conversion_job_processor = None
polling_task = None
file_converter = None

# Initialize FastAPI app
app = FastAPI(
    title="Content Extractor Service",
    description="URL content extraction and file parsing for Ideas Database",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class URLExtractionRequest(BaseModel):
    url: HttpUrl
    request_id: str
    extract_images: bool = False
    extract_links: bool = True
    max_depth: int = 1

class FileExtractionRequest(BaseModel):
    file_id: str
    file_type: str
    extract_metadata: bool = True

class ExtractionResult(BaseModel):
    request_id: str
    content_type: str
    title: Optional[str] = None
    text_content: str
    metadata: Dict[str, Any]
    images: List[str] = []
    links: List[str] = []
    extraction_status: str
    processing_time: float

class HealthResponse(BaseModel):
    status: str
    polling_active: bool = False

class MarkdownProcessRequest(BaseModel):
    attachment_id: str

class MarkdownProcessAllRequest(BaseModel):
    skip_processed: bool = True

class ConversionJobProcessor:
    """Processes conversion jobs for automatic Drive uploads"""
    
    def __init__(self):
        self.postgres_url = os.getenv('POSTGRES_URL')
        self.email_processor_host = os.getenv('EMAIL_PROCESSOR_HOST', 'idea_db_email_processor')
        self.connection_pool = None
        self.is_running = False
        
    async def start(self):
        """Initialize database connection and start processing"""
        try:
            self.connection_pool = await asyncpg.create_pool(self.postgres_url)
            self.is_running = True
            logger.info("ConversionJobProcessor started")
        except Exception as e:
            logger.error("Failed to start ConversionJobProcessor", error=str(e))
            raise
    
    async def stop(self):
        """Stop processing and close connections"""
        self.is_running = False
        if self.connection_pool:
            await self.connection_pool.close()
        logger.info("ConversionJobProcessor stopped")
    
    async def poll_and_process(self):
        """Main polling loop - checks for pending conversion jobs every 10 seconds"""
        while self.is_running:
            try:
                await self.process_pending_jobs()
                await asyncio.sleep(10)  # Poll every 10 seconds
            except Exception as e:
                logger.error("Error in polling loop", error=str(e))
                await asyncio.sleep(30)  # Wait longer on error
    
    async def process_pending_jobs(self):
        """Process all pending conversion jobs"""
        if not self.connection_pool:
            return
            
        async with self.connection_pool.acquire() as conn:
            # Get pending jobs ordered by priority and creation time
            jobs = await conn.fetch("""
                SELECT id, attachment_id, job_type, retry_count
                FROM idea_database.conversion_jobs 
                WHERE status = 'pending' 
                ORDER BY priority ASC, created_at ASC
                LIMIT 5
            """)
            
            for job in jobs:
                try:
                    await self.process_job(job, conn)
                except Exception as e:
                    logger.error("Failed to process job", job_id=str(job['id']), error=str(e))
                    await self.mark_job_failed(job['id'], str(e), conn)
    
    async def process_job(self, job, conn):
        """Process a single conversion job"""
        job_id = job['id']
        attachment_id = job['attachment_id']
        
        logger.info("Processing conversion job", job_id=str(job_id), attachment_id=str(attachment_id))
        
        # Mark job as processing
        await conn.execute("""
            UPDATE idea_database.conversion_jobs 
            SET status = 'processing', started_at = NOW()
            WHERE id = $1
        """, job_id)
        
        # Get attachment details
        attachment = await conn.fetchrow("""
            SELECT gmail_message_id, gmail_attachment_id, filename, file_type
            FROM idea_database.attachments 
            WHERE id = $1
        """, attachment_id)
        
        if not attachment:
            raise Exception(f"Attachment {attachment_id} not found")
        
        # Download attachment from Gmail and upload to Drive
        result = await self.download_and_upload_to_drive(attachment)
        
        # Update attachment with Drive information
        if result:
            await conn.execute("""
                UPDATE idea_database.attachments 
                SET drive_file_id = $1, drive_file_url = $2, storage_type = 'drive'
                WHERE id = $3
            """, result.get('file_id'), result.get('file_url'), attachment_id)
        
        # Mark job as completed
        await conn.execute("""
            UPDATE idea_database.conversion_jobs 
            SET status = 'completed', completed_at = NOW()
            WHERE id = $1
        """, job_id)
        
        logger.info("Conversion job completed", job_id=str(job_id))
    
    async def download_and_upload_to_drive(self, attachment):
        """Download attachment from Gmail and upload to Drive"""
        try:
            # Call email processor to download from Gmail and upload to Drive
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"http://{self.email_processor_host}:8000/gmail/attachment/download-and-upload",
                    json={
                        "message_id": attachment['gmail_message_id'],
                        "attachment_id": attachment['gmail_attachment_id'],
                        "filename": attachment['filename']
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise Exception(f"Upload failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error("Failed to download and upload attachment", 
                        attachment_id=attachment['gmail_attachment_id'], error=str(e))
            raise
    
    async def mark_job_failed(self, job_id, error_message, conn):
        """Mark job as failed and increment retry count"""
        await conn.execute("""
            UPDATE idea_database.conversion_jobs 
            SET status = 'failed', error_message = $1, retry_count = retry_count + 1
            WHERE id = $2
        """, error_message, job_id)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Content Extractor Service", "status": "running"}

# Health check
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    global conversion_job_processor
    return HealthResponse(
        status="healthy",
        polling_active=conversion_job_processor.is_running if conversion_job_processor else False
    )

# Job status for monitoring
@app.get("/jobs")
async def get_job_status():
    """Get conversion job processing status"""
    global conversion_job_processor
    
    if not conversion_job_processor or not conversion_job_processor.connection_pool:
        return {"status": "not_initialized", "pending_jobs": 0}
    
    try:
        async with conversion_job_processor.connection_pool.acquire() as conn:
            pending_count = await conn.fetchval("""
                SELECT COUNT(*) FROM idea_database.conversion_jobs 
                WHERE status = 'pending'
            """)
            
            processing_count = await conn.fetchval("""
                SELECT COUNT(*) FROM idea_database.conversion_jobs 
                WHERE status = 'processing'
            """)
            
            return {
                "status": "active" if conversion_job_processor.is_running else "stopped",
                "pending_jobs": pending_count,
                "processing_jobs": processing_count
            }
    except Exception as e:
        logger.error("Error getting job status", error=str(e))
        return {"status": "error", "error": str(e)}

# Manual markdown processing endpoints
@app.post("/attachments/{attachment_id}/process-markdown")
async def process_attachment_markdown(attachment_id: str):
    """Manually process a single attachment to markdown"""
    global file_converter, conversion_job_processor
    
    if not file_converter:
        raise HTTPException(status_code=503, detail="File converter not initialized")
    
    if not conversion_job_processor or not conversion_job_processor.connection_pool:
        raise HTTPException(status_code=503, detail="Database connection not available")
    
    try:
        async with conversion_job_processor.connection_pool.acquire() as conn:
            # Get attachment details
            attachment = await conn.fetchrow("""
                SELECT filename, file_type, drive_file_id, drive_file_url, markdown_content
                FROM idea_database.attachments 
                WHERE id = $1
            """, attachment_id)
            
            if not attachment:
                raise HTTPException(status_code=404, detail="Attachment not found")
            
            # Check if already processed
            if attachment['markdown_content']:
                return {
                    "status": "already_processed",
                    "message": "Attachment already has markdown content",
                    "attachment_id": attachment_id
                }
            
            # Download file from Drive
            if not attachment['drive_file_id']:
                raise HTTPException(status_code=400, detail="Attachment not uploaded to Drive yet")
            
            # Download file content via email processor
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"http://{conversion_job_processor.email_processor_host}:8000/attachments/{attachment_id}/download"
                )
                
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail="Failed to download attachment")
                
                file_content = response.content
            
            # Convert to markdown
            result = await file_converter.convert_to_markdown(
                file_content=file_content,
                filename=attachment['filename'],
                mime_type=attachment['file_type']
            )
            
            if result['success']:
                # Update database with markdown content
                await conn.execute("""
                    UPDATE idea_database.attachments 
                    SET markdown_content = $1
                    WHERE id = $2
                """, result['markdown_content'], attachment_id)
                
                logger.info("Attachment processed to markdown", attachment_id=attachment_id)
                
                return {
                    "status": "success",
                    "attachment_id": attachment_id,
                    "markdown_length": len(result['markdown_content']),
                    "metadata": result['metadata']
                }
            else:
                return {
                    "status": "error",
                    "attachment_id": attachment_id,
                    "error": result['error']
                }
                
    except Exception as e:
        logger.error("Error processing attachment markdown", attachment_id=attachment_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/attachments/process-all-markdown")
async def process_all_attachments_markdown(request: MarkdownProcessAllRequest):
    """Process all attachments to markdown (optionally skip already processed)"""
    global file_converter, conversion_job_processor
    
    if not file_converter:
        raise HTTPException(status_code=503, detail="File converter not initialized")
    
    if not conversion_job_processor or not conversion_job_processor.connection_pool:
        raise HTTPException(status_code=503, detail="Database connection not available")
    
    try:
        async with conversion_job_processor.connection_pool.acquire() as conn:
            # Get attachments to process
            if request.skip_processed:
                attachments = await conn.fetch("""
                    SELECT id, filename, file_type, drive_file_id
                    FROM idea_database.attachments 
                    WHERE drive_file_id IS NOT NULL 
                    AND (markdown_content IS NULL OR markdown_content = '')
                    ORDER BY created_at DESC
                """)
            else:
                attachments = await conn.fetch("""
                    SELECT id, filename, file_type, drive_file_id
                    FROM idea_database.attachments 
                    WHERE drive_file_id IS NOT NULL
                    ORDER BY created_at DESC
                """)
            
            results = {
                "processed": 0,
                "errors": 0,
                "skipped": 0,
                "details": []
            }
            
            for attachment in attachments:
                try:
                    # Download and process each attachment
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.get(
                            f"http://{conversion_job_processor.email_processor_host}:8000/attachments/{attachment['id']}/download"
                        )
                        
                        if response.status_code != 200:
                            results["errors"] += 1
                            results["details"].append({
                                "attachment_id": str(attachment['id']),
                                "filename": attachment['filename'],
                                "status": "download_failed"
                            })
                            continue
                        
                        file_content = response.content
                    
                    # Convert to markdown
                    result = await file_converter.convert_to_markdown(
                        file_content=file_content,
                        filename=attachment['filename'],
                        mime_type=attachment['file_type']
                    )
                    
                    if result['success']:
                        # Update database
                        await conn.execute("""
                            UPDATE idea_database.attachments 
                            SET markdown_content = $1
                            WHERE id = $2
                        """, result['markdown_content'], attachment['id'])
                        
                        results["processed"] += 1
                        results["details"].append({
                            "attachment_id": str(attachment['id']),
                            "filename": attachment['filename'],
                            "status": "success",
                            "markdown_length": len(result['markdown_content'])
                        })
                    else:
                        results["errors"] += 1
                        results["details"].append({
                            "attachment_id": str(attachment['id']),
                            "filename": attachment['filename'],
                            "status": "conversion_failed",
                            "error": result['error']
                        })
                        
                except Exception as e:
                    results["errors"] += 1
                    results["details"].append({
                        "attachment_id": str(attachment['id']),
                        "filename": attachment['filename'],
                        "status": "error",
                        "error": str(e)
                    })
            
            logger.info("Bulk markdown processing completed", 
                       processed=results["processed"], 
                       errors=results["errors"])
            
            return results
            
    except Exception as e:
        logger.error("Error in bulk markdown processing", error=str(e))
        raise HTTPException(status_code=500, detail=f"Bulk processing failed: {str(e)}")

@app.get("/attachments/{attachment_id}/markdown")
async def get_attachment_markdown(attachment_id: str):
    """Get processed markdown content for an attachment"""
    global conversion_job_processor
    
    if not conversion_job_processor or not conversion_job_processor.connection_pool:
        raise HTTPException(status_code=503, detail="Database connection not available")
    
    try:
        async with conversion_job_processor.connection_pool.acquire() as conn:
            attachment = await conn.fetchrow("""
                SELECT filename, markdown_content
                FROM idea_database.attachments 
                WHERE id = $1
            """, attachment_id)
            
            if not attachment:
                raise HTTPException(status_code=404, detail="Attachment not found")
            
            if not attachment['markdown_content']:
                raise HTTPException(status_code=404, detail="Markdown content not available")
            
            return {
                "attachment_id": attachment_id,
                "filename": attachment['filename'],
                "markdown_content": attachment['markdown_content'],
                "content_length": len(attachment['markdown_content'])
            }
            
    except Exception as e:
        logger.error("Error getting attachment markdown", attachment_id=attachment_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get markdown: {str(e)}")

# URL extraction endpoints (existing)
@app.post("/extract/url", response_model=ExtractionResult)
async def extract_url(request: URLExtractionRequest):
    """Extract content from a URL"""
    global file_converter
    
    if not file_converter:
        raise HTTPException(status_code=503, detail="File converter not initialized")
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Call the file converter to extract content from the URL
        result = await file_converter.extract_from_url(
            url=request.url,
            request_id=request.request_id,
            extract_images=request.extract_images,
            extract_links=request.extract_links,
            max_depth=request.max_depth
        )
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        return ExtractionResult(
            request_id=request.request_id,
            content_type=result['content_type'],
            title=result['title'],
            text_content=result['text_content'],
            metadata=result['metadata'],
            images=result['images'],
            links=result['links'],
            extraction_status="completed",
            processing_time=processing_time
        )
    except Exception as e:
        logger.error("Error extracting URL content", request_id=request.request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"URL extraction failed: {str(e)}")

# File extraction endpoints (existing)
@app.post("/extract/file", response_model=ExtractionResult)
async def extract_file(request: FileExtractionRequest):
    """Extract content from a file attachment"""
    global file_converter
    
    if not file_converter:
        raise HTTPException(status_code=503, detail="File converter not initialized")
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Call the file converter to extract content from the file attachment
        result = await file_converter.extract_from_file(
            file_id=request.file_id,
            file_type=request.file_type,
            extract_metadata=request.extract_metadata
        )
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        return ExtractionResult(
            request_id=request.file_id, # Assuming file_id is the request_id for file extraction
            content_type=result['content_type'],
            title=result['title'],
            text_content=result['text_content'],
            metadata=result['metadata'],
            images=result['images'],
            links=result['links'],
            extraction_status="completed",
            processing_time=processing_time
        )
    except Exception as e:
        logger.error("Error extracting file content", file_id=request.file_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"File extraction failed: {str(e)}")

# List supported file types
@app.get("/supported-types")
async def get_supported_types():
    """Get list of supported file types for extraction"""
    return {
        "document_types": ["pdf", "docx", "txt", "md", "rtf"],
        "spreadsheet_types": ["xlsx", "csv", "ods"],
        "presentation_types": ["pptx", "odp"],
        "image_types": ["jpg", "jpeg", "png", "gif", "bmp", "tiff"],
        "web_types": ["html", "xml", "json"],
        "archive_types": ["zip", "tar", "gz"]
    }

@app.on_event("startup")
async def startup_event():
    """Initialize conversion job processor on startup"""
    global conversion_job_processor, polling_task, file_converter
    
    # Initialize file converter
    file_converter = FileConverter()
    
    # Initialize conversion job processor
    conversion_job_processor = ConversionJobProcessor()
    await conversion_job_processor.start()
    
    # Start background polling task
    polling_task = asyncio.create_task(conversion_job_processor.poll_and_process())
    logger.info("Background conversion job polling started")

@app.on_event("shutdown") 
async def shutdown_event():
    """Clean shutdown of conversion job processor"""
    global conversion_job_processor, polling_task
    
    if conversion_job_processor:
        await conversion_job_processor.stop()
    
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    
    logger.info("Content Extractor service shut down")

if __name__ == "__main__":
    port = int(os.getenv("CONTENT_EXTRACTOR_PORT", 8000))
    logger.info("Starting Content Extractor Service", port=port)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_config=None  # Use structlog instead
    ) 