"""
Database Manager for News Crawler
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncpg
import structlog

logger = structlog.get_logger()


class DatabaseManager:
    """
    Manages database connections and operations for the news crawler.
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize database connection pool."""
        try:
            logger.info("Initializing database connection pool")
            
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
                server_settings={
                    'jit': 'off'  # Disable JIT for better performance on smaller queries
                }
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            self.initialized = True
            logger.info("Database connection pool initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.initialized = False
            logger.info("Database connection pool closed")
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            if not self.pool:
                return False
            
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    # ========================================================================
    # CRAWL JOB MANAGEMENT
    # ========================================================================
    
    async def create_crawl_job(
        self, 
        job_id: str, 
        job_config: Dict[str, Any], 
        implementation: str
    ) -> bool:
        """Create a new crawl job record."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO real_time_intel.crawl_jobs (
                        job_id, job_name, job_config, implementation, 
                        status, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """, 
                job_id,
                job_config.get('job_name', 'Unnamed Job'),
                json.dumps(job_config),
                implementation,
                'submitted',
                datetime.now()
                )
            
            logger.info(f"Created crawl job record: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create crawl job {job_id}: {e}")
            return False
    
    async def update_job_status(
        self, 
        job_id: str, 
        status: str, 
        error_message: Optional[str] = None
    ) -> bool:
        """Update job status."""
        try:
            async with self.pool.acquire() as conn:
                if status == 'running' and error_message is None:
                    await conn.execute("""
                        UPDATE real_time_intel.crawl_jobs 
                        SET status = $1, started_at = $2, updated_at = $3
                        WHERE job_id = $4
                    """, status, datetime.now(), datetime.now(), job_id)
                elif status == 'completed' and error_message is None:
                    await conn.execute("""
                        UPDATE real_time_intel.crawl_jobs 
                        SET status = $1, completed_at = $2, updated_at = $3
                        WHERE job_id = $4
                    """, status, datetime.now(), datetime.now(), job_id)
                else:
                    await conn.execute("""
                        UPDATE real_time_intel.crawl_jobs 
                        SET status = $1, error_message = $2, updated_at = $3
                        WHERE job_id = $4
                    """, status, error_message, datetime.now(), job_id)
            
            logger.info(f"Updated job {job_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update job status {job_id}: {e}")
            return False
    
    async def update_job_progress(
        self, 
        job_id: str, 
        progress_data: Dict[str, Any]
    ) -> bool:
        """Update job progress data."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE real_time_intel.crawl_jobs 
                    SET progress_data = $1, updated_at = $2
                    WHERE job_id = $3
                """, 
                json.dumps(progress_data),
                datetime.now(),
                job_id
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update job progress {job_id}: {e}")
            return False
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status information."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT job_id, job_name, status, implementation,
                           progress_data, created_at, started_at, completed_at,
                           error_message, updated_at
                    FROM real_time_intel.crawl_jobs 
                    WHERE job_id = $1
                """, job_id)
            
            if not row:
                return None
            
            # Parse progress data
            progress_data = {}
            if row['progress_data']:
                try:
                    progress_data = json.loads(row['progress_data'])
                except:
                    pass
            
            return {
                'job_id': row['job_id'],
                'job_name': row['job_name'],
                'status': row['status'],
                'implementation': row['implementation'],
                'progress': progress_data,
                'created_at': row['created_at'],
                'started_at': row['started_at'],
                'completed_at': row['completed_at'],
                'error_message': row['error_message'],
                'source_type': progress_data.get('source_type', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Failed to get job status {job_id}: {e}")
            return None
    
    async def get_job_results(
        self, 
        job_id: str, 
        page: int = 1, 
        limit: int = 50,
        include_fields: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get job results with pagination."""
        try:
            offset = (page - 1) * limit
            
            async with self.pool.acquire() as conn:
                # Get total count
                total_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM real_time_intel.extracted_articles 
                    WHERE job_id = $1
                """, job_id)
                
                if total_count == 0:
                    return None
                
                # Get articles
                articles = await conn.fetch("""
                    SELECT article_id, title, url, content, summary,
                           metadata, sentiment_data, entities_data,
                           quality_score, relevance_score, extracted_at
                    FROM real_time_intel.extracted_articles 
                    WHERE job_id = $1
                    ORDER BY extracted_at DESC
                    LIMIT $2 OFFSET $3
                """, job_id, limit, offset)
                
                # Process articles
                processed_articles = []
                for article in articles:
                    article_data = {
                        'article_id': article['article_id'],
                        'metadata': {
                            'title': article['title'],
                            'url': article['url']
                        },
                        'content': article['content'] if 'content' in (include_fields or []) else None,
                        'summary': article['summary'] if 'summary' in (include_fields or []) else None,
                        'quality_score': article['quality_score'],
                        'relevance_score': article['relevance_score'],
                        'processed_at': article['extracted_at']
                    }
                    
                    # Add optional fields
                    if include_fields:
                        if 'metadata' in include_fields and article['metadata']:
                            try:
                                article_data['metadata'].update(json.loads(article['metadata']))
                            except:
                                pass
                        
                        if 'sentiment' in include_fields and article['sentiment_data']:
                            try:
                                article_data['sentiment'] = json.loads(article['sentiment_data'])
                            except:
                                pass
                        
                        if 'entities' in include_fields and article['entities_data']:
                            try:
                                article_data['entities'] = json.loads(article['entities_data'])
                            except:
                                pass
                    
                    processed_articles.append(article_data)
                
                # Calculate pages
                total_pages = (total_count + limit - 1) // limit
                
                return {
                    'job_id': job_id,
                    'total_articles': total_count,
                    'articles': processed_articles,
                    'page': page,
                    'total_pages': total_pages,
                    'generated_at': datetime.now()
                }
                
        except Exception as e:
            logger.error(f"Failed to get job results {job_id}: {e}")
            return None
    
    # ========================================================================
    # ARTICLE STORAGE
    # ========================================================================
    
    async def store_article(
        self, 
        job_id: str, 
        article_data: Dict[str, Any]
    ) -> bool:
        """Store extracted article."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO real_time_intel.extracted_articles (
                        job_id, article_id, title, url, content, summary,
                        metadata, sentiment_data, entities_data, keywords,
                        quality_score, relevance_score, extracted_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT (article_id) DO UPDATE SET
                        quality_score = EXCLUDED.quality_score,
                        relevance_score = EXCLUDED.relevance_score,
                        updated_at = $13
                """,
                job_id,
                article_data['article_id'],
                article_data['metadata']['title'],
                article_data['metadata']['url'],
                article_data.get('content'),
                article_data.get('summary'),
                json.dumps(article_data.get('metadata', {})),
                json.dumps(article_data.get('sentiment')) if article_data.get('sentiment') else None,
                json.dumps(article_data.get('entities')) if article_data.get('entities') else None,
                json.dumps(article_data.get('keywords', [])),
                article_data.get('quality_score'),
                article_data.get('relevance_score'),
                datetime.now()
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store article {article_data.get('article_id')}: {e}")
            return False
    
    # ========================================================================
    # METRICS AND ANALYTICS
    # ========================================================================
    
    async def get_crawler_metrics(
        self, 
        implementation: Optional[str] = None,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Get crawler performance metrics."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            async with self.pool.acquire() as conn:
                # Base query
                where_clause = "WHERE created_at >= $1"
                params = [cutoff_time]
                
                if implementation:
                    where_clause += " AND implementation = $2"
                    params.append(implementation)
                
                # Get job statistics
                job_stats = await conn.fetchrow(f"""
                    SELECT 
                        COUNT(*) as total_jobs,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_jobs,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
                        COUNT(CASE WHEN status = 'running' THEN 1 END) as running_jobs,
                        AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds
                    FROM real_time_intel.crawl_jobs 
                    {where_clause}
                """, *params)
                
                # Get article statistics
                article_stats = await conn.fetchrow(f"""
                    SELECT 
                        COUNT(*) as total_articles,
                        AVG(quality_score) as avg_quality_score,
                        COUNT(CASE WHEN quality_score >= 0.8 THEN 1 END) as high_quality_articles
                    FROM real_time_intel.extracted_articles ea
                    JOIN real_time_intel.crawl_jobs cj ON ea.job_id = cj.job_id
                    {where_clause}
                """, *params)
                
                return {
                    'period_hours': hours_back,
                    'jobs': dict(job_stats) if job_stats else {},
                    'articles': dict(article_stats) if article_stats else {},
                    'generated_at': datetime.now()
                }
                
        except Exception as e:
            logger.error(f"Failed to get crawler metrics: {e}")
            return {}
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """Clean up old crawl data."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            async with self.pool.acquire() as conn:
                # Delete old articles first (foreign key constraint)
                deleted_articles = await conn.fetchval("""
                    DELETE FROM real_time_intel.extracted_articles 
                    WHERE extracted_at < $1
                    RETURNING COUNT(*)
                """, cutoff_date)
                
                # Delete old jobs
                deleted_jobs = await conn.fetchval("""
                    DELETE FROM real_time_intel.crawl_jobs 
                    WHERE created_at < $1
                    RETURNING COUNT(*)
                """, cutoff_date)
                
                logger.info(f"Cleaned up {deleted_jobs} old jobs and {deleted_articles} old articles")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return False 