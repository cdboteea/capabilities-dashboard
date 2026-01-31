#!/usr/bin/env python3
"""
AI Processor Service - LLM Entity Extraction & Knowledge Graph Generation

📋 PIPELINE REFERENCE: See docs/EMAIL_PROCESSING_PIPELINE.md for complete architecture

This service handles the CORE AI PROCESSING in the email pipeline:
1. Receives email content from Email Processor
2. Calls Mac Studio LLM endpoint (llama4:scout) for entity extraction
3. Parses LLM JSON response into structured entities and relationships
4. Stores data in knowledge_graph_nodes and knowledge_graph_edges tables
5. Updates source_emails processing status to 'completed'

Architecture Position: Service #2 of 5 in the pipeline
Data Flow: Email Processor → AI Processor → Mac Studio LLM → Knowledge Graph Storage
Database Tables: source_emails, knowledge_graph_nodes, knowledge_graph_edges
LLM Integration: http://192.168.1.50:8182/api/chat (Mac Studio)
"""

import os
import asyncio
import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, cast
import uvicorn
import json
import redis.asyncio as aioredis
import openai
import asyncpg

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

# Initialize FastAPI app
app = FastAPI(
    title="AI Processor Service",
    description="Entity extraction and AI-powered analysis for Ideas Database",
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
class EmailContent(BaseModel):
    email_id: str
    subject: str
    body: str
    sender: str
    timestamp: str
    attachments: Optional[List[str]] = []

class ProcessingResult(BaseModel):
    email_id: str
    entities: List[Dict[str, Any]]
    categories: List[str]
    sentiment: Dict[str, float]
    priority_score: float
    processing_status: str

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

# Global database pool
db_pool: Optional[asyncpg.Pool] = None

# Redis and LLM config from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://idea_db_redis:6379/0")
REDIS_EVENTS_CHANNELS = ["idea.preprocessed", "idea.chunked"]
REDIS_OUTPUT_CHANNEL = "idea.extracted"
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://matiass-mac-studio.tail174e9b.ts.net/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-local")
LLM_MODEL = os.getenv("LLM_MODEL", "llama4:scout")

openai_client = openai.AsyncOpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_API_BASE
)

async def fetch_taxonomy_from_db():
    """Fetch taxonomy from database and build prompt section."""
    try:
        async with db_pool.acquire() as conn:
            # Fetch node types
            node_rows = await conn.fetch("SELECT name, definition FROM idea_database.taxonomy_node_types ORDER BY name")
            # Fetch edge types  
            edge_rows = await conn.fetch("SELECT name, definition FROM idea_database.taxonomy_edge_types ORDER BY name")
            
            node_lines = [f"- {row['name']}: {row['definition']}" for row in node_rows]
            edge_lines = [f"- {row['name']}: {row['definition']}" for row in edge_rows]
            
            taxonomy_section = (
                "Node types (use ONLY these):\n" + "\n".join(node_lines) +
                "\n\nEdge types (use ONLY these):\n" + "\n".join(edge_lines)
            )
            return taxonomy_section
    except Exception as e:
        logger.error("Failed to fetch taxonomy from database", error=str(e))
        # Fallback to basic taxonomy
        return "Node types: idea, evidence, method, metric, person, organization, concept, technology, event\nEdge types: is-a, part-of, supports, contradicts, related-to"

async def get_valid_taxonomy_types():
    """Get valid node and edge types for validation"""
    try:
        async with db_pool.acquire() as conn:
            node_rows = await conn.fetch("SELECT name FROM idea_database.taxonomy_node_types")
            edge_rows = await conn.fetch("SELECT name FROM idea_database.taxonomy_edge_types")
            
            node_types = set(row['name'].lower() for row in node_rows)
            edge_types = set(row['name'].lower() for row in edge_rows)
            
            return node_types, edge_types
    except Exception as e:
        logger.error("Failed to get taxonomy types", error=str(e))
        return set(), set()

