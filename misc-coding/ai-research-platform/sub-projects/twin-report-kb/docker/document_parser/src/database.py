#!/usr/bin/env python3
"""
Database Manager for Document Parser
Handles PostgreSQL operations for parsed documents
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

import asyncpg
import structlog

logger = structlog.get_logger(__name__)

class DatabaseManager:
    """Manages database operations for parsed documents"""
    
    def __init__(self, postgres_url: str):
        self.postgres_url = postgres_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self, max_attempts: int = 10, backoff_seconds: int = 3):
        """Initialize database connection pool with retry logic."""

        attempt = 1
        while attempt <= max_attempts:
            try:
                self.pool = await asyncpg.create_pool(
                    self.postgres_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=60,
                    ssl="disable"  # Disable SSL inside Docker network
                )

                # Create tables if they don't exist
                await self._create_tables()

                logger.info("Database initialized successfully", attempt=attempt)
                return
            except Exception as e:
                logger.warning(
                    "Database initialization attempt failed – retrying",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=str(e)
                )
                if attempt == max_attempts:
                    logger.error("Exceeded max DB initialization attempts", error=str(e))
                    raise
                await asyncio.sleep(backoff_seconds)
                attempt += 1
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connections closed")
    
    async def _create_tables(self):
        """Create necessary tables for document parsing"""
        
        create_parsed_documents_table = """
        CREATE TABLE IF NOT EXISTS parsed_documents (
            document_id VARCHAR(255) PRIMARY KEY,
            content_type VARCHAR(100) NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata JSONB DEFAULT '{}',
            structure JSONB DEFAULT '{}',
            extraction_stats JSONB DEFAULT '{}',
            processing_time FLOAT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        create_batch_results_table = """
        CREATE TABLE IF NOT EXISTS batch_parse_results (
            batch_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            document_count INTEGER NOT NULL,
            success_count INTEGER NOT NULL,
            failed_count INTEGER NOT NULL,
            results JSONB NOT NULL,
            options JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        create_parsing_errors_table = """
        CREATE TABLE IF NOT EXISTS parsing_errors (
            error_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            document_identifier TEXT NOT NULL,
            content_type VARCHAR(100),
            error_message TEXT NOT NULL,
            error_details JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Create indexes for better performance
        create_indexes = """
        CREATE INDEX IF NOT EXISTS idx_parsed_documents_content_type ON parsed_documents(content_type);
        CREATE INDEX IF NOT EXISTS idx_parsed_documents_created_at ON parsed_documents(created_at);
        CREATE INDEX IF NOT EXISTS idx_batch_results_created_at ON batch_parse_results(created_at);
        CREATE INDEX IF NOT EXISTS idx_parsing_errors_created_at ON parsing_errors(created_at);
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(create_parsed_documents_table)
            await conn.execute(create_batch_results_table)
            await conn.execute(create_parsing_errors_table)
            await conn.execute(create_indexes)
        
        logger.info("Database tables created/verified")
    
    async def store_parsed_document(self, document_data: Dict[str, Any]) -> bool:
        """Store parsed document in database"""
        
        try:
            query = """
            INSERT INTO parsed_documents (
                document_id, content_type, title, content, metadata, 
                structure, extraction_stats, processing_time
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (document_id) DO UPDATE SET
                content_type = EXCLUDED.content_type,
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata,
                structure = EXCLUDED.structure,
                extraction_stats = EXCLUDED.extraction_stats,
                processing_time = EXCLUDED.processing_time,
                updated_at = CURRENT_TIMESTAMP
            """
            
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    document_data["document_id"],
                    document_data["content_type"],
                    document_data["title"],
                    document_data["content"],
                    json.dumps(document_data.get("metadata", {})),
                    json.dumps(document_data.get("structure", {})),
                    json.dumps(document_data.get("extraction_stats", {})),
                    document_data.get("processing_time", 0.0)
                )
            
            logger.info("Document stored successfully", document_id=document_data["document_id"])
            return True
            
        except Exception as e:
            logger.error("Failed to store document", 
                        document_id=document_data.get("document_id"),
                        error=str(e))
            return False
    
    async def get_parsed_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get parsed document by ID"""
        
        try:
            query = """
            SELECT document_id, content_type, title, content, metadata, 
                   structure, extraction_stats, processing_time, created_at, updated_at
            FROM parsed_documents 
            WHERE document_id = $1
            """
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, document_id)
                
                if row:
                    return {
                        "document_id": row["document_id"],
                        "content_type": row["content_type"],
                        "title": row["title"],
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "structure": json.loads(row["structure"]) if row["structure"] else {},
                        "extraction_stats": json.loads(row["extraction_stats"]) if row["extraction_stats"] else {},
                        "processing_time": row["processing_time"],
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat()
                    }
                
                return None
                
        except Exception as e:
            logger.error("Failed to get document", document_id=document_id, error=str(e))
            return None
    
    async def list_parsed_documents(
        self, 
        limit: int = 50, 
        offset: int = 0, 
        content_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List parsed documents with pagination"""
        
        try:
            base_query = """
            SELECT document_id, content_type, title, 
                   SUBSTRING(content, 1, 200) as content_preview,
                   metadata, processing_time, created_at
            FROM parsed_documents
            """
            
            if content_type:
                query = base_query + " WHERE content_type = $3 ORDER BY created_at DESC LIMIT $1 OFFSET $2"
                params = [limit, offset, content_type]
            else:
                query = base_query + " ORDER BY created_at DESC LIMIT $1 OFFSET $2"
                params = [limit, offset]
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                
                documents = []
                for row in rows:
                    documents.append({
                        "document_id": row["document_id"],
                        "content_type": row["content_type"],
                        "title": row["title"],
                        "content_preview": row["content_preview"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                        "processing_time": row["processing_time"],
                        "created_at": row["created_at"].isoformat()
                    })
                
                return documents
                
        except Exception as e:
            logger.error("Failed to list documents", error=str(e))
            return []
    
    async def store_batch_results(self, results: List[Dict[str, Any]], options: Dict[str, Any]) -> str:
        """Store batch parsing results"""
        
        try:
            success_count = len([r for r in results if "error" not in r])
            failed_count = len(results) - success_count
            
            query = """
            INSERT INTO batch_parse_results (
                document_count, success_count, failed_count, results, options
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING batch_id
            """
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    len(results),
                    success_count,
                    failed_count,
                    json.dumps(results),
                    json.dumps(options)
                )
                
                batch_id = str(row["batch_id"])
                logger.info("Batch results stored", 
                           batch_id=batch_id,
                           document_count=len(results),
                           success_count=success_count)
                
                return batch_id
                
        except Exception as e:
            logger.error("Failed to store batch results", error=str(e))
            raise
    
    async def log_parsing_error(
        self, 
        document_identifier: str, 
        content_type: str, 
        error_message: str, 
        error_details: Dict[str, Any] = None
    ):
        """Log parsing error to database"""
        
        try:
            query = """
            INSERT INTO parsing_errors (
                document_identifier, content_type, error_message, error_details
            ) VALUES ($1, $2, $3, $4)
            """
            
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    document_identifier,
                    content_type,
                    error_message,
                    json.dumps(error_details or {})
                )
            
            logger.info("Parsing error logged", 
                       document_identifier=document_identifier,
                       content_type=content_type)
            
        except Exception as e:
            logger.error("Failed to log parsing error", error=str(e))
    
    async def get_parsing_stats(self) -> Dict[str, Any]:
        """Get parsing statistics"""
        
        try:
            stats_query = """
            SELECT 
                content_type,
                COUNT(*) as document_count,
                AVG(processing_time) as avg_processing_time,
                MAX(processing_time) as max_processing_time,
                MIN(processing_time) as min_processing_time
            FROM parsed_documents 
            GROUP BY content_type
            """
            
            error_stats_query = """
            SELECT 
                content_type,
                COUNT(*) as error_count
            FROM parsing_errors 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY content_type
            """
            
            async with self.pool.acquire() as conn:
                stats_rows = await conn.fetch(stats_query)
                error_rows = await conn.fetch(error_stats_query)
                
                stats = {
                    "document_stats": [dict(row) for row in stats_rows],
                    "error_stats": [dict(row) for row in error_rows],
                    "total_documents": sum(row["document_count"] for row in stats_rows),
                    "generated_at": datetime.now().isoformat()
                }
                
                return stats
                
        except Exception as e:
            logger.error("Failed to get parsing stats", error=str(e))
            return {"error": str(e)}
    
    async def cleanup_old_documents(self, days_old: int = 30) -> int:
        """Clean up old parsed documents"""
        
        try:
            query = """
            DELETE FROM parsed_documents 
            WHERE created_at < CURRENT_DATE - INTERVAL '%s days'
            """ % days_old
            
            async with self.pool.acquire() as conn:
                result = await conn.execute(query)
                
                # Extract number of deleted rows from result
                deleted_count = int(result.split()[-1]) if result else 0
                
                logger.info("Old documents cleaned up", 
                           deleted_count=deleted_count,
                           days_old=days_old)
                
                return deleted_count
                
        except Exception as e:
            logger.error("Failed to cleanup old documents", error=str(e))
            return 0 