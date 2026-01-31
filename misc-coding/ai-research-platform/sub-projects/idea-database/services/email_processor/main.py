#!/usr/bin/env python3
"""
Email Processing Service - Core Pipeline Orchestrator

📋 PIPELINE REFERENCE: See docs/EMAIL_PROCESSING_PIPELINE.md for complete architecture

This service is the PRIMARY ORCHESTRATOR in the email processing pipeline:
1. Fetches emails from Gmail API with OAuth authentication
2. Calls AI Processor for LLM-based entity extraction
3. Stores emails in source_emails table (modern schema)
4. Manages attachments, URLs, and conversion jobs
5. Provides REST API endpoints for frontend

Architecture Position: Service #1 of 5 in the pipeline
Data Flow: Gmail → Email Processor → AI Processor → Knowledge Graph + Drive Storage
Database Tables: source_emails, attachments, urls, conversion_jobs
External Dependencies: ai_platform_postgres, Mac Studio LLM, Gmail/Drive APIs
"""

import asyncio
import os
import yaml
from pathlib import Path
from typing import Optional, List
from datetime import date

import sys
import logging
import structlog
import json

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import uvicorn

from src.gmail_client import GmailClient
from src.email_parser import EmailParser
from src.database import DatabaseManager
from src.x_api_client import SimpleXAPIClient, QuotaExceededError

logger = structlog.get_logger()

app = FastAPI(title="Idea Database Email Processor", version="1.0.0")

# Global components
gmail_client: Optional[GmailClient] = None
email_parser: Optional[EmailParser] = None
db_manager: Optional[DatabaseManager] = None
config: Optional[dict] = None
# X API
x_api_client: Optional[SimpleXAPIClient] = None

class ProcessingRequest(BaseModel):
    force_reprocess: bool = False
    max_emails: int = 50

@app.on_event("startup")
async def startup():
    """Initialize services on startup"""
    global gmail_client, email_parser, db_manager, config
    
    try:
        # Load configuration
        config_path = Path("/app/config/email_config.yml")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info("Configuration loaded", config_file=str(config_path))
        else:
            logger.warning("Config file not found, using defaults", path=str(config_path))
            config = {
                'email': {
                    'intake_email': 'ideaseea@gmail.com',
                    'processing': {'batch_size': 50}
                }
            }
        
        # Initialize database manager
        postgres_url = os.getenv('POSTGRES_URL')
        if postgres_url:
            db_manager = DatabaseManager(postgres_url)
            await db_manager.initialize()
            logger.info("Database manager initialized")
        else:
            logger.error("POSTGRES_URL environment variable not set")
            return
        
        # Initialize email parser
        email_parser = EmailParser(config, db_manager)
        
        # Initialize Gmail client (will use placeholder config)
        gmail_client = GmailClient(config)

        # Initialize X API client if token present
        x_token = os.getenv("X_BEARER_TOKEN")
        if x_token:
            x_api_client = SimpleXAPIClient(x_token, db_manager)
            logger.info("X API client initialized")
        else:
            logger.warning("X_BEARER_TOKEN not set; X API functionality disabled")
        
        logger.info("Email processor startup complete", 
                   intake_email=config['email']['intake_email'])
        
    except Exception as e:
        logger.error("Failed to initialize email processor", error=str(e))
        raise

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "email_processor",
        "version": "1.0.0",
        "description": "Gmail API integration and email processing for Ideas Database",
        "endpoints": {
            "health": "/health",
            "config": "/config", 
            "process_emails": "/process-emails",
            "stats": "/stats"
        },
        "intake_email": config['email']['intake_email'] if config else "not configured",
        "gmail_ready": gmail_client.has_credentials() if gmail_client else False
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "config_loaded": config is not None,
        "database_connected": db_manager is not None and db_manager.is_connected(),
        "intake_email": config['email']['intake_email'] if config else "unknown"
    }
    
    if not all([config, db_manager]):
        status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=status)
    
    return status

@app.get("/config")
async def get_config():
    """Get current configuration (excluding sensitive data)"""
    if not config:
        raise HTTPException(status_code=500, detail="Configuration not loaded")
    
    safe_config = {
        "intake_email": config['email']['intake_email'],
        "processing_settings": config['email']['processing'],
        "content_types": config['email']['content_types'],
        "categories": list(config['email']['keywords'].keys())
    }
    return safe_config

@app.post("/process-emails")
async def process_emails(request: ProcessingRequest):
    """Process emails from the configured intake account"""
    if not all([gmail_client, email_parser, db_manager]):
        raise HTTPException(status_code=500, detail="Services not initialized")
    
    try:
        # Check if Gmail credentials are available
        if not gmail_client.has_credentials():
            return {
                "status": "skipped",
                "message": "Gmail credentials not configured - email account ready for setup",
                "intake_email": config['email']['intake_email'],
                "next_steps": [
                    "Set up Gmail API credentials for ideaseea@gmail.com",
                    "Configure OAuth2 authentication",
                    "Enable Gmail API in Google Cloud Console"
                ]
            }
        
        # Process emails if credentials are available
        result = await gmail_client.fetch_recent_emails(
            max_emails=request.max_emails,
            force_reprocess=request.force_reprocess
        )
        
        processed_count = 0
        for email_data in result['emails']:
            await email_parser.process_email(email_data, request.force_reprocess, gmail_client)
            processed_count += 1
        
        return {
            "status": "completed",
            "emails_processed": processed_count,
            "total_found": result['total_count'],
            "intake_email": config['email']['intake_email']
        }
        
    except Exception as e:
        logger.error("Email processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/stats")