async def extract_with_llm(text: str, retry_on_noncompliance: bool = True) -> dict:
    """Call LLM endpoint to extract entities/edges per taxonomy, with compliance correction."""
    import copy
    
    # Fetch current taxonomy from database
    taxonomy_prompt_section = await fetch_taxonomy_from_db()
    
    prompt = f"""
You are an expert information extractor. Use ONLY the node and edge types and definitions provided below. If you are unsure, do NOT output a node/edge. Any type not listed will be ignored.

{taxonomy_prompt_section}

Extract all entities and relationships from the following text using ONLY the provided node and edge types. Return a JSON object with 'nodes' and 'edges'.

For nodes, include: {{"name": "entity name", "type": "node_type", "description": "brief description"}}
For edges, include: {{"source": "source_node_name", "target": "target_node_name", "type": "edge_type", "context": "brief context"}}

Text:
{text}
"""
    try:
        response = await openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": "You are an expert information extractor. Return only valid JSON."},
                      {"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1024
        )
        content = response.choices[0].message.content
        logger.info("LLM raw response", content=content)
        
        # Extract JSON from markdown code blocks - handle multiple blocks
        import re
        json_blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        
        if json_blocks:
            # Use the last JSON block (most refined version)
            cleaned_content = json_blocks[-1].strip()
        else:
            # Fallback: try to extract first JSON object directly
            cleaned_content = content.strip()
            # Remove any leading/trailing text and find the JSON
            json_match = re.search(r'(\{.*\})', cleaned_content, re.DOTALL)
            if json_match:
                cleaned_content = json_match.group(1)
        
        result = json.loads(cleaned_content)
        
        # --- Compliance check using database taxonomy ---
        node_types, edge_types = await get_valid_taxonomy_types()
        noncompliant_nodes = [n for n in result.get('nodes', []) if n.get('type', '').lower() not in node_types]
        noncompliant_edges = [e for e in result.get('edges', []) if e.get('type', '').lower() not in edge_types]
        
        if (noncompliant_nodes or noncompliant_edges) and retry_on_noncompliance:
            logger.warning("LLM returned non-compliant types, retrying", 
                          noncompliant_nodes=noncompliant_nodes, 
                          noncompliant_edges=noncompliant_edges)
            # Retry once with stricter prompt
            return await extract_with_llm(text, retry_on_noncompliance=False)
        
        # Filter out non-compliant types
        valid_nodes = [n for n in result.get('nodes', []) if n.get('type', '').lower() in node_types]
        valid_edges = [e for e in result.get('edges', []) if e.get('type', '').lower() in edge_types]
        
        logger.info("LLM extraction completed", 
                   nodes_extracted=len(valid_nodes), 
                   edges_extracted=len(valid_edges),
                   nodes_filtered=len(result.get('nodes', [])) - len(valid_nodes),
                   edges_filtered=len(result.get('edges', [])) - len(valid_edges))
        
        return {"nodes": valid_nodes, "edges": valid_edges}
        
    except json.JSONDecodeError as e:
        logger.error("LLM returned invalid JSON", error=str(e), content=content)
        return {"nodes": [], "edges": []}
    except Exception as e:
        logger.error("LLM extraction failed", error=str(e))
        return {"nodes": [], "edges": []}

async def store_knowledge_graph_data(email_id: str, llm_result: dict, email_content: EmailContent):
    """Store extracted nodes and edges in modern knowledge graph tables"""
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # 1. Store email in source_emails if not exists
                source_email_id = await conn.fetchval("""
                    INSERT INTO idea_database.source_emails 
                    (gmail_message_id, subject, sender_email, sender_name, received_date, 
                     original_content, cleaned_content, processing_status, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, NOW(), $5, $6, 'processing', NOW(), NOW())
                    ON CONFLICT (gmail_message_id) DO UPDATE SET 
                        processing_status = 'processing',
                        updated_at = NOW()
                    RETURNING id
                """, email_id, email_content.subject, email_content.sender, 
                     email_content.sender, email_content.body, email_content.body)
                
                # 2. Store knowledge graph nodes
                node_ids = {}
                for node in llm_result.get("nodes", []):
                    node_id = await conn.fetchval("""
                        INSERT INTO idea_database.knowledge_graph_nodes 
                        (name, node_type, description, properties, source_id, source_email_id, source_type, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, 'email', NOW(), NOW())
                        ON CONFLICT DO NOTHING
                        RETURNING id
                    """, node["name"], node["type"].lower(), node.get("description", ""), 
                         json.dumps(node.get("properties", {})), source_email_id, source_email_id)
                    
                    if node_id:
                        node_ids[node["name"]] = node_id
                        logger.info("Stored knowledge graph node", 
                                   name=node["name"], type=node["type"], node_id=str(node_id))
                
                # 3. Store knowledge graph edges  
                for edge in llm_result.get("edges", []):
                    source_id = node_ids.get(edge["source"])
                    target_id = node_ids.get(edge["target"])
                    
                    if source_id and target_id:
                        edge_id = await conn.fetchval("""
                            INSERT INTO idea_database.knowledge_graph_edges 
                            (source_node_id, target_node_id, edge_type, context, source_id, source_email_id, created_at, updated_at)
                            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                            ON CONFLICT DO NOTHING
                            RETURNING id
                        """, source_id, target_id, edge["type"].lower(), 
                             edge.get("context", ""), source_email_id, source_email_id)
                        
                        if edge_id:
                            logger.info("Stored knowledge graph edge", 
                                       source=edge["source"], target=edge["target"], 
                                       type=edge["type"], edge_id=str(edge_id))
                    else:
                        logger.warning("Skipping edge due to missing nodes", 
                                      source=edge["source"], target=edge["target"],
                                      source_found=source_id is not None,
                                      target_found=target_id is not None)
                
                # 4. Mark email as completed
                await conn.execute("""
                    UPDATE idea_database.source_emails SET processing_status = 'completed', updated_at = NOW()
                    WHERE id = $1
                """, source_email_id)
                
                logger.info("Knowledge graph data stored successfully", 
                           email_id=email_id, nodes_stored=len(node_ids), 
                           edges_attempted=len(llm_result.get("edges", [])))
                
    except Exception as e:
        logger.error("Failed to store knowledge graph data", email_id=email_id, error=str(e))
        raise

