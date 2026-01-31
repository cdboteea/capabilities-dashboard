#!/usr/bin/env python3
"""
Twin-Report KB Topic Manager
Central service for managing research topics and coordinating twin report generation
"""

import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import asyncpg
import httpx

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = FastAPI(
    title="Twin-Report KB Topic Manager",
    description="Central service for managing research topics and twin report generation",
    version="1.0.0"
)

# Global database connection pool
db_pool: Optional[asyncpg.Pool] = None

# Data Models
class TopicCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    parent_topic_id: Optional[str] = None
    generation_method: str = Field(default="local", regex="^(api|chat|local|hybrid)$")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TopicResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    parent_topic_id: Optional[str]
    twin_set_id: str
    status: str
    generation_method: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

class ArticleResponse(BaseModel):
    id: str
    topic_id: str
    model_origin: str
    version: int
    title: Optional[str]
    body_md: str
    source_type: str
    word_count: Optional[int]
    created_at: datetime

class TwinReportRequest(BaseModel):
    topic_id: str
    models: List[str] = Field(default=["deepseek-r1", "qwq-32b"])
    max_words: int = Field(default=8000, ge=1000, le=50000)
    include_citations: bool = True

@app.on_event("startup")
async def startup():
    """Initialize database connection pool and services"""
    global db_pool
    
    try:
        postgres_url = os.getenv('POSTGRES_URL')
        if not postgres_url:
            raise ValueError("POSTGRES_URL environment variable not set")
        
        db_pool = await asyncpg.create_pool(
            postgres_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        
        # Test connection
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        logger.info("Topic Manager startup complete")
        
    except Exception as e:
        logger.error("Failed to initialize Topic Manager", error=str(e))
        raise

@app.on_event("shutdown")
async def shutdown():
    """Clean up database connections"""
    global db_pool
    if db_pool:
        await db_pool.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "service": "topic_manager"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.post("/topics", response_model=TopicResponse)
async def create_topic(topic: TopicCreate):
    """Create a new research topic"""
    try:
        topic_id = str(uuid.uuid4())
        twin_set_id = str(uuid.uuid4())
        now = datetime.now()
        
        async with db_pool.acquire() as conn:
            # Verify parent topic exists if specified
            if topic.parent_topic_id:
                parent_exists = await conn.fetchval(
                    "SELECT id FROM twin_report.topics WHERE id = $1",
                    topic.parent_topic_id
                )
                if not parent_exists:
                    raise HTTPException(status_code=404, detail="Parent topic not found")
            
            # Insert new topic
            await conn.execute("""
                INSERT INTO twin_report.topics 
                (id, title, description, parent_topic_id, twin_set_id, 
                 generation_method, created_at, updated_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, topic_id, topic.title, topic.description, topic.parent_topic_id,
                twin_set_id, topic.generation_method, now, now, topic.metadata)
            
            # Fetch the created topic
            row = await conn.fetchrow("""
                SELECT id, title, description, parent_topic_id, twin_set_id, 
                       status, generation_method, created_at, updated_at, metadata
                FROM twin_report.topics WHERE id = $1
            """, topic_id)
        
        logger.info("Topic created", topic_id=topic_id, title=topic.title)
        
        return TopicResponse(**dict(row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create topic", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create topic")

@app.get("/topics", response_model=List[TopicResponse])
async def list_topics(
    parent_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """List topics with optional filtering"""
    try:
        query = """
            SELECT id, title, description, parent_topic_id, twin_set_id, 
                   status, generation_method, created_at, updated_at, metadata
            FROM twin_report.topics
            WHERE 1=1
        """
        params = []
        param_count = 0
        
        if parent_id:
            param_count += 1
            query += f" AND parent_topic_id = ${param_count}"
            params.append(parent_id)
        
        if status:
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(status)
        
        param_count += 1
        query += f" ORDER BY created_at DESC LIMIT ${param_count}"
        params.append(limit)
        
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        return [TopicResponse(**dict(row)) for row in rows]
        
    except Exception as e:
        logger.error("Failed to list topics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list topics")

@app.get("/topics/{topic_id}", response_model=TopicResponse)
async def get_topic(topic_id: str):
    """Get a specific topic by ID"""
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, title, description, parent_topic_id, twin_set_id, 
                       status, generation_method, created_at, updated_at, metadata
                FROM twin_report.topics WHERE id = $1
            """, topic_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        return TopicResponse(**dict(row))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get topic", topic_id=topic_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get topic")

@app.get("/topics/{topic_id}/articles", response_model=List[ArticleResponse])
async def get_topic_articles(topic_id: str):
    """Get all articles for a topic"""
    try:
        async with db_pool.acquire() as conn:
            # Verify topic exists
            topic_exists = await conn.fetchval(
                "SELECT id FROM twin_report.topics WHERE id = $1", topic_id
            )
            if not topic_exists:
                raise HTTPException(status_code=404, detail="Topic not found")
            
            # Get articles
            rows = await conn.fetch("""
                SELECT id, topic_id, model_origin, version, title, body_md,
                       source_type, word_count, created_at
                FROM twin_report.articles 
                WHERE topic_id = $1
                ORDER BY created_at DESC
            """, topic_id)
        
        return [ArticleResponse(**dict(row)) for row in rows]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get topic articles", topic_id=topic_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get topic articles")

