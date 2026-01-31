#!/usr/bin/env python3
"""
Document Parser - Twin-Report KB
Multi-format document parsing and content extraction service
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog
import uvicorn

from src.database import DatabaseManager
from src.pdf_parser import PDFParser
from src.google_docs_parser import GoogleDocsParser
from src.web_parser import WebParser
from src.chat_parser import ChatParser
from src.office_parser import OfficeParser
from src.content_normalizer import ContentNormalizer
from src.metadata_extractor import MetadataExtractor

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
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Pydantic models
class DocumentParseRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL to parse (for web documents)")
    google_doc_id: Optional[str] = Field(None, description="Google Docs document ID")
    content_type: str = Field(..., description="Type of content: pdf, docx, url, google_doc, chat_export")
    extraction_options: Dict[str, Any] = Field(default={}, description="Parsing options")

class DocumentParseResponse(BaseModel):
    document_id: str = Field(..., description="Unique document identifier")
    content_type: str = Field(..., description="Detected content type")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Extracted text content")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    structure: Dict[str, Any] = Field(..., description="Document structure information")
    extraction_stats: Dict[str, Any] = Field(..., description="Extraction statistics")
    processing_time: float = Field(..., description="Processing time in seconds")

class BatchParseRequest(BaseModel):
    documents: List[DocumentParseRequest] = Field(..., description="Documents to parse")
    batch_options: Dict[str, Any] = Field(default={}, description="Batch processing options")

# Global instances
db_manager: Optional[DatabaseManager] = None
pdf_parser: Optional[PDFParser] = None
google_docs_parser: Optional[GoogleDocsParser] = None
web_parser: Optional[WebParser] = None
chat_parser: Optional[ChatParser] = None
office_parser: Optional[OfficeParser] = None
content_normalizer: Optional[ContentNormalizer] = None
metadata_extractor: Optional[MetadataExtractor] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_manager, pdf_parser, google_docs_parser, web_parser, chat_parser, office_parser, content_normalizer, metadata_extractor
    
    logger.info("Starting Document Parser service")
    
    # Initialize database
    postgres_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL", "postgresql://twin_report:secure_password@postgres:5432/twin_report_kb")
    db_manager = DatabaseManager(postgres_url)
    await db_manager.initialize()
    
    # Initialize parsers
    pdf_parser = PDFParser()
    google_docs_parser = GoogleDocsParser()
    web_parser = WebParser()
    chat_parser = ChatParser()
    office_parser = OfficeParser()
    content_normalizer = ContentNormalizer()
    metadata_extractor = MetadataExtractor()
    
    logger.info("Document Parser service initialized")
    
    yield
    
    logger.info("Shutting down Document Parser service")
    if db_manager:
        await db_manager.close()

# Create FastAPI app
app = FastAPI(
    title="Document Parser",
    description="Twin-Report KB Document Parsing Service",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "document_parser",
        "components": {
            "database": "connected" if db_manager else "disconnected",
            "parsers": {
                "pdf": "ready" if pdf_parser else "not_ready",
                "google_docs": "ready" if google_docs_parser else "not_ready",
                "web": "ready" if web_parser else "not_ready",
                "chat": "ready" if chat_parser else "not_ready",
                "office": "ready" if office_parser else "not_ready"
            }
        }
    }

@app.post("/parse/upload", response_model=DocumentParseResponse)
async def parse_uploaded_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    extraction_options: str = Form(default="{}")
):
    """Parse an uploaded document file"""
    
    logger.info("File upload requested", 
               filename=file.filename,
               content_type=file.content_type)
    
    try:
        import json
        options = json.loads(extraction_options)
        
        start_time = asyncio.get_event_loop().time()
        
        # Determine content type
        content_type = _detect_content_type(file.filename, file.content_type)
        
        # Read file content
        file_content = await file.read()
        
        # Parse based on content type
        if content_type == "pdf":
            result = await pdf_parser.parse(file_content, options)
        elif content_type in ["docx", "xlsx", "pptx"]:
            result = await office_parser.parse(file_content, content_type, options)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")
        
        # Normalize content
        normalized_content = await content_normalizer.normalize(result["content"], content_type)
        
        # Extract metadata
        metadata = await metadata_extractor.extract(file_content, content_type, result.get("metadata", {}))
        
        # Generate document ID
        document_id = await _generate_document_id(file.filename, file_content)
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        response = DocumentParseResponse(
            document_id=document_id,
            content_type=content_type,
            title=result.get("title", file.filename),
            content=normalized_content,
            metadata=metadata,
            structure=result.get("structure", {}),
            extraction_stats=result.get("stats", {}),
            processing_time=processing_time
        )
        
        # Store in database
        background_tasks.add_task(store_parsed_document, response.dict())
        
        logger.info("File parsing completed",
                   document_id=document_id,
                   content_type=content_type,
                   processing_time=processing_time)
        
        return response
        
    except Exception as e:
        logger.error("File parsing failed", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")

@app.post("/parse/url", response_model=DocumentParseResponse)
async def parse_url(request: DocumentParseRequest, background_tasks: BackgroundTasks):
    """Parse a document from URL"""
    
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    logger.info("URL parsing requested", url=request.url)
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Parse web content
        result = await web_parser.parse(request.url, request.extraction_options)
        
        # Normalize content
        normalized_content = await content_normalizer.normalize(result["content"], "web")
        
        # Extract metadata
        metadata = await metadata_extractor.extract_from_url(request.url, result.get("metadata", {}))
        
        # Generate document ID
        document_id = await _generate_document_id(request.url)
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        response = DocumentParseResponse(
            document_id=document_id,
            content_type="web",
            title=result.get("title", "Web Document"),
            content=normalized_content,
            metadata=metadata,
            structure=result.get("structure", {}),
            extraction_stats=result.get("stats", {}),
            processing_time=processing_time
        )
        
        # Store in database
        background_tasks.add_task(store_parsed_document, response.dict())
        
        logger.info("URL parsing completed",
                   document_id=document_id,
                   url=request.url,
                   processing_time=processing_time)
        
        return response
        
    except Exception as e:
        logger.error("URL parsing failed", url=request.url, error=str(e))
        raise HTTPException(status_code=500, detail=f"URL parsing failed: {str(e)}")

@app.post("/parse/google-doc", response_model=DocumentParseResponse)
async def parse_google_doc(request: DocumentParseRequest, background_tasks: BackgroundTasks):
    """Parse a Google Docs document"""
    
    if not request.google_doc_id:
        raise HTTPException(status_code=400, detail="Google Doc ID is required")
    
    logger.info("Google Doc parsing requested", doc_id=request.google_doc_id)
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Parse Google Doc
        result = await google_docs_parser.parse(request.google_doc_id, request.extraction_options)
        
        # Normalize content
        normalized_content = await content_normalizer.normalize(result["content"], "google_doc")
        
        # Extract metadata
        metadata = await metadata_extractor.extract_from_google_doc(request.google_doc_id, result.get("metadata", {}))
        
        # Generate document ID
        document_id = await _generate_document_id(f"google_doc_{request.google_doc_id}")
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        response = DocumentParseResponse(
            document_id=document_id,
            content_type="google_doc",
            title=result.get("title", "Google Doc"),
            content=normalized_content,
            metadata=metadata,
            structure=result.get("structure", {}),
            extraction_stats=result.get("stats", {}),
            processing_time=processing_time
        )
        
        # Store in database
        background_tasks.add_task(store_parsed_document, response.dict())
        
        logger.info("Google Doc parsing completed",
                   document_id=document_id,
                   doc_id=request.google_doc_id,
                   processing_time=processing_time)
        
        return response
        
    except Exception as e:
        logger.error("Google Doc parsing failed", doc_id=request.google_doc_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Google Doc parsing failed: {str(e)}")

@app.post("/parse/batch")
async def parse_batch(request: BatchParseRequest, background_tasks: BackgroundTasks):
    """Parse multiple documents in batch"""
    
    logger.info("Batch parsing requested", document_count=len(request.documents))
    
    try:
        # Process batch in background
        background_tasks.add_task(process_batch_parsing, request.documents, request.batch_options)
        
        return {
            "status": "accepted",
            "message": f"Batch processing started for {len(request.documents)} documents",
            "document_count": len(request.documents)
        }
        
    except Exception as e:
        logger.error("Batch parsing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch parsing failed: {str(e)}")

@app.get("/document/{document_id}")
async def get_parsed_document(document_id: str):
    """Get parsed document by ID"""
    
    try:
        document = await db_manager.get_parsed_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return document
        
    except Exception as e:
        logger.error("Failed to retrieve document", document_id=document_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {str(e)}")

@app.get("/documents")
async def list_parsed_documents(
    limit: int = 50,
    offset: int = 0,
    content_type: Optional[str] = None
):
    """List parsed documents"""
    
    try:
        documents = await db_manager.list_parsed_documents(limit, offset, content_type)
        return {
            "documents": documents,
            "limit": limit,
            "offset": offset,
            "content_type": content_type
        }
        
    except Exception as e:
        logger.error("Failed to list documents", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

def _detect_content_type(filename: str, mime_type: str) -> str:
    """Detect content type from filename and MIME type"""
    
    if filename:
        ext = filename.lower().split('.')[-1]
        if ext == 'pdf':
            return 'pdf'
        elif ext in ['doc', 'docx']:
            return 'docx'
        elif ext in ['xls', 'xlsx']:
            return 'xlsx'
        elif ext in ['ppt', 'pptx']:
            return 'pptx'
        elif ext in ['txt', 'md']:
            return 'text'
    
    if mime_type:
        if 'pdf' in mime_type:
            return 'pdf'
        elif 'word' in mime_type or 'document' in mime_type:
            return 'docx'
        elif 'sheet' in mime_type:
            return 'xlsx'
        elif 'presentation' in mime_type:
            return 'pptx'
    
    return 'unknown'

async def _generate_document_id(identifier: str, content: bytes = None) -> str:
    """Generate unique document ID"""
    import hashlib
    
    if content:
        content_hash = hashlib.sha256(content).hexdigest()[:16]
        return f"doc_{content_hash}_{int(datetime.now().timestamp())}"
    else:
        identifier_hash = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"doc_{identifier_hash}_{int(datetime.now().timestamp())}"

async def store_parsed_document(document_data: Dict[str, Any]):
    """Store parsed document in database"""
    try:
        await db_manager.store_parsed_document(document_data)
        logger.info("Parsed document stored", document_id=document_data.get("document_id"))
    except Exception as e:
        logger.error("Failed to store parsed document", error=str(e))

async def process_batch_parsing(documents: List[DocumentParseRequest], options: Dict[str, Any]):
    """Process batch document parsing"""
    try:
        results = []
        for doc_request in documents:
            try:
                # Process each document based on type
                if doc_request.url:
                    result = await web_parser.parse(doc_request.url, doc_request.extraction_options)
                elif doc_request.google_doc_id:
                    result = await google_docs_parser.parse(doc_request.google_doc_id, doc_request.extraction_options)
                
                results.append(result)
                
            except Exception as e:
                logger.error("Batch document parsing failed", error=str(e))
                results.append({"error": str(e)})
        
        # Store batch results
        await db_manager.store_batch_results(results, options)
        logger.info("Batch parsing completed", document_count=len(documents), success_count=len([r for r in results if "error" not in r]))
        
    except Exception as e:
        logger.error("Batch processing failed", error=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 