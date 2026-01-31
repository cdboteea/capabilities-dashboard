"""
DatabaseManager - Handles all database operations for the diff worker
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from uuid import UUID
import asyncpg
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)

class DatabaseManager:
    """
    Manages database connections and operations for the diff worker
    """
    
    def __init__(self, postgres_url: str):
        self.postgres_url = postgres_url
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self, max_attempts: int = 10, backoff_seconds: int = 3):
        """Initialize database connection pool with retry logic.

        The service containers often start at the same time as Postgres. If the
        database isn't ready yet the first connection attempt fails and the
        whole container exits. To make the worker more resilient we retry the
        connection a few times before giving up so the container can survive
        brief DB outages or cold starts.

        Args:
            max_attempts (int): How many attempts before raising.
            backoff_seconds (int): Seconds to wait between attempts.
        """

        attempt = 1
        while attempt <= max_attempts:
            try:
                self.pool = await asyncpg.create_pool(
                    self.postgres_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=60,
                    ssl="disable"  # Disable SSL for Docker environment
                )
                logger.info("Database connection pool created successfully", attempt=attempt)
                return
            except Exception as e:
                logger.warning(
                    "Database connection attempt failed – will retry",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=str(e)
                )
                if attempt == max_attempts:
                    logger.error("Exceeded max DB connection attempts", error=str(e))
                    raise
                await asyncio.sleep(backoff_seconds)
                attempt += 1
    
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.pool is not None and not self.pool._closed
    
    async def get_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Fetch an article by ID"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, topic_id, model_origin, title, body_md, 
                           word_count, created_at, metadata
                    FROM twin_report.articles 
                    WHERE id = $1
                """, article_id)
                
                if row:
                    return {
                        "id": str(row["id"]),
                        "topic_id": str(row["topic_id"]),
                        "model_origin": row["model_origin"],
                        "title": row["title"],
                        "body_md": row["body_md"],
                        "word_count": row["word_count"],
                        "created_at": row["created_at"],
                        "metadata": row["metadata"] or {}
                    }
                return None
                
        except Exception as e:
            logger.error("Failed to fetch article", article_id=article_id, error=str(e))
            raise
    
    async def get_articles_by_topic(self, topic_id: str) -> List[Dict[str, Any]]:
        """Fetch all articles for a topic"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, topic_id, model_origin, title, body_md, 
                           word_count, created_at, metadata
                    FROM twin_report.articles 
                    WHERE topic_id = $1
                    ORDER BY created_at DESC
                """, topic_id)
                
                articles = []
                for row in rows:
                    articles.append({
                        "id": str(row["id"]),
                        "topic_id": str(row["topic_id"]),
                        "model_origin": row["model_origin"],
                        "title": row["title"],
                        "body_md": row["body_md"],
                        "word_count": row["word_count"],
                        "created_at": row["created_at"],
                        "metadata": row["metadata"] or {}
                    })
                
                return articles
                
        except Exception as e:
            logger.error("Failed to fetch articles by topic", topic_id=topic_id, error=str(e))
            raise
    
    async def store_diff_result(self, diff_id: str, diff_result: Dict[str, Any]) -> bool:
        """Store a diff analysis result"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO twin_report.twin_diff (
                        id, twin_set_id, article_1_id, article_2_id, 
                        diff_jsonb, confidence_score, created_at, summary
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                    diff_id,
                    diff_result["metadata"]["twin_set_id"],
                    diff_result["metadata"]["article_1_info"]["id"],
                    diff_result["metadata"]["article_2_info"]["id"],
                    json.dumps(diff_result),
                    diff_result.get("confidence_score", 0.0),
                    datetime.utcnow(),
                    diff_result.get("summary", "")
                )
                
                logger.info("Diff result stored successfully", diff_id=diff_id)
                return True
                
        except Exception as e:
            logger.error("Failed to store diff result", diff_id=diff_id, error=str(e))
            raise
    
    async def store_gap_scan_result(self, gap_scan_id: str, gap_result: Dict[str, Any]) -> bool:
        """Store a gap scan analysis result"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO twin_report.gap_scan_results (
                        id, twin_set_id, result_jsonb, created_at, 
                        human_reviewed, priority_score
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """, 
                    gap_scan_id,
                    gap_result["analysis_metadata"]["twin_set_id"],
                    json.dumps(gap_result),
                    datetime.utcnow(),
                    False,  # Not yet reviewed by human
                    self._calculate_average_priority(gap_result.get("priorities", {}))
                )
                
                logger.info("Gap scan result stored successfully", gap_scan_id=gap_scan_id)
                return True
                
        except Exception as e:
            logger.error("Failed to store gap scan result", gap_scan_id=gap_scan_id, error=str(e))
            raise
    
    async def get_twin_set_diffs(self, twin_set_id: str) -> List[Dict[str, Any]]:
        """Get all diff analyses for a twin set"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, article_1_id, article_2_id, diff_jsonb, 
                           confidence_score, created_at, summary
                    FROM twin_report.twin_diff 
                    WHERE twin_set_id = $1
                    ORDER BY created_at DESC
                """, twin_set_id)
                
                diffs = []
                for row in rows:
                    diff_data = json.loads(row["diff_jsonb"])
                    diffs.append({
                        "id": str(row["id"]),
                        "article_1_id": str(row["article_1_id"]),
                        "article_2_id": str(row["article_2_id"]),
                        "summary": row["summary"],
                        "confidence_score": float(row["confidence_score"]),
                        "created_at": row["created_at"],
                        "gaps_count": len(diff_data.get("gaps", [])),
                        "overlaps_count": len(diff_data.get("overlaps", [])),
                        "contradictions_count": len(diff_data.get("contradictions", []))
                    })
                
                return diffs
                
        except Exception as e:
            logger.error("Failed to fetch twin set diffs", twin_set_id=twin_set_id, error=str(e))
            raise
    
    async def get_diff_result(self, diff_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific diff analysis result"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, twin_set_id, article_1_id, article_2_id, 
                           diff_jsonb, confidence_score, created_at, summary
                    FROM twin_report.twin_diff 
                    WHERE id = $1
                """, diff_id)
                
                if row:
                    diff_data = json.loads(row["diff_jsonb"])
                    return {
                        "id": str(row["id"]),
                        "twin_set_id": str(row["twin_set_id"]),
                        "article_1_id": str(row["article_1_id"]),
                        "article_2_id": str(row["article_2_id"]),
                        "summary": row["summary"],
                        "confidence_score": float(row["confidence_score"]),
                        "created_at": row["created_at"],
                        "full_analysis": diff_data
                    }
                return None
                
        except Exception as e:
            logger.error("Failed to fetch diff result", diff_id=diff_id, error=str(e))
            raise
    
    async def update_diff_quality_score(self, diff_id: str, quality_score: Dict[str, Any]) -> bool:
        """Update diff result with quality score"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            async with self.pool.acquire() as conn:
                # Get current diff data
                row = await conn.fetchrow("""
                    SELECT diff_jsonb FROM twin_report.twin_diff WHERE id = $1
                """, diff_id)
                
                if row:
                    diff_data = json.loads(row["diff_jsonb"])
                    diff_data["quality_assessment"] = quality_score
                    
                    # Update with quality assessment
                    await conn.execute("""
                        UPDATE twin_report.twin_diff 
                        SET diff_jsonb = $1 
                        WHERE id = $2
                    """, json.dumps(diff_data), diff_id)
                    
                    logger.info("Diff quality score updated", diff_id=diff_id)
                    return True
                
                return False
                
        except Exception as e:
            logger.error("Failed to update diff quality score", diff_id=diff_id, error=str(e))
            raise
    
    async def get_topic_info(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Get topic information"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, title, description, twin_set_id, 
                           status, generation_method, created_at, metadata
                    FROM twin_report.topics 
                    WHERE id = $1
                """, topic_id)
                
                if row:
                    return {
                        "id": str(row["id"]),
                        "title": row["title"],
                        "description": row["description"],
                        "twin_set_id": str(row["twin_set_id"]),
                        "status": row["status"],
                        "generation_method": row["generation_method"],
                        "created_at": row["created_at"],
                        "metadata": row["metadata"] or {}
                    }
                return None
                
        except Exception as e:
            logger.error("Failed to fetch topic info", topic_id=topic_id, error=str(e))
            raise
    
    async def store_quality_check(
        self, 
        article_id: str, 
        check_type: str, 
        quality_result: Dict[str, Any]
    ) -> str:
        """Store a quality check result"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            async with self.pool.acquire() as conn:
                quality_check_id = await conn.fetchval("""
                    INSERT INTO twin_report.quality_checks (
                        article_id, check_type, status, details_jsonb, 
                        checked_at, confidence_score
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                """, 
                    article_id,
                    check_type,
                    quality_result.get("quality_level", "unknown"),
                    json.dumps(quality_result),
                    datetime.utcnow(),
                    quality_result.get("overall_score", 0.0)
                )
                
                logger.info("Quality check stored", 
                           article_id=article_id, 
                           check_type=check_type,
                           quality_check_id=quality_check_id)
                
                return str(quality_check_id)
                
        except Exception as e:
            logger.error("Failed to store quality check", 
                        article_id=article_id, 
                        check_type=check_type, 
                        error=str(e))
            raise
    
    async def get_articles_for_gap_analysis(self, twin_set_id: str) -> List[Dict[str, Any]]:
        """Get all articles in a twin set for gap analysis"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT a.id, a.topic_id, a.model_origin, a.title, 
                           a.body_md, a.word_count, a.created_at, a.metadata
                    FROM twin_report.articles a
                    JOIN twin_report.topics t ON a.topic_id = t.id
                    WHERE t.twin_set_id = $1
                    ORDER BY a.created_at DESC
                """, twin_set_id)
                
                articles = []
                for row in rows:
                    articles.append({
                        "id": str(row["id"]),
                        "topic_id": str(row["topic_id"]),
                        "model_origin": row["model_origin"],
                        "title": row["title"],
                        "body_md": row["body_md"],
                        "word_count": row["word_count"],
                        "created_at": row["created_at"],
                        "metadata": row["metadata"] or {}
                    })
                
                return articles
                
        except Exception as e:
            logger.error("Failed to fetch articles for gap analysis", 
                        twin_set_id=twin_set_id, error=str(e))
            raise
    
    async def get_gap_scan_history(self, twin_set_id: str) -> List[Dict[str, Any]]:
        """Get gap scan history for a twin set"""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, result_jsonb, created_at, 
                           human_reviewed, priority_score
                    FROM twin_report.gap_scan_results 
                    WHERE twin_set_id = $1
                    ORDER BY created_at DESC
                    LIMIT 10
                """, twin_set_id)
                
                history = []
                for row in rows:
                    result_data = json.loads(row["result_jsonb"])
                    history.append({
                        "id": str(row["id"]),
                        "created_at": row["created_at"],
                        "human_reviewed": row["human_reviewed"],
                        "priority_score": float(row["priority_score"]),
                        "gaps_found": len(result_data.get("gaps", [])),
                        "recommendations_count": len(result_data.get("recommendations", []))
                    })
                
                return history
                
        except Exception as e:
            logger.error("Failed to fetch gap scan history", 
                        twin_set_id=twin_set_id, error=str(e))
            raise
    
    def _calculate_average_priority(self, priorities: Dict[str, float]) -> float:
        """Calculate average priority score"""
        if not priorities:
            return 0.5
        
        return sum(priorities.values()) / len(priorities)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        if not self.pool:
            return {"status": "disconnected", "error": "No connection pool"}
        
        try:
            async with self.pool.acquire() as conn:
                # Test basic connectivity
                result = await conn.fetchval("SELECT 1")
                
                # Check table existence
                tables_exist = await conn.fetchval("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'twin_report' 
                    AND table_name IN ('articles', 'twin_diff', 'gap_scan_results', 'quality_checks')
                """)
                
                return {
                    "status": "healthy",
                    "connection_test": result == 1,
                    "required_tables_exist": tables_exist == 4,
                    "pool_size": self.pool.get_size(),
                    "pool_max_size": self.pool.get_max_size()
                }
                
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "error", 
                "error": str(e)
            } 