async def get_processing_stats():
    """Get email processing statistics"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    stats = await db_manager.get_processing_stats()
    return stats

# Frontend API compatibility endpoints
@app.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics (frontend compatibility)"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    stats = await db_manager.get_processing_stats()
    
    # Compute processed_today from recent_activity
    today_str = date.today().isoformat()
    processed_today = 0
    for item in stats.get("recent_activity", []):
        if item["date"] == today_str:
            processed_today = item["count"]
            break

    dashboard_stats = {
        "data": {
            "total_ideas": stats.get("total_ideas", 0),
            "processed_today": processed_today,
            "pending_processing": stats.get("pending_processing", 0),
            "total_entities": stats.get("total_entities", 0),
            "total_urls": stats.get("total_urls", 0),
            "total_attachments": stats.get("total_attachments", 0),
            "avg_processing_time": round(stats.get("avg_processing_time", 0), 2),
            "categories_breakdown": stats.get("categories", {}),
            "recent_activity": stats.get("recent_activity", []),
            "top_domains": stats.get("top_domains", {}),
        }
    }
    return dashboard_stats

@app.get("/ideas")
async def get_ideas(
    page: int = 1, 
    per_page: int = 20, 
    categories: str = None,
    senders: str = None,
    status: str = None,
    start_date: str = None,
    end_date: str = None
):
    """Get paginated ideas with filtering support (frontend compatibility)"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Use the enhanced filtering method
        ideas = await db_manager.get_filtered_ideas(
            entity_types=categories.split(',') if categories else None,  # Note: keeping categories param for compatibility
            senders=senders.split(',') if senders else None,
            status=status.split(',') if status else None,
            start_date=start_date,
            end_date=end_date,
            limit=per_page,
            offset=(page - 1) * per_page
        )
        
        # Transform to frontend expected format
        transformed_ideas = []
        for idea in ideas:
            transformed_ideas.append({
                "id": str(idea["id"]),
                "subject": idea.get("subject", ""),
                "cleaned_content": idea.get("cleaned_content", ""),
                "category": idea.get("category", ""),
                "sender_email": idea.get("sender_email", ""),
                "sender_name": idea.get("sender_name", "") or idea.get("sender_email", "")[: idea.get("sender_email", "").find("<")].strip() if "<" in idea.get("sender_email", "") else idea.get("sender_email", ""),
                "received_date": idea.get("received_date") or idea.get("created_at"),
                "created_at": idea.get("created_at", "").isoformat() if idea.get("created_at") else "",
                "processing_status": "completed",
                "priority_score": 0.8,
                "sentiment_score": 0.2
            })
        
        return {
            "data": {
                "items": transformed_ideas,
                "total": len(transformed_ideas),
                "page": page,
                "per_page": per_page,
                "pages": 1
            }
        }
        
    except Exception as e:
        logger.error("Failed to get ideas", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get ideas: {str(e)}")

@app.post("/search")
async def search_ideas(request: dict):
    """Search ideas with filtering support (frontend compatibility)"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    query = request.get("query", "")
    search_type = request.get("type", "semantic")
    filters = request.get("filters", {})
    page = request.get("page", 1)
    per_page = request.get("per_page", 20)
    
    try:
        if query.strip():
            # Use search with filters
            results = await db_manager.search_ideas_with_filters(
                query=query,
                entity_types=filters.get("entity_types"),
                senders=filters.get("senders"),
                status=filters.get("processing_status"),
                start_date=filters.get("date_range", {}).get("start"),
                end_date=filters.get("date_range", {}).get("end"),
                limit=per_page,
                offset=(page - 1) * per_page
            )
        else:
            # For empty search, use filtered ideas
            results = await db_manager.get_filtered_ideas(
                entity_types=filters.get("entity_types"),
                senders=filters.get("senders"),
                status=filters.get("processing_status"),
                start_date=filters.get("date_range", {}).get("start"),
                end_date=filters.get("date_range", {}).get("end"),
                limit=per_page,
                offset=(page - 1) * per_page
            )
        
        # Transform to frontend expected format
        transformed_results = []
        for result in results:
            transformed_results.append({
                "id": str(result["id"]),
                "subject": result.get("subject", ""),
                "cleaned_content": result.get("cleaned_content", ""),
                "category": result.get("category", ""),
                "sender_email": result.get("sender_email", ""),
                "sender_name": result.get("sender_name", "") or result.get("sender_email", "")[: result.get("sender_email", "").find("<")].strip() if "<" in result.get("sender_email", "") else result.get("sender_email", ""),
                "received_date": result.get("received_date") or result.get("created_at"),
                "created_at": result.get("created_at", "").isoformat() if result.get("created_at") else "",
                "processing_status": "completed",
                "relevance_score": result.get("rank", 1.0) if "rank" in result else 1.0
            })
        
        return {
            "data": {
                "ideas": transformed_results,           # Frontend expects 'ideas'
                "total_count": len(transformed_results), # Frontend expects 'total_count'
                "facets": {                             # Frontend expects facets object
                    "categories": {},
                    "senders": {},
                    "entity_types": {},
                    "domains": {}
                },
                "query_time_ms": 0,                     # Frontend expects query time
                "query": query,
                "type": search_type
            }
        }
        
    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/dashboard/activity")
async def dashboard_activity(limit: int = 20):
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    activities = await db_manager.get_recent_activity(limit)
    return {"data": activities}

@app.get("/processing/timeseries")
async def processing_timeseries(metric: str = 'ideas', period: str = 'day', days: int = 30):
    if metric != 'ideas':
        raise HTTPException(status_code=400, detail="Only ideas metric supported")
    if period != 'day':
        raise HTTPException(status_code=400, detail="Only daily period supported")
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    ts = await db_manager.get_processing_timeseries(days)
    return {"data": ts}

@app.get("/ideas/{idea_id}")
async def get_idea_detail(idea_id: str):
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    idea = await db_manager.get_idea_full(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return {"data": idea}

@app.patch("/ideas/{idea_id}")
async def patch_idea(idea_id: str, payload: dict):
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    allowed_fields = {"category"}
    updates = {k: v for k, v in payload.items() if k in allowed_fields}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    await db_manager.update_idea(idea_id, updates)
    return {"status": "updated"}

@app.delete("/ideas/{idea_id}")
async def delete_idea(idea_id: str):
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    await db_manager.delete_idea(idea_id)
    return {"status": "deleted"}

# New endpoint: attachment metadata/info (JSON only)
@app.get("/attachments/{att_id}/info")
async def get_attachment_info(att_id: str):
    """Return attachment metadata in JSON (no file content)."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")

    query = "SELECT * FROM idea_database.attachments WHERE id = $1"
    async with db_manager.connection_pool.acquire() as conn:
        attachment = await conn.fetchrow(query, att_id)

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Basic guidance message for UI
    note_msg = (
        "File stored in database / Drive. Use the Download button to retrieve the binary content."
    )

    return {
        "status": "success",
        "attachment": {
            "id": str(attachment["id"]),
            "filename": attachment["filename"],
            "file_type": attachment.get("file_type"),
            "file_size": attachment.get("file_size"),
            "storage_type": attachment.get("storage_type"),
            "created_at": attachment.get("created_at"),
        },
        "message": note_msg,
    }

@app.get("/attachments/{att_id}/download")
async def download_attachment(att_id: str):
    """Download attachment file content - tries Gmail first, then Google Drive fallback"""
    if not all([db_manager, gmail_client]):
        raise HTTPException(status_code=500, detail="Services not initialized")
    
    # Get attachment metadata from database
    query = "SELECT * FROM idea_database.attachments WHERE id = $1"
    async with db_manager.connection_pool.acquire() as conn:
        attachment = await conn.fetchrow(query, att_id)
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Try Gmail download first if we have Gmail metadata
    gmail_message_id = attachment.get("gmail_message_id")
    gmail_attachment_id = attachment.get("gmail_attachment_id")
    
    if gmail_message_id and gmail_attachment_id and gmail_client:
        try:
            # Download from Gmail directly
            file_content = await gmail_client.download_gmail_attachment(
                gmail_message_id, gmail_attachment_id
            )
            
            if file_content:
                from fastapi.responses import Response
                return Response(
                    content=file_content,
                    media_type=attachment.get("file_type", "application/octet-stream"),
                    headers={
                        "Content-Disposition": f'attachment; filename="{attachment["filename"]}"',
                        "Content-Length": str(len(file_content))
                    }
                )
        except Exception as e:
            logger.error("Failed to download from Gmail", attachment_id=att_id, error=str(e))
    
    # Fallback: Try Google Drive if we have drive file ID
    drive_file_id = attachment.get("drive_file_id")
    
    if drive_file_id and gmail_client and gmail_client.drive_client:
        try:
            # Download from Google Drive
            file_content = await gmail_client.drive_client.download_file(drive_file_id)
            
            if file_content:
                from fastapi.responses import Response
                return Response(
                    content=file_content,
                    media_type=attachment.get("file_type", "application/octet-stream"),
                    headers={
                        "Content-Disposition": f'attachment; filename="{attachment["filename"]}"',
                        "Content-Length": str(len(file_content))
                    }
                )
        except Exception as e:
            logger.error("Failed to download from Drive", attachment_id=att_id, error=str(e))
    
    # Final fallback: Return metadata (this is what was happening before)
    return {
        "id": str(attachment["id"]),
        "filename": attachment["filename"],
        "file_type": attachment.get("file_type"),
        "file_size": attachment.get("file_size"),
        "created_at": attachment.get("created_at"),
        "storage_type": attachment.get("storage_type", "unknown"),
        "error": "File content not available - neither Gmail nor Drive download succeeded"
    }

# Phase 1: New endpoints for enhanced functionality