async def analyze_sentiment(text: str) -> Dict[str, float]:
    """Simple sentiment analysis - can be enhanced later"""
    # Placeholder sentiment analysis
    return {"positive": 0.6, "neutral": 0.3, "negative": 0.1}

async def calculate_priority(llm_result: dict) -> float:
    """Calculate priority score based on extracted entities"""
    nodes = llm_result.get("nodes", [])
    edges = llm_result.get("edges", [])
    
    # Simple priority calculation based on entity complexity
    base_score = 0.5
    entity_boost = min(len(nodes) * 0.1, 0.3)  # Up to 0.3 boost for entities
    relationship_boost = min(len(edges) * 0.05, 0.2)  # Up to 0.2 boost for relationships
    
    return min(base_score + entity_boost + relationship_boost, 1.0)

async def handle_redis_event(event_data: str):
    """Process a single event from Redis, extract, and publish results."""
    try:
        payload = json.loads(event_data)
        text = payload.get("text") or payload.get("content") or ""
        if not text:
            logger.warn("No text found in event payload", payload=payload)
            return
        extraction = await extract_with_llm(text)
        output = {
            "source_event": payload,
            "extraction": extraction
        }
        # Publish to output channel
        async with aioredis.from_url(REDIS_URL) as redis:
            await redis.publish(REDIS_OUTPUT_CHANNEL, json.dumps(output))
        logger.info("Published extraction result", channel=REDIS_OUTPUT_CHANNEL)
    except Exception as e:
        logger.error("Failed to process redis event", error=str(e), event=event_data)

async def redis_subscriber():
    """Background task: subscribe to Redis channels and process events."""
    logger.info("Starting Redis event subscriber", channels=REDIS_EVENTS_CHANNELS)
    try:
        redis = aioredis.from_url(REDIS_URL)
        pubsub = redis.pubsub()
        await pubsub.subscribe(*REDIS_EVENTS_CHANNELS)
        async for message in pubsub.listen():
            if message["type"] == "message":
                event_data = message["data"]
                if isinstance(event_data, bytes):
                    event_data = event_data.decode()
                logger.info("Received redis event", channel=message["channel"], data=event_data)
                await handle_redis_event(event_data)
    except Exception as e:
        logger.error("Redis subscriber error", error=str(e))

# Database config
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://ai_user:ai_platform_dev@ai_platform_postgres:5432/ai_platform")