@app.post("/topics/{topic_id}/generate-twin-reports")
async def generate_twin_reports(topic_id: str, request: TwinReportRequest, background_tasks: BackgroundTasks):
    """Generate twin reports for a topic using specified models"""
    try:
        # Verify topic exists
        async with db_pool.acquire() as conn:
            topic = await conn.fetchrow(
                "SELECT id, title, generation_method FROM twin_report.topics WHERE id = $1", 
                topic_id
            )
            if not topic:
                raise HTTPException(status_code=404, detail="Topic not found")
        
        # Trigger background generation tasks
        for model in request.models:
            background_tasks.add_task(
                generate_article_task, 
                topic_id, 
                model, 
                topic['title'],
                request.max_words,
                request.include_citations
            )
        
        logger.info("Twin report generation started", 
                   topic_id=topic_id, models=request.models)
        
        return {
            "status": "started",
            "topic_id": topic_id,
            "models": request.models,
            "message": "Twin report generation started in background"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start twin report generation", 
                    topic_id=topic_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start generation")

async def generate_article_task(topic_id: str, model: str, topic_title: str, 
                               max_words: int, include_citations: bool):
    """Background task to generate an article using specified model"""
    try:
        # Get Mac Studio endpoint
        mac_studio_endpoint = os.getenv('MAC_STUDIO_ENDPOINT')
        if not mac_studio_endpoint:
            logger.error("MAC_STUDIO_ENDPOINT not configured")
            return
        
        # Prepare the prompt
        prompt = f"""
        Write a comprehensive research report on: {topic_title}
        
        Requirements:
        - Maximum {max_words} words
        - Include detailed analysis and insights
        - {"Include proper citations and references" if include_citations else "Focus on content without citations"}
        - Use markdown formatting
        - Be thorough and authoritative
        
        Topic: {topic_title}
        """
        
        # Call Mac Studio LLM
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{mac_studio_endpoint}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are an expert researcher and technical writer."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_words * 2,  # Rough token estimation
                    "temperature": 0.3
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Save article to database
                article_id = str(uuid.uuid4())
                word_count = len(content.split())
                now = datetime.now()
                
                async with db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO twin_report.articles 
                        (id, topic_id, model_origin, title, body_md, 
                         source_type, word_count, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """, article_id, topic_id, model, f"{topic_title} - {model}",
                        content, "api", word_count, now, now)
                
                logger.info("Article generated successfully", 
                           topic_id=topic_id, model=model, 
                           article_id=article_id, word_count=word_count)
            else:
                logger.error("Failed to generate article", 
                           topic_id=topic_id, model=model, 
                           status_code=response.status_code)
                
    except Exception as e:
        logger.error("Article generation task failed", 
                    topic_id=topic_id, model=model, error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 