@app.get("/attachments/{att_id}/markdown")
async def get_attachment_markdown(att_id: str):
    """Get markdown content of attachment"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    query = "SELECT markdown_content, conversion_status, conversion_error, filename FROM idea_database.attachments WHERE id = $1"
    async with db_manager.connection_pool.acquire() as conn:
        attachment = await conn.fetchrow(query, att_id)
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    if not attachment["markdown_content"]:
        return {
            "status": "no_markdown",
            "conversion_status": attachment.get("conversion_status"),
            "conversion_error": attachment.get("conversion_error"),
            "message": "Markdown content not available"
        }
    
    return {
        "status": "success",
        "filename": attachment["filename"],
        "conversion_status": attachment["conversion_status"],
        "markdown_content": attachment["markdown_content"]
    }

@app.get("/source-emails/{email_id}/urls")
async def get_email_urls(email_id: str):
    """Get all URLs associated with a specific email"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        async with db_manager.connection_pool.acquire() as conn:
            # Verify email exists
            email_check = await conn.fetchrow(
                "SELECT id FROM idea_database.source_emails WHERE id = $1",
                email_id
            )
            
            if not email_check:
                raise HTTPException(status_code=404, detail="Email not found")
            
            # Get URLs for this email
            urls = await conn.fetch("""
                SELECT id, url, domain, title, description, content_type, 
                       fetch_status, word_count, fetch_date, processing_status,
                       markdown_content
                FROM idea_database.urls 
                WHERE source_email_id = $1 
                ORDER BY created_at DESC
            """, email_id)
            
            url_list = []
            for url in urls:
                url_list.append({
                    "id": str(url["id"]),
                    "url": url["url"],
                    "domain": url["domain"],
                    "title": url["title"],
                    "description": url["description"],
                    "content_type": url["content_type"],
                    "fetch_status": url["fetch_status"],
                    "word_count": url["word_count"],
                    "fetch_date": url["fetch_date"].isoformat() if url["fetch_date"] else None,
                    "processing_status": url["processing_status"],
                    "has_content": bool(url["markdown_content"])
                })
            
            return {
                "status": "success",
                "email_id": email_id,
                "urls": url_list,
                "count": len(url_list)
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get email URLs", email_id=email_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get URLs: {str(e)}")