@app.on_event("startup")
async def startup_event():
    global db_pool
    db_pool = await asyncpg.create_pool(POSTGRES_URL, min_size=1, max_size=5)
    # Start Redis subscriber in background
    asyncio.create_task(redis_subscriber())
    logger.info("AI Processor startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    global db_pool
    if db_pool:
        await db_pool.close()

# Taxonomy Pydantic models
class TaxonomyNodeTypeIn(BaseModel):
    name: str
    color: str
    definition: str
    example: Optional[str] = None
    attributes: Optional[dict] = None

class TaxonomyNodeTypeOut(TaxonomyNodeTypeIn):
    id: str

class TaxonomyEdgeTypeIn(BaseModel):
    name: str
    color: str
    definition: str
    example: Optional[str] = None
    directionality: str

class TaxonomyEdgeTypeOut(TaxonomyEdgeTypeIn):
    id: str

# --- Taxonomy Node Type Endpoints ---
@app.get("/taxonomy/nodes", response_model=List[TaxonomyNodeTypeOut])
async def list_node_types():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id::text, name, color, definition, example, attributes FROM idea_database.taxonomy_node_types ORDER BY name")
        result = []
        for row in rows:
            data = dict(row)
            if data["attributes"] and isinstance(data["attributes"], str):
                try:
                    data["attributes"] = json.loads(data["attributes"])
                except Exception:
                    data["attributes"] = None
            result.append(TaxonomyNodeTypeOut(**data))
        return result

@app.post("/taxonomy/nodes", response_model=TaxonomyNodeTypeOut)
async def create_node_type(node: TaxonomyNodeTypeIn):
    async with db_pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO idea_database.taxonomy_node_types (name, color, definition, example, attributes)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id::text, name, color, definition, example, attributes
                """,
                node.name, node.color, node.definition, node.example, json.dumps(node.attributes) if node.attributes else None
            )
            data = dict(row)
            if data["attributes"] and isinstance(data["attributes"], str):
                try:
                    data["attributes"] = json.loads(data["attributes"])
                except Exception:
                    data["attributes"] = None
            return TaxonomyNodeTypeOut(**data)
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=400, detail="Node type name must be unique.")

@app.put("/taxonomy/nodes/{node_id}", response_model=TaxonomyNodeTypeOut)
async def update_node_type(node_id: str, node: TaxonomyNodeTypeIn):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE idea_database.taxonomy_node_types
            SET name=$1, color=$2, definition=$3, example=$4, attributes=$5, updated_at=NOW()
            WHERE id=$6
            RETURNING id::text, name, color, definition, example, attributes
            """,
            node.name, node.color, node.definition, node.example, json.dumps(node.attributes) if node.attributes else None, node_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Node type not found.")
        data = dict(row)
        if data["attributes"] and isinstance(data["attributes"], str):
            try:
                data["attributes"] = json.loads(data["attributes"])
            except Exception:
                data["attributes"] = None
        return TaxonomyNodeTypeOut(**data)

@app.delete("/taxonomy/nodes/{node_id}")
async def delete_node_type(node_id: str):
    async with db_pool.acquire() as conn:
        result = await conn.execute("DELETE FROM idea_database.taxonomy_node_types WHERE id=$1", node_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Node type not found.")
        return {"status": "deleted"}

# --- Taxonomy Edge Type Endpoints ---
@app.get("/taxonomy/edges", response_model=List[TaxonomyEdgeTypeOut])
async def list_edge_types():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id::text, name, color, definition, example, directionality FROM idea_database.taxonomy_edge_types ORDER BY name")
        return [TaxonomyEdgeTypeOut(**dict(row)) for row in rows]

@app.post("/taxonomy/edges", response_model=TaxonomyEdgeTypeOut)
async def create_edge_type(edge: TaxonomyEdgeTypeIn):
    async with db_pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO idea_database.taxonomy_edge_types (name, color, definition, example, directionality)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id::text, name, color, definition, example, directionality
                """,
                edge.name, edge.color, edge.definition, edge.example, edge.directionality
            )
            return TaxonomyEdgeTypeOut(**dict(row))
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=400, detail="Edge type name must be unique.")

@app.put("/taxonomy/edges/{edge_id}", response_model=TaxonomyEdgeTypeOut)
async def update_edge_type(edge_id: str, edge: TaxonomyEdgeTypeIn):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE idea_database.taxonomy_edge_types
            SET name=$1, color=$2, definition=$3, example=$4, directionality=$5, updated_at=NOW()
            WHERE id=$6
            RETURNING id::text, name, color, definition, example, directionality
            """,
            edge.name, edge.color, edge.definition, edge.example, edge.directionality, edge_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Edge type not found.")
        return TaxonomyEdgeTypeOut(**dict(row))

@app.delete("/taxonomy/edges/{edge_id}")
async def delete_edge_type(edge_id: str):
    async with db_pool.acquire() as conn:
        result = await conn.execute("DELETE FROM idea_database.taxonomy_edge_types WHERE id=$1", edge_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Edge type not found.")
        return {"status": "deleted"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "ai_processor",
        "version": "1.0.0",
        "description": "Entity extraction and AI-powered analysis for Ideas Database",
        "endpoints": {
            "health": "/health",
            "process_email": "/process/email",
            "process_batch": "/process/batch",
            "status": "/status/{email_id}",
            "extract_entities": "/extract/entities",
            "categorize": "/categorize",
            "manual_extract": "/extract/manual"
        }
    }

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="ai_processor",
        version="1.0.0"
    )

# Process email content
@app.post("/process/email", response_model=ProcessingResult)
async def process_email(email_content: EmailContent, background_tasks: BackgroundTasks):
    """Process email content for entity extraction and categorization"""
    logger.info("Processing email", email_id=email_content.email_id)
    
    try:
        # Combine subject and body for LLM analysis
        combined_text = f"Subject: {email_content.subject}\n\nContent: {email_content.body}"
        
        # Extract entities and relationships using LLM with database taxonomy
        llm_result = await extract_with_llm(combined_text)
        
        # Store results in modern knowledge graph tables
        await store_knowledge_graph_data(email_content.email_id, llm_result, email_content)
        
        # Calculate additional metrics
        sentiment = await analyze_sentiment(email_content.body)
        priority_score = await calculate_priority(llm_result)
        
        # Extract unique categories from node types
        categories = list(set(node["type"] for node in llm_result.get("nodes", [])))
        
        result = ProcessingResult(
            email_id=email_content.email_id,
            entities=llm_result.get("nodes", []),
            categories=categories,
            sentiment=sentiment,
            priority_score=priority_score,
            processing_status="completed"
        )
        
        logger.info("Email processed successfully", 
                   email_id=email_content.email_id,
                   entities_found=len(result.entities),
                   categories=categories,
                   priority_score=priority_score)
        return result
        
    except Exception as e:
        logger.error("Error processing email", email_id=email_content.email_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

# Batch processing endpoint
@app.post("/process/batch")
async def process_batch(emails: List[EmailContent], background_tasks: BackgroundTasks):
    """Process multiple emails in batch"""
    logger.info("Processing email batch", count=len(emails))
    
    try:
        results = []
        for email in emails:
            # Add to background tasks for async processing
            background_tasks.add_task(process_email_background, email)
            results.append({"email_id": email.email_id, "status": "queued"})
        
        return {"processed": len(emails), "results": results}
        
    except Exception as e:
        logger.error("Error processing batch", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

async def process_email_background(email_content: EmailContent):
    """Background task for email processing"""
    logger.info("Background processing email", email_id=email_content.email_id)
    # TODO: Implement background processing logic
    await asyncio.sleep(1)  # Placeholder
    logger.info("Background processing completed", email_id=email_content.email_id)

# Get processing status
@app.get("/status/{email_id}")
async def get_processing_status(email_id: str):
    """Get processing status for a specific email"""
    # TODO: Implement status tracking
    return {"email_id": email_id, "status": "completed", "timestamp": "2025-06-22T14:00:00Z"}

# Extract entities from text
@app.post("/extract/entities")
async def extract_entities(request: Dict[str, Any]):
    """Extract entities from text content"""
    text = request.get("text", "")
    logger.info("Extracting entities from text", text_length=len(text))
    
    try:
        # TODO: Implement actual entity extraction
        entities = [
            {"type": "person", "value": "John Doe", "confidence": 0.95, "start": 0, "end": 8},
            {"type": "organization", "value": "Acme Corp", "confidence": 0.88, "start": 20, "end": 29},
            {"type": "location", "value": "New York", "confidence": 0.92, "start": 35, "end": 43}
        ]
        
        return {"text": text, "entities": entities, "status": "completed"}
        
    except Exception as e:
        logger.error("Error extracting entities", error=str(e))
        raise HTTPException(status_code=500, detail=f"Entity extraction failed: {str(e)}")

# Categorize content
@app.post("/categorize")
async def categorize_content(request: Dict[str, Any]):
    """Categorize content based on AI analysis"""
    text = request.get("text", "")
    subject = request.get("subject", "")
    logger.info("Categorizing content", text_length=len(text))
    
    try:
        # TODO: Implement actual categorization
        categories = [
            {"category": "technology", "confidence": 0.85},
            {"category": "business", "confidence": 0.72},
            {"category": "research", "confidence": 0.68}
        ]
        
        return {
            "text": text,
            "subject": subject,
            "categories": categories,
            "primary_category": "technology",
            "status": "completed"
        }
        
    except Exception as e:
        logger.error("Error categorizing content", error=str(e))
        raise HTTPException(status_code=500, detail=f"Categorization failed: {str(e)}")

# Manual extraction endpoint for testing
class ManualExtractionRequest(BaseModel):
    text: str

@app.post("/extract/manual")
async def manual_extract(request: ManualExtractionRequest):
    """Manually trigger LLM extraction for a given text."""
    logger.info("Manual extraction requested", text_length=len(request.text))
    result = await extract_with_llm(request.text)
    return {"input": request.text, "extraction": result}

if __name__ == "__main__":
    port = int(os.getenv("AI_PROCESSOR_PORT", 8000))
    logger.info("Starting AI Processor Service", port=port)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_config=None  # Use structlog instead
    ) 