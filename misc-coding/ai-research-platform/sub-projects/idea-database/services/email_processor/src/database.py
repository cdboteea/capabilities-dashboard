#!/usr/bin/env python3
"""
Database Manager for Email Processing Pipeline

📋 PIPELINE REFERENCE: See docs/EMAIL_PROCESSING_PIPELINE.md for complete architecture

This module handles ALL DATABASE OPERATIONS for the email processing pipeline:
- Modern schema operations (source_emails, knowledge_graph_nodes, knowledge_graph_edges)
- Email storage and retrieval with full-text search
- Attachment and URL management with Drive integration
- Conversion job queue management
- Dashboard statistics and reporting

Database Schema: Modern architecture using source_emails as primary table
External Database: ai_platform_postgres:5432 (shared across services)
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import structlog
import asyncpg
import traceback

logger = structlog.get_logger()

class DatabaseManager:
    """PostgreSQL database manager for ideas storage"""
    
    # ------------------------------------------------------------
    # WARNING FOR LLMs & DEVELOPERS:
    # Do NOT modify node creation or persistence methods (ideas, entities, URLs, categories, senders)
    # without first consulting the user (project owner).
    # These methods are critical for graph integrity and downstream logic.
    # ------------------------------------------------------------
    
    def __init__(self, postgres_url: str):
        self.postgres_url = postgres_url
        self.connection_pool = None
        
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                self.postgres_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool initialized")
            
            # Test connection
            async with self.connection_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.connection_pool is not None
    
    async def store_idea(self, title: str, content: str, category: str,
                        source_email: str, email_hash: str, message_id: str,
                        received_date: datetime, processing_status: str = 'completed') -> str:
        """
        Store a new idea in the database
        WARNING: Do not change idea persistence logic without explicit user approval.
        """
        
        query = """
        INSERT INTO idea_database.ideas (subject, cleaned_content, category, sender_email, email_id, message_id,
                          received_date, created_at, updated_at, processing_status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id
        """
        
        now = datetime.now()
        
        async with self.connection_pool.acquire() as conn:
            idea_id = await conn.fetchval(
                query, title, content, category, source_email, email_hash, message_id,
                received_date, now, now, processing_status
            )
        
        logger.info("Idea stored", idea_id=idea_id, category=category)
        return str(idea_id)
    
    async def store_urls(self, idea_id: str, urls: List[Dict[str, str]]):
        """
        Store URLs associated with an idea with Phase 1 enhancements
        WARNING: Do not change URL persistence logic without explicit user approval.
        """
        
        if not urls:
            return
        
        query = """
        INSERT INTO idea_database.urls (
            idea_id, url, domain, title, description, content_type, 
            fetch_status, archive_path, markdown_content, processing_status,
            processing_error, content_length, processed_date, created_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        ON CONFLICT (idea_id, url) DO NOTHING
        """
        
        now = datetime.now()
        stored_count = 0
        
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                for url_data in urls:
                    try:
                        result = await conn.execute(
                            query, 
                            idea_id, 
                            url_data['url'], 
                            url_data['domain'], 
                            url_data['title'],
                            url_data.get('description'),
                            url_data.get('content_type'),
                            url_data.get('fetch_status', 'pending'),
                            url_data.get('archive_path'),
                            url_data.get('markdown_content'),
                            url_data.get('processing_status', 'pending'),
                            url_data.get('processing_error'),
                            url_data.get('content_length'),
                            url_data.get('processed_date'),
                            now
                        )
                        # Count successful inserts (ON CONFLICT DO NOTHING returns "INSERT 0 0" for conflicts)
                        if result == "INSERT 0 1":
                            stored_count += 1
                    except Exception as e:
                        # Log individual URL errors but don't fail the entire batch
                        logger.warning("Failed to store URL", 
                                     idea_id=idea_id, 
                                     url=url_data.get('url', 'unknown'), 
                                     error=str(e))
        
        logger.info("URLs stored", idea_id=idea_id, total_urls=len(urls), stored_count=stored_count)

    async def get_urls_by_idea(self, idea_id: str) -> List[Dict[str, Any]]:
        """Retrieve all URLs associated with a given idea ID."""
        query = "SELECT id, url FROM idea_database.urls WHERE idea_id = $1"
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, idea_id)
        return [dict(row) for row in rows]

    async def get_entities_by_idea(self, idea_id: str) -> List[Dict[str, Any]]:
        """Retrieve all entities associated with a given idea ID."""
        query = "SELECT id, entity_value, entity_type FROM idea_database.entities WHERE idea_id = $1"
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, idea_id)
        return [dict(row) for row in rows]

    async def store_links(self, links: List[Dict[str, Any]]):
        """Store a list of knowledge graph links (edges) in the database."""
        if not links:
            logger.warning("store_links called with empty links list")
            return

        logger.info("store_links received edges", edges=links)
        query = """
        INSERT INTO idea_database.links (source_node_id, target_node_id, type)
        VALUES ($1, $2, $3)
        ON CONFLICT (source_node_id, target_node_id, type) DO NOTHING
        """
        async with self.connection_pool.acquire() as conn:
            try:
                await conn.executemany(
                    query,
                    [(link['source'], link['target'], link['type']) for link in links]
                )
                logger.info("Stored knowledge graph links", count=len(links))
            except Exception as e:
                logger.error("Failed to store links", error=str(e), edges=links)

    async def is_email_processed(self, email_hash: str) -> bool:
        """Check if email has already been processed"""
        
        query = "SELECT id FROM idea_database.ideas WHERE email_id = $1 LIMIT 1"
        
        async with self.connection_pool.acquire() as conn:
            result = await conn.fetchval(query, email_hash)
        
        return result is not None
    
    async def get_idea_id_by_email(self, email_hash: str) -> Optional[str]:
        """Return idea ID for a given email hash if it exists"""
        query = "SELECT id FROM idea_database.ideas WHERE email_id = $1 LIMIT 1"
        async with self.connection_pool.acquire() as conn:
            result = await conn.fetchval(query, email_hash)
            return str(result) if result else None
    
    async def get_ideas_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get ideas by category"""
        
        query = """
        SELECT id, subject, cleaned_content, category, sender_email, created_at
        FROM idea_database.ideas 
        WHERE category = $1
        ORDER BY created_at DESC
        LIMIT $2
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, category, limit)
        
        return [dict(row) for row in rows]
    
    async def search_ideas(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search ideas comprehensively across subject, content, and sender fields"""
        
        query = """
        SELECT id, subject, cleaned_content, 
               'email' as category, sender_email, created_at,
               ts_rank(
                   to_tsvector('english', 
                       COALESCE(subject, '') || ' ' || 
                       COALESCE(cleaned_content, '') || ' ' || 
                       COALESCE(sender_email, '')
                   ), 
                   to_tsquery($1)
               ) as rank
        FROM idea_database.source_emails 
        WHERE (
            to_tsvector('english', 
                COALESCE(subject, '') || ' ' || 
                COALESCE(cleaned_content, '') || ' ' || 
                COALESCE(sender_email, '')
            ) @@ to_tsquery($1)
            OR subject ILIKE $2
            OR sender_email ILIKE $2
            OR cleaned_content ILIKE $2
        )
        AND processing_status = 'completed'
        ORDER BY rank DESC, created_at DESC
        LIMIT $3
        """
        
        # Convert search term to tsquery format for full-text search
        search_query = ' & '.join(search_term.split())
        # Wildcard pattern for ILIKE search
        like_pattern = f'%{search_term}%'
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, search_query, like_pattern, limit)
        
        return [dict(row) for row in rows]
    
    async def search_ideas_with_filters(
        self,
        query: str,
        entity_types: List[str] = None,
        senders: List[str] = None,
        status: List[str] = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search ideas with comprehensive filtering support"""
        
        # Convert search term to tsquery format for full-text search
        search_query = ' & '.join(query.split())
        # Wildcard pattern for ILIKE search
        like_pattern = f'%{query}%'
        
        # Build WHERE clause conditions - start with search conditions
        where_conditions = ["""(
            to_tsvector('english', 
                COALESCE(se.subject, '') || ' ' || 
                COALESCE(se.cleaned_content, '') || ' ' || 
                COALESCE(se.sender_email, '')
            ) @@ to_tsquery($1)
            OR se.subject ILIKE $2
            OR se.sender_email ILIKE $2
            OR se.cleaned_content ILIKE $2
        )"""]
        
        params = [search_query, like_pattern]
        param_counter = 3
        
        # Add additional filter conditions
        where_conditions.append("se.processing_status = 'completed'")
        
        # Handle entity type filtering
        if entity_types:
            entity_type_placeholders = [f"${param_counter + i}" for i in range(len(entity_types))]
            where_conditions.append(f"kgn.node_type = ANY(ARRAY[{','.join(entity_type_placeholders)}])")
            params.extend(entity_types)
            param_counter += len(entity_types)
            
        if senders:
            sender_placeholders = [f"${param_counter + i}" for i in range(len(senders))]
            where_conditions.append(f"se.sender_email = ANY(ARRAY[{','.join(sender_placeholders)}])")
            params.extend(senders)
            param_counter += len(senders)
            
        if status:
            status_placeholders = [f"${param_counter + i}" for i in range(len(status))]
            where_conditions.append(f"se.processing_status = ANY(ARRAY[{','.join(status_placeholders)}])")
            params.extend(status)
            param_counter += len(status)
            
        if start_date:
            where_conditions.append(f"se.created_at >= ${param_counter}")
            params.append(start_date)
            param_counter += 1
            
        if end_date:
            where_conditions.append(f"se.created_at <= ${param_counter}")
            params.append(end_date)
            param_counter += 1
        
        # Add LIMIT and OFFSET parameters
        limit_param = f"${param_counter}"
        offset_param = f"${param_counter + 1}"
        params.extend([limit, offset])
        
        # Build query with optional JOIN for entity type filtering
        if entity_types:
            query_sql = f"""
            SELECT DISTINCT se.id, se.subject, se.cleaned_content, 
                   'email' as category, se.sender_email, se.created_at,
                   ts_rank(
                       to_tsvector('english', 
                           COALESCE(se.subject, '') || ' ' || 
                           COALESCE(se.cleaned_content, '') || ' ' || 
                           COALESCE(se.sender_email, '')
                       ), 
                       to_tsquery($1)
                   ) as rank
            FROM idea_database.source_emails se
            INNER JOIN idea_database.knowledge_graph_nodes kgn ON se.id = kgn.source_email_id
            WHERE {' AND '.join(where_conditions)}
            ORDER BY rank DESC, se.created_at DESC
            LIMIT {limit_param} OFFSET {offset_param}
            """
        else:
            query_sql = f"""
            SELECT se.id, se.subject, se.cleaned_content, 
                   'email' as category, se.sender_email, se.created_at,
                   ts_rank(
                       to_tsvector('english', 
                           COALESCE(se.subject, '') || ' ' || 
                           COALESCE(se.cleaned_content, '') || ' ' || 
                           COALESCE(se.sender_email, '')
                       ), 
                       to_tsquery($1)
                   ) as rank
            FROM idea_database.source_emails se
            WHERE {' AND '.join(where_conditions)}
            ORDER BY rank DESC, se.created_at DESC
            LIMIT {limit_param} OFFSET {offset_param}
            """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query_sql, *params)
        return [dict(row) for row in rows]
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get email processing statistics from MODERN knowledge graph tables"""
        
        # MODERN QUERIES: Read from knowledge graph tables instead of legacy tables
        queries = {
            "total_ideas": "SELECT COUNT(*) FROM idea_database.source_emails",
            "categories": """
                SELECT node_type as category, COUNT(*) as count 
                FROM idea_database.knowledge_graph_nodes 
                GROUP BY node_type 
                ORDER BY count DESC
            """,
            "recent_activity": """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM idea_database.source_emails 
                WHERE created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """,
            "total_urls": "SELECT COUNT(*) FROM idea_database.urls",
            "top_domains": """
                SELECT domain, COUNT(*) as count
                FROM idea_database.urls
                GROUP BY domain
                ORDER BY count DESC
                LIMIT 10
            """,
            "total_entities": "SELECT COUNT(*) FROM idea_database.knowledge_graph_nodes",
            "total_attachments": "SELECT COUNT(*) FROM idea_database.attachments",
            "pending_processing": "SELECT COUNT(*) FROM idea_database.source_emails WHERE processing_status != 'completed'",
            "avg_processing_time": """
                SELECT COALESCE(
                    EXTRACT(EPOCH FROM (NOW() - MAX(updated_at))),
                    0
                )
                FROM idea_database.source_emails
                WHERE processing_status = 'completed'
            """
        }
        
        stats = {}
        
        async with self.connection_pool.acquire() as conn:
            # Get total ideas (from source_emails)
            stats["total_ideas"] = await conn.fetchval(queries["total_ideas"])
            
            # Get category breakdown (from knowledge_graph_nodes)
            category_rows = await conn.fetch(queries["categories"])
            stats["categories"] = {row['category']: row['count'] for row in category_rows}
            
            # Get recent activity (from source_emails)
            activity_rows = await conn.fetch(queries["recent_activity"])
            stats["recent_activity"] = [
                {"date": row['date'].isoformat(), "count": row['count']} 
                for row in activity_rows
            ]
            
            # Get URL stats (still valid)
            stats["total_urls"] = await conn.fetchval(queries["total_urls"])
            
            # Additional totals (from modern tables)
            stats["total_entities"] = await conn.fetchval(queries["total_entities"])
            stats["total_attachments"] = await conn.fetchval(queries["total_attachments"])
            stats["pending_processing"] = await conn.fetchval(queries["pending_processing"])
            avg_proc = await conn.fetchval(queries["avg_processing_time"])
            stats["avg_processing_time"] = float(avg_proc) if avg_proc else 0.0
            
            domain_rows = await conn.fetch(queries["top_domains"])
            stats["top_domains"] = {row['domain']: row['count'] for row in domain_rows}
        
        return stats
    
    async def store_processing_summary(self, summary: Dict[str, Any]):
        """Store email processing summary"""
        
        query = """
        INSERT INTO idea_database.processing_summary (processing_date, emails_processed, 
                                      categories_distribution, urls_extracted, 
                                      processing_time_minutes, created_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        """
        
        now = datetime.now()
        
        async with self.connection_pool.acquire() as conn:
            await conn.execute(
                query,
                now.date(),
                summary.get('total_processed', 0),
                summary.get('categories', {}),
                summary.get('urls_found', 0),
                summary.get('processing_time', 0),
                now
            )
        
        logger.info("Processing summary stored", date=now.date())
    
    async def get_idea_with_urls(self, idea_id: str) -> Optional[Dict[str, Any]]:
        """Get idea with associated URLs"""
        
        idea_query = """
        SELECT id, subject, cleaned_content, category, sender_email, 
               received_date, created_at
        FROM idea_database.ideas WHERE id = $1
        """
        
        urls_query = """
        SELECT DISTINCT ON (url) url, domain, title, created_at
        FROM idea_database.urls WHERE idea_id = $1
        ORDER BY url, created_at
        """
        
        async with self.connection_pool.acquire() as conn:
            idea_row = await conn.fetchrow(idea_query, idea_id)
            if not idea_row:
                return None
            
            url_rows = await conn.fetch(urls_query, idea_id)
            
            idea_data = dict(idea_row)
            idea_data['urls'] = [dict(row) for row in url_rows]
            
            return idea_data
    
    async def get_idea_full(self, idea_id: str) -> Optional[Dict[str, Any]]:
        """Return idea along with URLs and attachments"""

        idea_query = """
        SELECT * FROM idea_database.ideas WHERE id = $1
        """

        urls_query = """
        SELECT DISTINCT ON (url) * FROM idea_database.urls WHERE idea_id = $1 ORDER BY url, created_at
        """

        attachments_query = """
        SELECT * FROM idea_database.attachments WHERE idea_id = $1 ORDER BY created_at
        """

        async with self.connection_pool.acquire() as conn:
            idea_row = await conn.fetchrow(idea_query, idea_id)
            if not idea_row:
                return None
            urls = await conn.fetch(urls_query, idea_id)
            atts = await conn.fetch(attachments_query, idea_id)

        return {
            **dict(idea_row),
            "urls": [dict(u) for u in urls],
            "attachments": [dict(a) for a in atts],
        }

    async def update_idea(self, idea_id: str, updates: Dict[str, Any]):
        """Patch-update an idea row (currently only category supported)."""
        if not updates:
            return
        set_clauses = []
        values = []
        idx = 1
        for field, value in updates.items():
            set_clauses.append(f"{field} = ${idx}")
            values.append(value)
            idx += 1
        set_clause = ", ".join(set_clauses)
        query = f"UPDATE idea_database.ideas SET {set_clause}, updated_at = NOW() WHERE id = ${idx}"
        values.append(idea_id)
        async with self.connection_pool.acquire() as conn:
            await conn.execute(query, *values)

    async def delete_idea(self, idea_id: str):
        """Delete idea; cascades remove urls/attachments via FK."""
        query = "DELETE FROM idea_database.ideas WHERE id = $1"
        async with self.connection_pool.acquire() as conn:
            await conn.execute(query, idea_id)
    
    async def close(self):
        """Close database connection pool"""
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("Database connection pool closed")
    
    async def get_recent_ideas(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get most recent ideas regardless of category from MODERN source_emails table"""
        query = """
        SELECT id, subject, cleaned_content, 
               'email' as category, sender_email, sender_name, 
               received_date, created_at
        FROM idea_database.source_emails
        WHERE processing_status = 'completed'
        ORDER BY created_at DESC
        LIMIT $1
        """
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
        return [dict(row) for row in rows]
    
    async def get_filtered_ideas(
        self, 
        entity_types: List[str] = None,
        senders: List[str] = None,
        status: List[str] = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get ideas with comprehensive filtering support"""
        
        # Build WHERE clause conditions
        where_conditions = ["se.processing_status = 'completed'"]
        params = []
        param_counter = 1
        
        # Use JOIN with knowledge graph if filtering by entity types
        if entity_types:
            entity_type_placeholders = [f"${param_counter + i}" for i in range(len(entity_types))]
            where_conditions.append(f"kgn.node_type = ANY(ARRAY[{','.join(entity_type_placeholders)}])")
            params.extend(entity_types)
            param_counter += len(entity_types)
            
        if senders:
            sender_placeholders = [f"${param_counter + i}" for i in range(len(senders))]
            where_conditions.append(f"se.sender_email = ANY(ARRAY[{','.join(sender_placeholders)}])")
            params.extend(senders)
            param_counter += len(senders)
            
        if status:
            status_placeholders = [f"${param_counter + i}" for i in range(len(status))]
            where_conditions.append(f"se.processing_status = ANY(ARRAY[{','.join(status_placeholders)}])")
            params.extend(status)
            param_counter += len(status)
            
        if start_date:
            where_conditions.append(f"se.created_at >= ${param_counter}")
            params.append(start_date)
            param_counter += 1
            
        if end_date:
            where_conditions.append(f"se.created_at <= ${param_counter}")
            params.append(end_date)
            param_counter += 1
        
        # Add LIMIT and OFFSET parameters
        limit_param = f"${param_counter}"
        offset_param = f"${param_counter + 1}"
        params.extend([limit, offset])
        
        # Build query with optional JOIN for entity type filtering
        if entity_types:
            query = f"""
            SELECT DISTINCT se.id, se.subject, se.cleaned_content, 
                   'email' as category, se.sender_email, se.sender_name, 
                   se.received_date, se.created_at
            FROM idea_database.source_emails se
            INNER JOIN idea_database.knowledge_graph_nodes kgn ON se.id = kgn.source_email_id
            WHERE {' AND '.join(where_conditions)}
            ORDER BY se.created_at DESC
            LIMIT {limit_param} OFFSET {offset_param}
            """
        else:
            query = f"""
            SELECT se.id, se.subject, se.cleaned_content, 
                   'email' as category, se.sender_email, se.sender_name, 
                   se.received_date, se.created_at
            FROM idea_database.source_emails se
            WHERE {' AND '.join(where_conditions)}
            ORDER BY se.created_at DESC
            LIMIT {limit_param} OFFSET {offset_param}
            """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
    
    async def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent activity items for the dashboard feed from MODERN source_emails table"""
        query = """
        SELECT id, 'email' as category, sender_email, created_at
        FROM idea_database.source_emails
        WHERE processing_status = 'completed'
        ORDER BY created_at DESC
        LIMIT $1
        """
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
        activities = []
        for row in rows:
            activities.append({
                "id": str(row["id"]),
                "type": "email_processed",
                "description": f"Email processed ({row['category']})",
                "timestamp": row["created_at"].isoformat(),
                "metadata": {
                    "category": row["category"],
                    "sender": row["sender_email"]
                }
            })
        return activities
    
    async def get_processing_timeseries(self, days: int = 30) -> List[Dict[str, Any]]:
        """Return count of emails processed per day for last N days from MODERN source_emails table"""
        # Use parameterized interval arithmetic without string interpolation inside the SQL string.
        # Multiply an integer parameter by INTERVAL '1 day' to get a proper interval value.
        query = """
        SELECT DATE(created_at) AS date, COUNT(*) AS count
        FROM idea_database.source_emails
        WHERE created_at >= (NOW() - ($1 * INTERVAL '1 day'))
        AND processing_status = 'completed'
        GROUP BY DATE(created_at)
        ORDER BY date
        """
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, days)
        # Ensure output list is sorted by date ascending for chart rendering
        return [
            {"date": row["date"].isoformat(), "value": row["count"]}  # type: ignore[index]
            for row in rows
        ]
    
    # Phase 1: Enhanced methods for conversion job management
    
    async def create_conversion_job(self, attachment_id: str = None, url_id: str = None, 
                                  job_type: str = "file_conversion", priority: int = 5) -> str:
        """Create a new conversion job"""
        query = """
        INSERT INTO idea_database.conversion_jobs (
            attachment_id, url_id, job_type, status, priority, created_at
        ) VALUES ($1, $2, $3, 'pending', $4, NOW())
        RETURNING id
        """
        
        async with self.connection_pool.acquire() as conn:
            job_id = await conn.fetchval(query, attachment_id, url_id, job_type, priority)
        
        logger.info("Conversion job created", job_id=job_id, job_type=job_type)
        return str(job_id)
    
    async def get_pending_conversion_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending conversion jobs ordered by priority"""
        query = """
        SELECT j.*, a.filename, a.file_path, a.drive_file_id, u.url
        FROM idea_database.conversion_jobs j
        LEFT JOIN idea_database.attachments a ON j.attachment_id = a.id
        LEFT JOIN idea_database.urls u ON j.url_id = u.id
        WHERE j.status = 'pending' AND j.retry_count < 3
        ORDER BY j.priority ASC, j.created_at ASC
        LIMIT $1
        """
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
        
        return [dict(row) for row in rows]
    
    async def update_conversion_job(self, job_id: str, status: str, error_message: str = None):
        """Update conversion job status"""
        if status == 'processing':
            query = """
            UPDATE idea_database.conversion_jobs 
            SET status = $1, started_at = NOW() 
            WHERE id = $2
            """
            async with self.connection_pool.acquire() as conn:
                await conn.execute(query, status, job_id)
        elif status == 'completed':
            query = """
            UPDATE idea_database.conversion_jobs 
            SET status = $1, completed_at = NOW() 
            WHERE id = $2
            """
            async with self.connection_pool.acquire() as conn:
                await conn.execute(query, status, job_id)
        elif status == 'failed':
            query = """
            UPDATE idea_database.conversion_jobs 
            SET status = $1, error_message = $2, retry_count = retry_count + 1 
            WHERE id = $3
            """
            async with self.connection_pool.acquire() as conn:
                await conn.execute(query, status, error_message, job_id)
        elif status == 'pending':
            query = """
            UPDATE idea_database.conversion_jobs 
            SET status = 'pending', error_message = NULL, started_at = NULL, completed_at = NULL, retry_count = 0 
            WHERE id = $1
            """
            async with self.connection_pool.acquire() as conn:
                await conn.execute(query, job_id)
            logger.info("Conversion job reset to pending", job_id=job_id)
        
        logger.info("Conversion job updated", job_id=job_id, status=status)
    
    async def get_attachment_by_drive_id(self, drive_file_id: str) -> Optional[Dict[str, Any]]:
        """Get attachment by Google Drive file ID"""
        query = """
        SELECT * FROM idea_database.attachments 
        WHERE drive_file_id = $1
        """
        
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(query, drive_file_id)
        
        return dict(row) if row else None
    
    async def update_attachment_markdown(self, attachment_id: str, markdown_content: str, 
                                       conversion_status: str = 'completed'):
        """Update attachment with markdown content"""
        query = """
        UPDATE idea_database.attachments 
        SET markdown_content = $1, conversion_status = $2, conversion_error = NULL
        WHERE id = $3
        """
        
        async with self.connection_pool.acquire() as conn:
            await conn.execute(query, markdown_content, conversion_status, attachment_id)
        
        logger.info("Attachment markdown updated", attachment_id=attachment_id)
    
    async def update_url_content(self, url_id: str, markdown_content: str, 
                               content_length: int, processing_status: str = 'completed'):
        """Update URL with processed content"""
        query = """
        UPDATE idea_database.urls 
        SET markdown_content = $1, content_length = $2, processing_status = $3, 
            processing_error = NULL, processed_date = NOW()
        WHERE id = $4
        """
        
        async with self.connection_pool.acquire() as conn:
            await conn.execute(query, markdown_content, content_length, processing_status, url_id)
        
        logger.info("URL content updated", url_id=url_id)
    
    async def get_drive_storage_stats(self) -> Dict[str, Any]:
        """Get Google Drive storage statistics"""
        queries = {
            "total_files": "SELECT COUNT(*) FROM idea_database.attachments WHERE drive_file_id IS NOT NULL",
            "total_size": "SELECT SUM(file_size) FROM idea_database.attachments WHERE drive_file_id IS NOT NULL",
            "conversion_stats": """
                SELECT conversion_status, COUNT(*) as count 
                FROM idea_database.attachments 
                GROUP BY conversion_status
            """,
            "storage_by_type": """
                SELECT storage_type, COUNT(*) as count, SUM(file_size) as total_size
                FROM idea_database.attachments 
                GROUP BY storage_type
            """
        }
        
        stats = {}
        
        async with self.connection_pool.acquire() as conn:
            stats["total_drive_files"] = await conn.fetchval(queries["total_files"]) or 0
            stats["total_drive_size"] = await conn.fetchval(queries["total_size"]) or 0
            
            conversion_rows = await conn.fetch(queries["conversion_stats"])
            stats["conversion_stats"] = {row['conversion_status']: row['count'] for row in conversion_rows}
            
            storage_rows = await conn.fetch(queries["storage_by_type"])
            stats["storage_by_type"] = {
                row['storage_type']: {
                    'count': row['count'], 
                    'size': row['total_size'] or 0
                } for row in storage_rows
            }
        
        return stats 
    
    async def store_attachments(self, idea_id: str, attachments: List[Dict[str, Any]]):
        """Store file attachments metadata with Phase 1 enhancements.
        Expected attachment fields: filename, mime_type, size, file_path, content_hash, 
        drive_file_id, drive_file_url, markdown_content, conversion_status, storage_type
        """

        if not attachments:
            return

        query = """
        INSERT INTO idea_database.attachments (
            idea_id,
            filename,
            original_filename,
            file_type,
            file_size,
            file_path,
            content_hash,
            extracted_text,
            drive_file_id,
            drive_file_url,
            markdown_content,
            conversion_status,
            conversion_error,
            storage_type,
            processing_status,
            gmail_message_id,
            gmail_attachment_id,
            created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, 'pending', $15, $16, NOW()
        )
        """

        created_attachment_ids = []
        
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                for att in attachments:
                    # Insert attachment and get the ID
                    result = await conn.fetchval(
                        query + " RETURNING id",
                        idea_id,
                        att.get('filename') or att.get('name') or 'attachment',
                        att.get('original_filename'),
                        att.get('mime_type') or att.get('file_type'),
                        att.get('size') or att.get('file_size'),
                        att.get('file_path') or att.get('path') or '',
                        att.get('content_hash'),
                        att.get('extracted_text'),
                        att.get('drive_file_id'),
                        att.get('drive_file_url'),
                        att.get('markdown_content'),
                        att.get('conversion_status', 'pending'),
                        att.get('conversion_error'),
                        att.get('storage_type', 'local'),
                        att.get('gmail_message_id'),
                        att.get('gmail_attachment_id'),
                    )
                    if result:  # Only if insertion was successful (not a duplicate)
                        created_attachment_ids.append(str(result))
        
        # Create conversion jobs for newly created attachments
        for attachment_id in created_attachment_ids:
            try:
                await self.create_conversion_job(
                    attachment_id=attachment_id,
                    job_type="file_conversion",
                    priority=5
                )
                logger.info("Conversion job created for attachment", attachment_id=attachment_id)
            except Exception as e:
                logger.error("Failed to create conversion job", attachment_id=attachment_id, error=str(e)) 

    async def get_knowledge_graph_data(self) -> Dict[str, list]:
        """Fetches all nodes and edges to construct the knowledge graph."""
        nodes_query = """
        (SELECT id, 'idea' as type, subject as label FROM idea_database.ideas)
        UNION
        (SELECT id, 'entity' as type, entity_value as label FROM idea_database.entities)
        UNION
        (SELECT id, 'url' as type, url as label FROM idea_database.urls)
        UNION
        (SELECT id, 'category' as type, name as label FROM idea_database.categories)
        UNION
        (SELECT id, 'sender' as type, email as label FROM idea_database.senders)
        """
        edges_query = """
        SELECT source_node_id, target_node_id, type 
        FROM idea_database.links
        """
        async with self.connection_pool.acquire() as conn:
            node_records = await conn.fetch(nodes_query)
            edge_records = await conn.fetch(edges_query)
        nodes = [{"id": str(r['id']), "type": r['type'], "label": r['label']} for r in node_records]
        edges = [{"source": str(r['source_node_id']), "target": str(r['target_node_id']), "type": r['type']} for r in edge_records]
        logger.info("Fetched knowledge graph data", node_count=len(nodes), edge_count=len(edges))
        return {"nodes": nodes, "edges": edges} 

    async def store_entity(self, idea_id: str, entity_type: str, entity_value: str) -> str:
        """
        Insert entity if not present and return its UUID.
        WARNING: Do not change entity persistence logic without explicit user approval.
        """
        # Check if entity already exists for this idea/type/value
        select_query = """
        SELECT id FROM idea_database.entities WHERE idea_id = $1 AND entity_type = $2 AND entity_value = $3 LIMIT 1
        """
        insert_query = """
        INSERT INTO idea_database.entities (idea_id, entity_type, entity_value, created_at)
        VALUES ($1, $2, $3, NOW())
        RETURNING id
        """
        async with self.connection_pool.acquire() as conn:
            entity_id = await conn.fetchval(select_query, idea_id, entity_type, entity_value)
            if entity_id:
                return str(entity_id)
            entity_id = await conn.fetchval(insert_query, idea_id, entity_type, entity_value)
            return str(entity_id) 

    async def get_or_create_category(self, name: str) -> str:
        """
        Insert category if not present and return its UUID.
        WARNING: Do not change category persistence logic without explicit user approval.
        """
        select_query = """
        SELECT id FROM idea_database.categories WHERE name = $1 LIMIT 1
        """
        insert_query = """
        INSERT INTO idea_database.categories (name) VALUES ($1) RETURNING id
        """
        async with self.connection_pool.acquire() as conn:
            category_id = await conn.fetchval(select_query, name)
            if category_id:
                return str(category_id)
            category_id = await conn.fetchval(insert_query, name)
            return str(category_id)

    async def get_or_create_sender(self, email: str) -> str:
        """
        Insert sender if not present and return its UUID.
        WARNING: Do not change sender persistence logic without explicit user approval.
        """
        select_query = """
        SELECT id FROM idea_database.senders WHERE email = $1 LIMIT 1
        """
        insert_query = """
        INSERT INTO idea_database.senders (email) VALUES ($1) RETURNING id
        """
        async with self.connection_pool.acquire() as conn:
            sender_id = await conn.fetchval(select_query, email)
            if sender_id:
                return str(sender_id)
            sender_id = await conn.fetchval(insert_query, email)
            return str(sender_id) 

    async def store_nodes(self, nodes: list[dict]) -> list:
        """Store a list of nodes of arbitrary types using taxonomy tables."""
        inserted_ids = []
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                for node in nodes:
                    logger.info("store_nodes: inserting node", node=node, stack=traceback.format_stack())
                    node_type = node.get('type')
                    node_id = node.get('id')
                    label = node.get('label')
                    properties = node.get('properties', {})
                    # Route to appropriate table
                    if node_type == 'idea':
                        # Insert into ideas table
                        query = """
                        INSERT INTO idea_database.ideas (id, subject, cleaned_content, created_at, updated_at)
                        VALUES ($1, $2, $3, NOW(), NOW())
                        ON CONFLICT (id) DO NOTHING
                        """
                        await conn.execute(query, node_id, label, properties.get('content', ''))
                        inserted_ids.append(str(node_id))
                    elif node_type == 'entity':
                        query = """
                        INSERT INTO idea_database.entities (id, entity_value, entity_type, created_at)
                        VALUES ($1, $2, $3, NOW())
                        ON CONFLICT (id) DO NOTHING
                        """
                        await conn.execute(query, node_id, label, properties.get('entity_type', 'unknown'))
                        inserted_ids.append(str(node_id))
                    elif node_type == 'url':
                        query = """
                        INSERT INTO idea_database.urls (id, url, domain, title, created_at)
                        VALUES ($1, $2, $3, $4, NOW())
                        ON CONFLICT (id) DO NOTHING
                        """
                        await conn.execute(query, node_id, label, properties.get('domain', ''), properties.get('title', label))
                        inserted_ids.append(str(node_id))
                    elif node_type == 'category':
                        query = """
                        INSERT INTO idea_database.categories (id, name, created_at)
                        VALUES ($1, $2, NOW())
                        ON CONFLICT (id) DO NOTHING
                        """
                        await conn.execute(query, node_id, label)
                        inserted_ids.append(str(node_id))
                    elif node_type == 'sender':
                        query = """
                        INSERT INTO idea_database.senders (id, email, created_at)
                        VALUES ($1, $2, NOW())
                        ON CONFLICT (id) DO NOTHING
                        """
                        await conn.execute(query, node_id, label)
                        inserted_ids.append(str(node_id))
                    else:
                        # Fallback: insert into taxonomy_node_types as a generic node
                        query = """
                        INSERT INTO idea_database.taxonomy_node_types (id, name, definition, created_at)
                        VALUES ($1, $2, $3, NOW())
                        ON CONFLICT (id) DO NOTHING
                        """
                        await conn.execute(query, node_id, label, properties.get('definition', ''))
                        inserted_ids.append(str(node_id))
        return inserted_ids 
    
    async def cleanup_email_data(self) -> Dict[str, Any]:
        """
        Clean up all email-related data while preserving taxonomy tables.
        ⚠️ CRITICAL: This method automatically protects taxonomy tables and will NEVER delete:
        - taxonomy_node_types (essential for AI processing)
        - taxonomy_edge_types (essential for knowledge graph)
        
        Returns statistics about what was cleaned up.
        """
        
        if not self.connection_pool:
            raise Exception("Database not initialized")
        
        # Tables to clean in order (respects foreign key constraints)
        # ⚠️ PROTECTED TABLES (NEVER CLEANED): taxonomy_node_types, taxonomy_edge_types
        cleanup_tables = [
            'conversion_jobs',         # References attachments, urls
            'x_posts',                # References urls
            'knowledge_graph_edges',   # MODERN: Knowledge graph relationships
            'knowledge_graph_nodes',   # MODERN: Knowledge graph entities  
            'links',                  # Legacy knowledge graph connections
            'entities',               # Legacy entity storage  
            'attachments',            # References ideas/emails
            'urls',                   # References ideas/emails
            'source_emails',          # MODERN: Main email storage
            'ideas',                  # Legacy main table
            'categories',             # Legacy category data (safe to delete)
            'senders',                # Email sender information
            'search_queries',         # Independent search queries
            'processing_summary',     # Processing statistics
            'drive_config'            # Drive configuration
        ]
        
        stats = {'cleaned_tables': {}, 'total_records_deleted': 0}
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.transaction():
                    
                    # Get counts before deletion for reporting
                    for table in cleanup_tables:
                        try:
                            count = await conn.fetchval(f"SELECT COUNT(*) FROM idea_database.{table}")
                            stats['cleaned_tables'][table] = count
                            stats['total_records_deleted'] += count
                        except Exception as e:
                            # Table might not exist, skip it
                            logger.warning(f"Could not count records in table {table}", error=str(e))
                            stats['cleaned_tables'][table] = 0
                    
                    # Perform cleanup in order
                    for table in cleanup_tables:
                        try:
                            await conn.execute(f"TRUNCATE TABLE idea_database.{table} RESTART IDENTITY CASCADE")
                            logger.info(f"Cleaned table: {table}", records_deleted=stats['cleaned_tables'][table])
                        except Exception as e:
                            # Table might not exist or have no data, log but continue
                            logger.warning(f"Could not clean table {table}", error=str(e))
                            stats['cleaned_tables'][table] = 0
                    
                    # Verify taxonomy tables are preserved
                    node_types_count = await conn.fetchval("SELECT COUNT(*) FROM idea_database.taxonomy_node_types")
                    edge_types_count = await conn.fetchval("SELECT COUNT(*) FROM idea_database.taxonomy_edge_types")
                    
                    stats['taxonomy_preserved'] = {
                        'node_types': node_types_count,
                        'edge_types': edge_types_count
                    }
                    
                    logger.info("Database cleanup completed", **stats)
                    
            return stats
                    
        except Exception as e:
            logger.error("Database cleanup failed", error=str(e), traceback=traceback.format_exc())
            raise Exception(f"Database cleanup failed: {str(e)}")

    # ===================================================================
    # MODERN SCHEMA METHODS - URL/ATTACHMENT STORAGE FOR SOURCE_EMAILS
    # ===================================================================
    
    async def get_source_email_id_by_gmail_id(self, gmail_message_id: str) -> Optional[str]:
        """Get source_email_id from gmail_message_id for modern schema integration"""
        try:
            query = "SELECT id FROM idea_database.source_emails WHERE gmail_message_id = $1"
            async with self.connection_pool.acquire() as conn:
                result = await conn.fetchval(query, gmail_message_id)
                return str(result) if result else None
        except Exception as e:
            logger.error("Failed to get source_email_id", gmail_message_id=gmail_message_id, error=str(e))
            return None
    
    async def store_urls_modern(self, source_email_id: str, urls: List[Dict[str, str]]):
        """
        Store URLs linked to source_emails table (modern schema)
        Adapts legacy URL storage to work with modern knowledge graph system
        """
        
        if not urls:
            return
        
        # First update urls table to support source_email_id (temporary bridge approach)
        # Note: This adds source_email_id column if it doesn't exist
        try:
            async with self.connection_pool.acquire() as conn:
                # Add source_email_id column if it doesn't exist
                await conn.execute("""
                    ALTER TABLE idea_database.urls 
                    ADD COLUMN IF NOT EXISTS source_email_id UUID REFERENCES idea_database.source_emails(id)
                """)
        except Exception as e:
            logger.warning("Failed to add source_email_id column to urls table", error=str(e))
        
        query = """
        INSERT INTO idea_database.urls (
            source_email_id, url, domain, title, description, content_type, 
            fetch_status, archive_path, markdown_content, processing_status,
            processing_error, content_length, processed_date, created_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """
        
        now = datetime.now()
        stored_count = 0
        
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                for url_data in urls:
                    try:
                        result = await conn.execute(
                            query, 
                            source_email_id, 
                            url_data['url'], 
                            url_data['domain'], 
                            url_data['title'],
                            url_data.get('description'),
                            url_data.get('content_type'),
                            url_data.get('fetch_status', 'pending'),
                            url_data.get('archive_path'),
                            url_data.get('markdown_content'),
                            url_data.get('processing_status', 'pending'),
                            url_data.get('processing_error'),
                            url_data.get('content_length'),
                            url_data.get('processed_date'),
                            now
                        )
                        # Count successful inserts  
                        if result == "INSERT 0 1":
                            stored_count += 1
                    except Exception as e:
                        # Log individual URL errors but don't fail the entire batch
                        logger.warning("Failed to store URL (modern schema)", 
                                     source_email_id=source_email_id, 
                                     url=url_data.get('url', 'unknown'), 
                                     error=str(e))
        
        logger.info("URLs stored (modern schema)", source_email_id=source_email_id, total_urls=len(urls), stored_count=stored_count)

    async def store_attachments_modern(self, source_email_id: str, attachments: List[Dict[str, Any]], gmail_client=None):
        """
        Store file attachments linked to source_emails table (modern schema)
        Adapts legacy attachment storage to work with modern knowledge graph system
        Drive uploads are handled by conversion jobs in Content Extractor
        """

        if not attachments:
            return

        # First update attachments table to support source_email_id (temporary bridge approach)
        try:
            async with self.connection_pool.acquire() as conn:
                # Add source_email_id column if it doesn't exist
                await conn.execute("""
                    ALTER TABLE idea_database.attachments 
                    ADD COLUMN IF NOT EXISTS source_email_id UUID REFERENCES idea_database.source_emails(id)
                """)
        except Exception as e:
            logger.warning("Failed to add source_email_id column to attachments table", error=str(e))

        query = """
        INSERT INTO idea_database.attachments (
            source_email_id,
            filename,
            original_filename,
            file_type,
            file_size,
            file_path,
            content_hash,
            extracted_text,
            drive_file_id,
            drive_file_url,
            markdown_content,
            conversion_status,
            conversion_error,
            storage_type,
            processing_status,
            gmail_message_id,
            gmail_attachment_id,
            created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, 'pending', $15, $16, NOW()
        )
        ON CONFLICT (content_hash) DO NOTHING
        """

        created_attachment_ids = []
        
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                for att in attachments:
                    try:
                        # Insert attachment and get the ID
                        result = await conn.fetchval(
                            query + " RETURNING id",
                            source_email_id,
                            att.get('filename') or att.get('name') or 'attachment',
                            att.get('original_filename'),
                            att.get('mime_type') or att.get('file_type'),
                            att.get('size') or att.get('file_size'),
                            att.get('file_path') or att.get('path') or '',
                            att.get('content_hash'),
                            att.get('extracted_text'),
                            att.get('drive_file_id'),
                            att.get('drive_file_url'),
                            att.get('markdown_content'),
                            att.get('conversion_status', 'pending'),
                            att.get('conversion_error'),
                            att.get('storage_type', 'local'),
                            att.get('gmail_message_id'),
                            att.get('gmail_attachment_id'),
                        )
                        if result:  # Only if insertion was successful (not a duplicate)
                            created_attachment_ids.append(str(result))
                    except Exception as e:
                        logger.warning("Failed to store attachment (modern schema)", 
                                     source_email_id=source_email_id, 
                                     filename=att.get('filename', 'unknown'), 
                                     error=str(e))
        
        # Create conversion jobs for newly created attachments
        for attachment_id in created_attachment_ids:
            try:
                await self.create_conversion_job(
                    attachment_id=attachment_id,
                    job_type="file_conversion",
                    priority=5
                )
                logger.info("Conversion job created for attachment (modern schema)", attachment_id=attachment_id)
            except Exception as e:
                logger.error("Failed to create conversion job (modern schema)", attachment_id=attachment_id, error=str(e))
        
        logger.info("Attachments stored (modern schema)", source_email_id=source_email_id, total_attachments=len(attachments), created_count=len(created_attachment_ids))