@app.get("/source-emails/{email_id}/attachments")
async def get_email_attachments(email_id: str):
    """Get all attachments associated with a specific email"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        async with db_manager.connection_pool.acquire() as conn:
            # Verify email exists
            email_check = await conn.fetchrow(
                "SELECT id FROM idea_database.source_emails WHERE id = $1",
                email_id
            )
            
            if not email_check:
                raise HTTPException(status_code=404, detail="Email not found")
            
            # Get attachments for this email
            attachments = await conn.fetch("""
                SELECT id, filename, original_filename, file_type, file_size,
                       content_hash, processing_status, conversion_status,
                       storage_type, gmail_message_id, gmail_attachment_id,
                       created_at
                FROM idea_database.attachments 
                WHERE source_email_id = $1 
                ORDER BY created_at DESC
            """, email_id)
            
            attachment_list = []
            for att in attachments:
                attachment_list.append({
                    "id": str(att["id"]),
                    "filename": att["filename"],
                    "original_filename": att["original_filename"],
                    "file_type": att["file_type"],
                    "file_size": att["file_size"],
                    "content_hash": att["content_hash"],
                    "processing_status": att["processing_status"],
                    "conversion_status": att["conversion_status"],
                    "storage_type": att["storage_type"],
                    "gmail_message_id": att["gmail_message_id"],
                    "gmail_attachment_id": att["gmail_attachment_id"],
                    "created_at": att["created_at"].isoformat() if att["created_at"] else None
                })
            
            return {
                "status": "success",
                "email_id": email_id,
                "attachments": attachment_list,
                "count": len(attachment_list)
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get email attachments", email_id=email_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get attachments: {str(e)}")

@app.put("/source-emails/{email_id}/content")
async def update_email_content(email_id: str, content_update: dict):
    """Update the content of a specific email"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    content = content_update.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    try:
        async with db_manager.connection_pool.acquire() as conn:
            # Verify email exists
            email_check = await conn.fetchrow(
                "SELECT id, subject FROM idea_database.source_emails WHERE id = $1",
                email_id
            )
            
            if not email_check:
                raise HTTPException(status_code=404, detail="Email not found")
            
            # Update the cleaned_content field
            await conn.execute("""
                UPDATE idea_database.source_emails 
                SET cleaned_content = $1, updated_at = NOW()
                WHERE id = $2
            """, content, email_id)
            
            return {
                "status": "success",
                "message": "Email content updated successfully",
                "email": {
                    "id": email_id,
                    "subject": email_check["subject"],
                    "cleaned_content": content
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update email content", email_id=email_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update content: {str(e)}")

@app.get("/conversion/stats")
async def get_conversion_stats():
    """Get file conversion and storage statistics"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    stats = await db_manager.get_drive_storage_stats()
    
    return {
        "status": "success",
        "storage_stats": stats,
        "drive_integration": {
            "enabled": gmail_client and gmail_client.drive_client and gmail_client.drive_client.has_credentials(),
            "folder_configured": gmail_client and gmail_client.drive_client and hasattr(gmail_client.drive_client, 'drive_folder_id') and bool(gmail_client.drive_client.drive_folder_id)
        }
    }

@app.get("/conversion/jobs")
async def get_conversion_jobs(limit: int = 20):
    """Get pending conversion jobs"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    jobs = await db_manager.get_pending_conversion_jobs(limit)
    
    return {
        "status": "success", 
        "jobs": jobs,
        "total": len(jobs)
    }

@app.post("/conversion/jobs/{job_id}/retry")
async def retry_conversion_job(job_id: str):
    """Retry a failed conversion job"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Reset job status to pending
    await db_manager.update_conversion_job(job_id, "pending")
    
    return {
        "status": "success",
        "message": f"Conversion job {job_id} marked for retry"
    }

@app.get("/drive/quota")
async def get_drive_quota():
    """Get Google Drive storage quota information"""
    if not gmail_client or not gmail_client.drive_client or not gmail_client.drive_client.has_credentials():
        raise HTTPException(status_code=503, detail="Google Drive not configured")
    
    try:
        quota = await gmail_client.drive_client.get_storage_quota()
        return {
            "status": "success",
            "quota": quota,
            "usage_percentage": (quota["used"] / quota["total"] * 100) if quota["total"] > 0 else 0
        }
    except Exception as e:
        logger.error("Failed to get Drive quota", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get quota: {str(e)}")

@app.post("/drive/upload")
async def upload_to_drive(file: UploadFile = File(...)):
    """Upload file to Google Drive"""
    if not gmail_client or not gmail_client.drive_client or not gmail_client.drive_client.has_credentials():
        raise HTTPException(status_code=503, detail="Google Drive not configured")
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload to Drive
        result = await gmail_client.drive_client.upload_file(
            file_content=file_content,
            filename=file.filename,
            mime_type=file.content_type
        )
        
        if result is None:
            raise HTTPException(status_code=503, detail="Drive upload unavailable - service account lacks storage quota")
        
        return {
            "status": "success",
            "file_id": result.get("file_id"),
            "file_url": result.get("file_url"),
            "filename": file.filename,
            "size": len(file_content)
        }
        
    except Exception as e:
        logger.error("Failed to upload to Drive", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail=f"Drive upload failed: {str(e)}")

@app.post("/gmail/attachment/download-and-upload")
async def download_gmail_attachment_and_upload_to_drive(request: dict):
    """Download attachment from Gmail and upload to Google Drive (for content extractor)"""
    if not all([gmail_client, gmail_client.drive_client]):
        raise HTTPException(status_code=503, detail="Gmail or Drive not configured")
    
    message_id = request.get("message_id")
    attachment_id = request.get("attachment_id") 
    filename = request.get("filename")
    
    if not all([message_id, attachment_id, filename]):
        raise HTTPException(status_code=400, detail="Missing required fields: message_id, attachment_id, filename")
    
    try:
        # Download attachment from Gmail
        file_content = await gmail_client.download_gmail_attachment(message_id, attachment_id)
        
        if not file_content:
            raise HTTPException(status_code=404, detail="Attachment not found in Gmail")
        
        # Upload to Google Drive
        result = await gmail_client.drive_client.upload_file(
            file_content=file_content,
            filename=filename,
            mime_type="application/octet-stream"  # Default MIME type
        )
        
        if not result:
            raise HTTPException(status_code=503, detail="Drive upload failed")
        
        logger.info("Gmail attachment uploaded to Drive", 
                   filename=filename, file_id=result.get("file_id"))
        
        return {
            "status": "success",
            "file_id": result.get("file_id"),
            "file_url": result.get("file_url"),
            "filename": filename,
            "size": len(file_content),
            "content_hash": result.get("content_hash")
        }
        
    except Exception as e:
        logger.error("Failed to download and upload attachment", 
                    message_id=message_id, attachment_id=attachment_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Download and upload failed: {str(e)}")

@app.post("/urls/{url_id}/process")
async def process_url_content(url_id: str):
    """Trigger on-demand URL content processing"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Create conversion job for URL processing
    job_id = await db_manager.create_conversion_job(url_id=url_id, job_type="url_processing")
    
    return {
        "status": "success",
        "message": f"URL processing job created: {job_id}",
        "job_id": job_id
    }

@app.get("/drive/folder-url")
async def get_shared_folder_url():
    """Get the URL to the shared Google Drive folder"""
    if not gmail_client or not gmail_client.drive_client:
        raise HTTPException(status_code=500, detail="Drive client not available")
    
    try:
        folder_url = await gmail_client.drive_client.get_shared_folder_url()
        if not folder_url:
            raise HTTPException(status_code=404, detail="Shared folder not found")
        
        return {
            "folder_url": folder_url,
            "folder_name": gmail_client.drive_client.drive_folder_name,
            "user_email": gmail_client.drive_client.user_email
        }
        
    except Exception as e:
        logger.error("Failed to get shared folder URL", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get folder URL: {str(e)}")

class ShareRequest(BaseModel):
    recipient_email: str = None
    permission: str = "reader"  # reader, commenter, writer
    send_notification: bool = True
    generate_link: bool = False

@app.post("/drive/share/{file_id}")
async def share_file_enhanced(file_id: str, request: ShareRequest):
    """Share a specific Drive file with enhanced options"""
    if not gmail_client or not gmail_client.drive_client:
        raise HTTPException(status_code=500, detail="Drive client not available")
    
    try:
        result = {
            "message": "File shared successfully",
            "file_id": file_id,
            "actions_performed": []
        }
        
        # Share with specific email if provided
        if request.recipient_email:
            success = await gmail_client.drive_client.share_file_with_email(
                file_id, 
                request.recipient_email,
                request.permission,
                request.send_notification
            )
            if not success:
                raise HTTPException(status_code=400, detail="Failed to share file with recipient")
            
            result["actions_performed"].append({
                "action": "shared_with_email",
                "recipient": request.recipient_email,
                "permission": request.permission,
                "notification_sent": request.send_notification
            })
        
        # Generate shareable link if requested
        if request.generate_link:
            link_info = await gmail_client.drive_client.generate_shareable_link(
                file_id,
                request.permission
            )
            if link_info:
                result["shareable_link"] = link_info["link"]
                result["link_permission"] = link_info["permission"]
                result["actions_performed"].append({
                    "action": "generated_link",
                    "permission": request.permission
                })
        
        if not request.recipient_email and not request.generate_link:
            raise HTTPException(status_code=400, detail="Must specify recipient email or generate link")
        
        return result
        
    except Exception as e:
        logger.error("Failed to share file", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to share file: {str(e)}")

@app.get("/drive/sharing-status")
async def get_sharing_status():
    """Get the current sharing status and configuration"""
    if not gmail_client or not gmail_client.drive_client:
        raise HTTPException(status_code=500, detail="Drive client not available")
    
    try:
        auth_info = gmail_client.drive_client.get_auth_info()
        return {
            "sharing_enabled": gmail_client.drive_client.user_email is not None,
            "user_email": gmail_client.drive_client.user_email,
            "folder_name": gmail_client.drive_client.drive_folder_name,
            "folder_id": gmail_client.drive_client.drive_folder_id,
            "has_credentials": gmail_client.drive_client.has_credentials(),
            "auth_method": auth_info.get("auth_method"),
            "oauth_available": auth_info.get("oauth_available"),
            "service_account_available": auth_info.get("service_account_available")
        }
        
    except Exception as e:
        logger.error("Failed to get sharing status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get sharing status: {str(e)}")

@app.delete("/drive/files/{file_id}")
async def delete_drive_file(file_id: str):
    """Delete a specific file from Google Drive"""
    if not gmail_client or not gmail_client.drive_client:
        raise HTTPException(status_code=500, detail="Drive client not available")
    
    try:
        success = await gmail_client.drive_client.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not found or already deleted")
        
        return {
            "status": "success",
            "message": "File deleted successfully",
            "file_id": file_id
        }
        
    except Exception as e:
        logger.error("Failed to delete file", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

# ============================================================================
# NEW ENDPOINTS FOR ENHANCED DASHBOARD FUNCTIONALITY
# ============================================================================

@app.get("/drive/files")
async def list_drive_files(limit: int = 100):
    """List all files in the Google Drive folder"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Get all attachments with Drive file IDs from database
        query = """
            SELECT a.id, a.filename, a.file_type, a.file_size, a.drive_file_id, 
                   a.created_at, se.subject, se.sender_email
            FROM idea_database.attachments a
            LEFT JOIN idea_database.source_emails se ON a.source_email_id = se.id
            WHERE a.drive_file_id IS NOT NULL
            ORDER BY a.created_at DESC
            LIMIT $1
        """
        
        async with db_manager.connection_pool.acquire() as conn:
            files = await conn.fetch(query, limit)
        
        # Format response
        file_list = []
        for file in files:
            file_list.append({
                "id": str(file["id"]),
                "filename": file["filename"],
                "file_type": file.get("file_type"),
                "file_size": file.get("file_size", 0),
                "drive_file_id": file["drive_file_id"],
                "created_at": file["created_at"].isoformat() if file["created_at"] else None,
                "updated_at": file["created_at"].isoformat() if file["created_at"] else None,  # Use created_at for both
                "email_subject": file.get("subject"),
                "email_sender": file.get("sender_email")
            })
        
        return {
            "status": "success",
            "files": file_list,
            "total": len(file_list)
        }
        
    except Exception as e:
        logger.error("Failed to list Drive files", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.get("/drive/files/{file_id}")
async def get_drive_file_details(file_id: str):
    """Get detailed information about a specific Drive file"""
    if not gmail_client or not gmail_client.drive_client:
        raise HTTPException(status_code=500, detail="Drive client not available")
    
    try:
        # Get file metadata from Google Drive
        metadata = await gmail_client.drive_client.get_file_metadata(file_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get database info for this file
        query = """
            SELECT a.id, a.filename, a.file_type, a.file_size, a.conversion_status,
                   a.markdown_content, a.created_at, se.subject, se.sender_email
            FROM idea_database.attachments a
            LEFT JOIN idea_database.source_emails se ON a.source_email_id = se.id
            WHERE a.drive_file_id = $1
        """
        
        async with db_manager.connection_pool.acquire() as conn:
            db_file = await conn.fetchrow(query, file_id)
        
        result = {
            "drive_metadata": metadata,
            "database_info": None
        }
        
        if db_file:
            result["database_info"] = {
                "id": str(db_file["id"]),
                "filename": db_file["filename"],
                "file_type": db_file.get("file_type"),
                "file_size": db_file.get("file_size", 0),
                "conversion_status": db_file.get("conversion_status"),
                "has_markdown": bool(db_file.get("markdown_content")),
                "created_at": db_file["created_at"].isoformat() if db_file["created_at"] else None,
                "email_subject": db_file.get("subject"),
                "email_sender": db_file.get("sender_email")
            }
        
        return {
            "status": "success",
            **result
        }
        
    except Exception as e:
        logger.error("Failed to get file details", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get file details: {str(e)}")

@app.post("/drive/oauth/refresh")
async def refresh_oauth_token():
    """Manually refresh OAuth token"""
    if not gmail_client or not gmail_client.drive_client:
        raise HTTPException(status_code=500, detail="Drive client not available")
    
    try:
        # Try to refresh the OAuth token
        if gmail_client.drive_client.auth_method == 'oauth':
            # Re-initialize OAuth service to trigger refresh
            gmail_client.drive_client._initialize_service()
            
            auth_info = gmail_client.drive_client.get_auth_info()
            
            return {
                "status": "success",
                "message": "OAuth token refreshed successfully",
                "auth_info": auth_info
            }
        else:
            return {
                "status": "warning",
                "message": "Not using OAuth authentication",
                "auth_method": gmail_client.drive_client.auth_method
            }
            
    except Exception as e:
        logger.error("Failed to refresh OAuth token", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to refresh token: {str(e)}")

# URL Management Endpoints
@app.get("/urls")
async def list_urls(limit: int = 100, offset: int = 0):
    """List all URLs from database"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        query = """
            SELECT u.id, u.url, u.title, u.description, u.content_length, 
                   u.processing_status, u.created_at, se.subject, se.sender_email
            FROM idea_database.urls u
            LEFT JOIN idea_database.source_emails se ON u.source_email_id = se.id
            ORDER BY u.created_at DESC
            LIMIT $1 OFFSET $2
        """
        
        count_query = "SELECT COUNT(*) FROM idea_database.urls"
        
        async with db_manager.connection_pool.acquire() as conn:
            urls = await conn.fetch(query, limit, offset)
            total = await conn.fetchval(count_query)
        
        url_list = []
        for url in urls:
            url_list.append({
                "id": str(url["id"]),
                "url": url["url"],
                "title": url.get("title"),
                "description": url.get("description"),
                "content_length": url.get("content_length", 0),
                "processing_status": url.get("processing_status"),
                "created_at": url["created_at"].isoformat() if url["created_at"] else None,
                "email_subject": url.get("subject"),
                "email_sender": url.get("sender_email")
            })
        
        return {
            "status": "success",
            "urls": url_list,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error("Failed to list URLs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list URLs: {str(e)}")

@app.get("/urls/{url_id}")
async def get_url_details(url_id: str):
    """Get detailed information about a specific URL"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        query = """
            SELECT u.*, se.subject, se.sender_email, se.created_at as email_created
            FROM idea_database.urls u
            LEFT JOIN idea_database.source_emails se ON u.source_email_id = se.id
            WHERE u.id = $1
        """
        
        async with db_manager.connection_pool.acquire() as conn:
            url = await conn.fetchrow(query, url_id)
        
        if not url:
            raise HTTPException(status_code=404, detail="URL not found")
        
        return {
            "status": "success",
            "url": {
                "id": str(url["id"]),
                "url": url["url"],
                "title": url.get("title"),
                "description": url.get("description"),
                "content_length": url.get("content_length", 0),
                "processing_status": url.get("processing_status"),
                "markdown_content": url.get("markdown_content"),
                "created_at": url["created_at"].isoformat() if url["created_at"] else None,
                "updated_at": url["updated_at"].isoformat() if url["updated_at"] else None,
                "email_subject": url.get("subject"),
                "email_sender": url.get("sender_email"),
                "email_created": url["email_created"].isoformat() if url["email_created"] else None
            }
        }
        
    except Exception as e:
        logger.error("Failed to get URL details", url_id=url_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get URL details: {str(e)}")

@app.get("/urls/{url_id}/preview")
async def get_url_preview(url_id: str):
    """Generate a preview of URL content"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        query = """
            SELECT url, title, description, markdown_content, content_length
            FROM idea_database.urls
            WHERE id = $1
        """
        
        async with db_manager.connection_pool.acquire() as conn:
            url = await conn.fetchrow(query, url_id)
        
        if not url:
            raise HTTPException(status_code=404, detail="URL not found")
        
        # Generate preview from markdown content
        markdown_content = url.get("markdown_content", "")
        preview = ""
        
        if markdown_content:
            # Take first 500 characters of markdown content
            preview = markdown_content[:500]
            if len(markdown_content) > 500:
                preview += "..."
        
        return {
            "status": "success",
            "preview": {
                "url": url["url"],
                "title": url.get("title"),
                "description": url.get("description"),
                "content_preview": preview,
                "content_length": url.get("content_length", 0),
                "has_full_content": bool(markdown_content)
            }
        }
        
    except Exception as e:
        logger.error("Failed to generate URL preview", url_id=url_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")

# Settings Management Endpoints
@app.get("/settings/categories")
async def get_categories():
    """Get all email categories"""
    try:
        # For now, return hardcoded categories. In future, make this database-driven
        categories = [
            {"id": "personal_thoughts", "name": "Personal Thoughts", "description": "Personal notes and reflections"},
            {"id": "dev_tools", "name": "Dev Tools", "description": "Development tools and resources"},
            {"id": "research_papers", "name": "Research Papers", "description": "Academic papers and research"},
            {"id": "ai_implementations", "name": "AI Implementations", "description": "AI/ML implementations and code"},
            {"id": "industry_news", "name": "Industry News", "description": "News and industry updates"},
            {"id": "reference_materials", "name": "Reference Materials", "description": "Documentation and references"}
        ]
        
        return {
            "status": "success",
            "categories": categories
        }
        
    except Exception as e:
        logger.error("Failed to get categories", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")

@app.get("/settings/models")
async def get_available_models():
    """Get available AI models"""
    try:
        # Return available models from Mac Studio endpoint
        models = [
            {"id": "deepseek-r1", "name": "DeepSeek R1", "description": "Primary reasoning, complex analysis"},
            {"id": "qwen3-32b", "name": "Qwen3 32B", "description": "Multilingual, general purpose"},
            {"id": "qwen2-5", "name": "Qwen 2.5", "description": "Fast inference, general tasks"},
            {"id": "qwen2-5vl", "name": "Qwen 2.5 VL", "description": "Vision + text processing"},
            {"id": "llama4-scout", "name": "Llama4 Scout", "description": "Domain expertise, technical analysis"},
            {"id": "llama4-maverick", "name": "Llama4 Maverick", "description": "Creative research, exploration"}
        ]
        
        return {
            "status": "success",
            "models": models
        }
        
    except Exception as e:
        logger.error("Failed to get available models", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

@app.get("/settings/oauth")
async def get_oauth_status():
    """Get OAuth authentication status for all services"""
    try:
        oauth_status = {
            "gmail": {
                "enabled": gmail_client is not None,
                "configured": gmail_client and gmail_client.service is not None if gmail_client else False,
                "user_email": gmail_client.email_address if gmail_client else None
            },
            "drive": {
                "enabled": gmail_client and gmail_client.drive_client and gmail_client.drive_client.has_credentials(),
                "configured": gmail_client and gmail_client.drive_client and gmail_client.drive_client.service is not None if gmail_client and gmail_client.drive_client else False,
                "user_email": gmail_client.drive_client.user_email if gmail_client and gmail_client.drive_client else None,
                "auth_method": gmail_client.drive_client.auth_method if gmail_client and gmail_client.drive_client else None
            }
        }
        
        return {
            "status": "success",
            "oauth_status": oauth_status
        }
        
    except Exception as e:
        logger.error("Failed to get OAuth status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get OAuth status: {str(e)}")

@app.post("/oauth/refresh/gmail")
async def refresh_gmail_oauth():
    """Refresh Gmail OAuth token"""
    try:
        if not gmail_client:
            raise HTTPException(status_code=503, detail="Gmail client not initialized")
        
        # Attempt to refresh Gmail credentials
        if gmail_client.service:
            # Get current credentials
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            
            token_path = "/app/credentials/gmail_token.json"
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Save refreshed token
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                    logger.info("Gmail OAuth token refreshed successfully")
                    return {"status": "success", "message": "Gmail OAuth token refreshed successfully"}
                else:
                    return {"status": "error", "message": "No valid refresh token available. Manual OAuth flow required."}
            else:
                return {"status": "error", "message": "No Gmail token file found. OAuth setup required."}
        else:
            return {"status": "error", "message": "Gmail service not initialized"}
            
    except Exception as e:
        logger.error("Failed to refresh Gmail OAuth", error=str(e))
        return {"status": "error", "message": f"Failed to refresh Gmail OAuth: {str(e)}"}

@app.post("/oauth/refresh/drive")
async def refresh_drive_oauth():
    """Refresh Google Drive OAuth token"""
    try:
        if not gmail_client or not gmail_client.drive_client:
            raise HTTPException(status_code=503, detail="Drive client not initialized")
        
        # Attempt to refresh Drive credentials
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        
        token_path = "/app/credentials/drive_oauth_token.json"
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/drive.file'])
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                
                # Reinitialize Drive service with new token
                gmail_client.drive_client._initialize_service()
                
                logger.info("Drive OAuth token refreshed successfully")
                return {"status": "success", "message": "Drive OAuth token refreshed successfully"}
            else:
                return {"status": "error", "message": "No valid refresh token available. Manual OAuth flow required."}
        else:
            return {"status": "error", "message": "No Drive token file found. OAuth setup required."}
            
    except Exception as e:
        logger.error("Failed to refresh Drive OAuth", error=str(e))
        return {"status": "error", "message": f"Failed to refresh Drive OAuth: {str(e)}"}


# ============================================================================
# Knowledge Graph Endpoints
# ============================================================================

@app.get("/knowledge-graph")
async def get_knowledge_graph(limit: int = 200):
    """Get knowledge graph data from modern tables"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # MODERN APPROACH: Query knowledge_graph_nodes and knowledge_graph_edges
        nodes_query = """
        SELECT id, name as label, node_type as type, description, properties
        FROM idea_database.knowledge_graph_nodes 
        ORDER BY created_at DESC LIMIT $1
        """
        
        edges_query = """
        SELECT kge.source_node_id as source, kge.target_node_id as target, 
               kge.edge_type as type, kge.weight, kge.context
        FROM idea_database.knowledge_graph_edges kge
        JOIN idea_database.knowledge_graph_nodes src ON kge.source_node_id = src.id
        JOIN idea_database.knowledge_graph_nodes tgt ON kge.target_node_id = tgt.id
        ORDER BY kge.created_at DESC LIMIT $1
        """
        
        async with db_manager.connection_pool.acquire() as conn:
            node_records = await conn.fetch(nodes_query, limit)
            edge_records = await conn.fetch(edges_query, limit)
        
        nodes = [{"id": str(r['id']), "type": r['type'], "label": r['label'], 
                 "description": r.get('description')} for r in node_records]
        edges = [{"source": str(r['source']), "target": str(r['target']), 
                 "type": r['type'], "weight": float(r.get('weight', 1.0))} for r in edge_records]
        
        logger.info("Fetched modern knowledge graph data", 
                   node_count=len(nodes), edge_count=len(edges))
        
        return {"nodes": nodes, "edges": edges}
        
    except Exception as e:
        logger.error("Failed to get modern knowledge graph data", error=str(e))
        
        # FALLBACK TO LEGACY (temporary during transition)
        try:
            logger.info("Attempting fallback to legacy knowledge graph data")
            legacy_data = await db_manager.get_knowledge_graph_data()
            logger.info("Using legacy knowledge graph as fallback", 
                       node_count=len(legacy_data.get("nodes", [])), 
                       edge_count=len(legacy_data.get("edges", [])))
            return legacy_data
        except Exception as fallback_error:
            logger.error("Legacy fallback also failed", error=str(fallback_error))
            raise HTTPException(status_code=500, detail=f"Failed to get knowledge graph: {str(e)}")


class UpdateNodeRequest(BaseModel):
    label: str


@app.put("/knowledge-graph/nodes/{node_id}")
async def update_node_label(node_id: str, request: UpdateNodeRequest):
    """
    Update the label of a node in the knowledge graph.
    Handles different node types by updating the appropriate database table.
    """
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")

    try:
        async with db_manager.connection_pool.acquire() as conn:
            # First, determine what type of node this is by checking each table
            node_info = None
            node_type = None
            
            # Check if it's an idea node
            idea_row = await conn.fetchrow(
                "SELECT id, subject FROM idea_database.ideas WHERE id = $1", 
                node_id
            )
            if idea_row:
                node_info = idea_row
                node_type = 'idea'
            else:
                # Check if it's a URL node
                url_row = await conn.fetchrow(
                    "SELECT id, url FROM idea_database.urls WHERE id = $1", 
                    node_id
                )
                if url_row:
                    node_info = url_row
                    node_type = 'url'
                else:
                    # Check if it's an entity node
                    entity_row = await conn.fetchrow(
                        "SELECT id, entity_value FROM idea_database.entities WHERE id = $1", 
                        node_id
                    )
                    if entity_row:
                        node_info = entity_row
                        node_type = 'entity'
            
            if not node_info:
                raise HTTPException(status_code=404, detail="Node not found")
            
            # Update the appropriate table based on node type
            if node_type == 'idea':
                await conn.execute(
                    "UPDATE idea_database.ideas SET subject = $1 WHERE id = $2",
                    request.label, node_id
                )
                logger.info("Updated idea node label", node_id=node_id, new_label=request.label)
                
            elif node_type == 'url':
                await conn.execute(
                    "UPDATE idea_database.urls SET url = $1 WHERE id = $2",
                    request.label, node_id
                )
                logger.info("Updated URL node label", node_id=node_id, new_label=request.label)
                
            elif node_type == 'entity':
                await conn.execute(
                    "UPDATE idea_database.entities SET entity_value = $1 WHERE id = $2",
                    request.label, node_id
                )
                logger.info("Updated entity node label", node_id=node_id, new_label=request.label)
            
            return {
                "status": "success",
                "node_id": node_id,
                "node_type": node_type,
                "new_label": request.label,
                "message": f"Successfully updated {node_type} node label"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update node label", node_id=node_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Could not update node label: {str(e)}")


# ============================================================================
# X API ENDPOINTS (manual tweet retrieval)
# ============================================================================

class FetchXPostsRequest(BaseModel):
    urls: list[str]


def _parse_tweet_id(url: str) -> Optional[str]:
    """Extract numerical tweet id from a twitter URL."""
    import re
    match = re.search(r"/status/(\d+)", url)
    if not match:
        return None
    
    # Check for query parameters and remove them
    tweet_id_str = match.group(1)
    if '?' in tweet_id_str:
        tweet_id_str = tweet_id_str.split('?')[0]
        
    return tweet_id_str


@app.get("/x-posts/api-usage")
async def get_x_api_usage():
    if not x_api_client:
        raise HTTPException(status_code=503, detail="X API client not configured")
    usage = await x_api_client.get_usage()
    return {"status": "success", **usage}


@app.get("/x-posts")
async def list_x_posts(limit: int = 100, offset: int = 0):
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")

    # ------------------------------------------------------------------
    # 1) Existing fetched tweets from x_posts
    # ------------------------------------------------------------------
    query_existing = """
        SELECT p.tweet_id, p.data, u.url, u.processing_status, u.created_at
        FROM idea_database.x_posts p
        LEFT JOIN idea_database.urls u ON p.url_id = u.id
        ORDER BY p.created_at DESC
        LIMIT $1 OFFSET $2
    """
    count_q = "SELECT COUNT(*) FROM idea_database.x_posts"

    posts: list[dict] = []
    async with db_manager.connection_pool.acquire() as conn:
        existing_rows = await conn.fetch(query_existing, limit, offset)
        total_existing = await conn.fetchval(count_q)

        for r in existing_rows:
            posts.append({
                "tweet_id": str(r[0]) if r[0] else None,
                "url": r[2],
                "processing_status": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
                "data": r[1],
            })

        # ------------------------------------------------------------------
        # 2) Twitter URLs that have NOT yet been fetched (no x_posts record)
        # ------------------------------------------------------------------
        missing_q = """
            SELECT u.url, u.processing_status, u.created_at
            FROM idea_database.urls u
            LEFT JOIN idea_database.x_posts p ON p.url_id = u.id
            WHERE u.url ILIKE 'https://twitter.com/%' AND p.url_id IS NULL
            ORDER BY u.created_at DESC
            LIMIT $1 OFFSET $2
        """
        missing_rows = await conn.fetch(missing_q, limit, offset)

    for r in missing_rows:
        # derive tweet_id (optional) for frontend convenience
        tweet_id_parsed = _parse_tweet_id(r[0])
        posts.append({
            "tweet_id": tweet_id_parsed,
            "url": r[0],
            "processing_status": r[1],
            "created_at": r[2].isoformat() if r[2] else None,
            "data": None,
        })

    # Combine counts (approximate) – existing + missing
    total = len(posts)

    return {"status": "success", "x_posts": posts, "total": total, "limit": limit, "offset": offset}


@app.post("/x-posts/fetch")
async def fetch_x_posts(req: FetchXPostsRequest):
    if not all([db_manager, x_api_client]):
        raise HTTPException(status_code=503, detail="X API not available")

    results = []
    for url in req.urls:
        tweet_id = _parse_tweet_id(url)
        if not tweet_id:
            results.append({"url": url, "status": "invalid_url"})
            continue

        try:
            data = await x_api_client.fetch_tweet(tweet_id)
        except QuotaExceededError:
            raise HTTPException(status_code=429, detail="Monthly X API quota exhausted")
        except Exception as e:
            results.append({"url": url, "status": "error", "message": str(e)})
            continue

        # find corresponding urls.id
        async with db_manager.connection_pool.acquire() as conn:
            url_row = await conn.fetchrow("SELECT id FROM idea_database.urls WHERE url = $1", url)
            if not url_row:
                results.append({"url": url, "status": "not_found_in_db"})
                continue
            url_id = url_row[0]

            # upsert into x_posts
            await conn.execute(
                """
                INSERT INTO idea_database.x_posts (tweet_id, url_id, data)
                VALUES ($1, $2, $3)
                ON CONFLICT (tweet_id) DO UPDATE SET data = EXCLUDED.data
                """,
                int(tweet_id), url_id, data
            )

            # mark url processed
            await conn.execute(
                "UPDATE idea_database.urls SET processing_status='completed', api_used=true WHERE id=$1",
                url_id,
            )

        results.append({"url": url, "status": "fetched"})

    usage = await x_api_client.get_usage()
    return {"status": "success", "results": results, "usage": usage}

@app.post("/database/cleanup")
async def cleanup_database():
    """
    Clean up all email-related data while preserving taxonomy tables.
    
    ⚠️ CRITICAL SAFETY: This endpoint automatically protects taxonomy tables and will NEVER delete:
    - taxonomy_node_types (essential for AI processing)
    - taxonomy_edge_types (essential for knowledge graph)
    
    This operation:
    - Deletes all processed emails, attachments, URLs, entities, and links
    - Preserves the modern 9-node taxonomy system
    - Resets all ID counters for clean reprocessing
    - Returns detailed statistics about what was cleaned
    
    Use this before reprocessing all emails with force_reprocess=true.
    """
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        logger.info("Database cleanup requested")
        
        # Perform the cleanup
        cleanup_stats = await db_manager.cleanup_email_data()
        
        logger.info("Database cleanup completed successfully", **cleanup_stats)
        
        return {
            "success": True,
            "message": "Database cleanup completed successfully",
            "statistics": cleanup_stats,
            "taxonomy_protected": True,
            "next_steps": "Use /process-emails with force_reprocess=true to reprocess all emails"
        }
        
    except Exception as e:
        logger.error("Database cleanup failed", error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Database cleanup failed: {str(e)}"
        )

# ===================================================================
# EMAIL-SPECIFIC KNOWLEDGE GRAPH MANAGEMENT ENDPOINTS (PHASE 2)
# ===================================================================

class EntityCreateRequest(BaseModel):
    name: str
    node_type: str
    description: Optional[str] = ""
    properties: Optional[dict] = {}

class EntityUpdateRequest(BaseModel):
    name: Optional[str] = None
    node_type: Optional[str] = None 
    description: Optional[str] = None
    properties: Optional[dict] = None

class RelationshipCreateRequest(BaseModel):
    source_entity_name: str
    target_entity_name: str
    edge_type: str
    context: Optional[str] = ""
    weight: Optional[float] = 1.0

class RelationshipUpdateRequest(BaseModel):
    edge_type: Optional[str] = None
    context: Optional[str] = None
    weight: Optional[float] = None

class KnowledgeGraphUpdateRequest(BaseModel):
    entities: Optional[List[EntityCreateRequest]] = []
    relationships: Optional[List[RelationshipCreateRequest]] = []
    delete_entity_ids: Optional[List[str]] = []
    delete_relationship_ids: Optional[List[str]] = []

@app.get("/source-emails/{email_id}/knowledge-graph")
async def get_email_knowledge_graph(email_id: str):
    """Get all entities and relationships extracted from a specific email"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        async with db_manager.connection_pool.acquire() as conn:
            # Check if email exists
            email_check = await conn.fetchrow(
                "SELECT id, subject, sender_email FROM idea_database.source_emails WHERE id = $1",
                email_id
            )
            
            if not email_check:
                raise HTTPException(status_code=404, detail="Email not found")
            
            # Get entities for this email
            entities_query = """
                SELECT kgn.id, kgn.name, kgn.node_type, kgn.description, 
                       kgn.properties, kgn.extraction_confidence, kgn.created_at
                FROM idea_database.knowledge_graph_nodes kgn
                WHERE kgn.source_email_id = $1
                ORDER BY kgn.created_at DESC
            """
            
            entities = await conn.fetch(entities_query, email_id)
            
            # Get relationships for this email
            relationships_query = """
                SELECT kge.id, kge.edge_type, kge.weight, kge.context,
                       kge.extraction_confidence, kge.created_at,
                       source_node.name as source_name, source_node.node_type as source_type,
                       target_node.name as target_name, target_node.node_type as target_type
                FROM idea_database.knowledge_graph_edges kge
                JOIN idea_database.knowledge_graph_nodes source_node ON kge.source_node_id = source_node.id
                JOIN idea_database.knowledge_graph_nodes target_node ON kge.target_node_id = target_node.id
                WHERE kge.source_email_id = $1
                ORDER BY kge.created_at DESC
            """
            
            relationships = await conn.fetch(relationships_query, email_id)
        
        # Format entities
        formatted_entities = []
        for entity in entities:
            formatted_entities.append({
                "id": str(entity["id"]),
                "name": entity["name"],
                "type": entity["node_type"],
                "description": entity.get("description", ""),
                "properties": entity.get("properties", {}),
                "confidence": float(entity.get("extraction_confidence", 1.0)),
                "created_at": entity["created_at"].isoformat()
            })
        
        # Format relationships
        formatted_relationships = []
        for rel in relationships:
            formatted_relationships.append({
                "id": str(rel["id"]),
                "source": rel["source_name"],
                "target": rel["target_name"],
                "type": rel["edge_type"],
                "context": rel.get("context", ""),
                "weight": float(rel.get("weight", 1.0)),
                "confidence": float(rel.get("extraction_confidence", 1.0)),
                "created_at": rel["created_at"].isoformat()
            })
        
        return {
            "status": "success",
            "email": {
                "id": email_id,
                "subject": email_check["subject"],
                "sender": email_check["sender_email"]
            },
            "knowledge_graph": {
                "entities": formatted_entities,
                "relationships": formatted_relationships,
                "entity_count": len(formatted_entities),
                "relationship_count": len(formatted_relationships)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get email knowledge graph", email_id=email_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge graph: {str(e)}")

@app.put("/source-emails/{email_id}/knowledge-graph")
async def update_email_knowledge_graph(email_id: str, update_request: KnowledgeGraphUpdateRequest):
    """Update entities and relationships for a specific email"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        async with db_manager.connection_pool.acquire() as conn:
            async with conn.transaction():
                # Verify email exists
                email_check = await conn.fetchrow(
                    "SELECT id FROM idea_database.source_emails WHERE id = $1",
                    email_id
                )
                
                if not email_check:
                    raise HTTPException(status_code=404, detail="Email not found")
                
                results = {
                    "entities_added": 0,
                    "relationships_added": 0,
                    "entities_deleted": 0,
                    "relationships_deleted": 0
                }
                
                # Delete specified entities
                if update_request.delete_entity_ids:
                    for entity_id in update_request.delete_entity_ids:
                        await conn.execute(
                            "DELETE FROM idea_database.knowledge_graph_nodes WHERE id = $1 AND source_email_id = $2",
                            entity_id, email_id
                        )
                        results["entities_deleted"] += 1
                
                # Delete specified relationships
                if update_request.delete_relationship_ids:
                    for rel_id in update_request.delete_relationship_ids:
                        await conn.execute(
                            "DELETE FROM idea_database.knowledge_graph_edges WHERE id = $1 AND source_email_id = $2",
                            rel_id, email_id
                        )
                        results["relationships_deleted"] += 1
                
                # Add new entities
                entity_name_to_id = {}
                if update_request.entities:
                    for entity in update_request.entities:
                        entity_id = await conn.fetchval("""
                            INSERT INTO idea_database.knowledge_graph_nodes 
                            (name, node_type, description, properties, source_email_id, source_id, 
                             source_type, extraction_confidence, created_at, updated_at)
                            VALUES ($1, $2, $3, $4, $5, $6, 'email', 1.0, NOW(), NOW())
                            RETURNING id
                        """, entity.name, entity.node_type, entity.description, 
                             json.dumps(entity.properties), email_id, email_id)
                        
                        entity_name_to_id[entity.name] = entity_id
                        results["entities_added"] += 1
                
                # Get existing entities for relationship creation
                existing_entities = await conn.fetch(
                    "SELECT id, name FROM idea_database.knowledge_graph_nodes WHERE source_email_id = $1",
                    email_id
                )
                
                for entity in existing_entities:
                    entity_name_to_id[entity["name"]] = entity["id"]
                
                # Add new relationships
                if update_request.relationships:
                    for rel in update_request.relationships:
                        source_id = entity_name_to_id.get(rel.source_entity_name)
                        target_id = entity_name_to_id.get(rel.target_entity_name)
                        
                        if source_id and target_id:
                            await conn.execute("""
                                INSERT INTO idea_database.knowledge_graph_edges 
                                (source_node_id, target_node_id, edge_type, weight, context, 
                                 source_email_id, source_id, extraction_confidence, created_at, updated_at)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, 1.0, NOW(), NOW())
                            """, source_id, target_id, rel.edge_type, rel.weight, 
                                 rel.context, email_id, email_id)
                            
                            results["relationships_added"] += 1
                        else:
                            logger.warning("Skipping relationship due to missing entities", 
                                         source=rel.source_entity_name, target=rel.target_entity_name)
        
        return {
            "status": "success",
            "message": "Knowledge graph updated successfully",
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update email knowledge graph", email_id=email_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update knowledge graph: {str(e)}")

@app.post("/source-emails/{email_id}/entities")
async def create_email_entity(email_id: str, entity: EntityCreateRequest):
    """Add a new entity to a specific email"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        async with db_manager.connection_pool.acquire() as conn:
            # Verify email exists
            email_check = await conn.fetchrow(
                "SELECT id FROM idea_database.source_emails WHERE id = $1",
                email_id
            )
            
            if not email_check:
                raise HTTPException(status_code=404, detail="Email not found")
            
            # Create entity
            entity_id = await conn.fetchval("""
                INSERT INTO idea_database.knowledge_graph_nodes 
                (name, node_type, description, properties, source_email_id, source_id, 
                 source_type, extraction_confidence, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, 'email', 1.0, NOW(), NOW())
                RETURNING id
            """, entity.name, entity.node_type, entity.description, 
                 json.dumps(entity.properties), email_id, email_id)
        
        return {
            "status": "success",
            "message": "Entity created successfully",
            "entity": {
                "id": str(entity_id),
                "name": entity.name,
                "type": entity.node_type,
                "description": entity.description,
                "email_id": email_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create entity", email_id=email_id, entity_name=entity.name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create entity: {str(e)}")

@app.put("/entities/{entity_id}")
async def update_entity(entity_id: str, entity_update: EntityUpdateRequest):
    """Update a specific entity"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Build dynamic update query
        update_fields = []
        update_values = []
        param_count = 1
        
        if entity_update.name is not None:
            update_fields.append(f"name = ${param_count}")
            update_values.append(entity_update.name)
            param_count += 1
            
        if entity_update.node_type is not None:
            update_fields.append(f"node_type = ${param_count}")
            update_values.append(entity_update.node_type)
            param_count += 1
            
        if entity_update.description is not None:
            update_fields.append(f"description = ${param_count}")
            update_values.append(entity_update.description)
            param_count += 1
            
        if entity_update.properties is not None:
            update_fields.append(f"properties = ${param_count}")
            update_values.append(json.dumps(entity_update.properties))
            param_count += 1
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_fields.append(f"updated_at = ${param_count}")
        update_values.append("NOW()")
        param_count += 1
        
        update_values.append(entity_id)  # For WHERE clause
        
        query = f"""
            UPDATE idea_database.knowledge_graph_nodes 
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, name, node_type, description, source_email_id
        """
        
        async with db_manager.connection_pool.acquire() as conn:
            # Handle NOW() function properly
            if "NOW()" in update_values:
                now_index = update_values.index("NOW()")
                update_values[now_index] = None
                # Use actual NOW() in query
                query = query.replace(f"${now_index + 1}", "NOW()")
                # Adjust subsequent parameter numbers
                for i in range(now_index + 1, len(update_values)):
                    if update_values[i] is not None:
                        query = query.replace(f"${i + 1}", f"${i}")
                update_values = [v for v in update_values if v is not None]
            
            updated_entity = await conn.fetchrow(query, *update_values)
        
        if not updated_entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        return {
            "status": "success",
            "message": "Entity updated successfully",
            "entity": {
                "id": str(updated_entity["id"]),
                "name": updated_entity["name"],
                "type": updated_entity["node_type"],
                "description": updated_entity["description"],
                "email_id": str(updated_entity["source_email_id"])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update entity", entity_id=entity_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update entity: {str(e)}")

@app.delete("/entities/{entity_id}")
async def delete_entity(entity_id: str):
    """Delete a specific entity"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        async with db_manager.connection_pool.acquire() as conn:
            # Get entity details before deletion
            entity = await conn.fetchrow(
                "SELECT id, name, source_email_id FROM idea_database.knowledge_graph_nodes WHERE id = $1",
                entity_id
            )
            
            if not entity:
                raise HTTPException(status_code=404, detail="Entity not found")
            
            # Delete entity (cascades to relationships)
            await conn.execute(
                "DELETE FROM idea_database.knowledge_graph_nodes WHERE id = $1",
                entity_id
            )
        
        return {
            "status": "success",
            "message": "Entity deleted successfully",
            "deleted_entity": {
                "id": str(entity["id"]),
                "name": entity["name"],
                "email_id": str(entity["source_email_id"])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete entity", entity_id=entity_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete entity: {str(e)}")

@app.post("/source-emails/{email_id}/relationships")
async def create_email_relationship(email_id: str, relationship: RelationshipCreateRequest):
    """Add a new relationship to a specific email"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        async with db_manager.connection_pool.acquire() as conn:
            # Verify email exists
            email_check = await conn.fetchrow(
                "SELECT id FROM idea_database.source_emails WHERE id = $1",
                email_id
            )
            
            if not email_check:
                raise HTTPException(status_code=404, detail="Email not found")
            
            # Get entity IDs
            source_entity = await conn.fetchrow(
                "SELECT id FROM idea_database.knowledge_graph_nodes WHERE name = $1 AND source_email_id = $2",
                relationship.source_entity_name, email_id
            )
            
            target_entity = await conn.fetchrow(
                "SELECT id FROM idea_database.knowledge_graph_nodes WHERE name = $1 AND source_email_id = $2",
                relationship.target_entity_name, email_id
            )
            
            if not source_entity:
                raise HTTPException(status_code=404, detail=f"Source entity '{relationship.source_entity_name}' not found in this email")
            
            if not target_entity:
                raise HTTPException(status_code=404, detail=f"Target entity '{relationship.target_entity_name}' not found in this email")
            
            # Create relationship
            relationship_id = await conn.fetchval("""
                INSERT INTO idea_database.knowledge_graph_edges 
                (source_node_id, target_node_id, edge_type, weight, context, 
                 source_email_id, source_id, extraction_confidence, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, 1.0, NOW(), NOW())
                RETURNING id
            """, source_entity["id"], target_entity["id"], relationship.edge_type, 
                 relationship.weight, relationship.context, email_id, email_id)
        
        return {
            "status": "success",
            "message": "Relationship created successfully",
            "relationship": {
                "id": str(relationship_id),
                "source": relationship.source_entity_name,
                "target": relationship.target_entity_name,
                "type": relationship.edge_type,
                "context": relationship.context,
                "weight": relationship.weight,
                "email_id": email_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create relationship", email_id=email_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create relationship: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    ) 