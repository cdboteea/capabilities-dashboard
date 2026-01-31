"""
Database manager for Quality Controller
Handles quality check results storage and retrieval
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import asyncpg
import structlog
from sqlalchemy import text

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Database manager for quality check operations"""
    
    def __init__(self, postgres_url: str):
        self.postgres_url = postgres_url
        self.pool = None
    
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
                    ssl="disable"  # Disable SSL for Docker environment
                )
                
                # Create tables if they don't exist
                await self._create_tables()
                
                logger.info("Database connection pool initialized", attempt=attempt)
                return
            except Exception as e:
                logger.warning(
                    "DB init attempt failed – retrying",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=str(e)
                )
                if attempt == max_attempts:
                    logger.error("Exceeded max DB init attempts", error=str(e))
                    raise
                await asyncio.sleep(backoff_seconds)
                attempt += 1
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def store_quality_check_results(self, results: Dict[str, Any], request_data: Dict[str, Any]):
        """Store quality check results"""
        try:
            async with self.pool.acquire() as conn:
                query = """
                INSERT INTO quality_checks (
                    content_hash, overall_score, component_scores, 
                    results_data, request_data, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """
                
                import hashlib
                content_hash = hashlib.sha256(request_data.get("content", "").encode()).hexdigest()
                
                result = await conn.fetchrow(
                    query,
                    content_hash,
                    results.get("overall_score", 0.0),
                    json.dumps(results.get("component_scores", {})),
                    json.dumps(results),
                    json.dumps(request_data),
                    datetime.now(timezone.utc)
                )
                
                logger.info("Quality check results stored", id=result["id"])
                return result["id"]
                
        except Exception as e:
            logger.error("Failed to store quality check results", error=str(e))
            raise
    
    async def get_quality_check_results(self, check_id: str) -> Optional[Dict[str, Any]]:
        """Get quality check results by ID"""
        try:
            async with self.pool.acquire() as conn:
                query = """
                SELECT * FROM quality_checks WHERE id = $1
                """
                
                result = await conn.fetchrow(query, check_id)
                
                if result:
                    return {
                        "id": result["id"],
                        "content_hash": result["content_hash"],
                        "overall_score": result["overall_score"],
                        "component_scores": json.loads(result["component_scores"]),
                        "results_data": json.loads(result["results_data"]),
                        "request_data": json.loads(result["request_data"]),
                        "created_at": result["created_at"].isoformat()
                    }
                
                return None
                
        except Exception as e:
            logger.error("Failed to get quality check results", check_id=check_id, error=str(e))
            raise
    
    async def store_quality_check_result(self, report_id: str, results: Dict[str, Any], overall_score: float, quality_level: str):
        """Store quality check result for a report"""
        try:
            async with self.pool.acquire() as conn:
                query = """
                INSERT INTO report_quality_checks (
                    report_id, overall_score, quality_level, 
                    results_data, created_at
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (report_id) DO UPDATE SET
                    overall_score = EXCLUDED.overall_score,
                    quality_level = EXCLUDED.quality_level,
                    results_data = EXCLUDED.results_data,
                    updated_at = $5
                """
                
                await conn.execute(
                    query,
                    report_id,
                    overall_score,
                    quality_level,
                    json.dumps(results),
                    datetime.now(timezone.utc)
                )
                
                logger.info("Report quality check stored", report_id=report_id, quality_level=quality_level)
                
        except Exception as e:
            logger.error("Failed to store report quality check", report_id=report_id, error=str(e))
            raise
    
    async def _create_tables(self):
        """Create quality control tables"""
        
        create_quality_checks_table = """
        CREATE TABLE IF NOT EXISTS quality_checks (
            id SERIAL PRIMARY KEY,
            report_id VARCHAR(255) NOT NULL,
            overall_score FLOAT NOT NULL,
            quality_level VARCHAR(50) NOT NULL,
            fact_check_results JSONB,
            citation_verification JSONB,
            quality_assessment JSONB,
            source_evaluation JSONB,
            recommendations TEXT[],
            processing_time FLOAT,
            analysis_depth VARCHAR(20),
            check_types TEXT[],
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        create_quality_metrics_table = """
        CREATE TABLE IF NOT EXISTS quality_metrics (
            id SERIAL PRIMARY KEY,
            metric_date DATE NOT NULL UNIQUE,
            total_reports INTEGER DEFAULT 0,
            average_score FLOAT DEFAULT 0.0,
            quality_distribution JSONB DEFAULT '{}',
            common_issues JSONB DEFAULT '[]',
            processing_stats JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        create_fact_check_cache = """
        CREATE TABLE IF NOT EXISTS fact_check_cache (
            id SERIAL PRIMARY KEY,
            content_hash VARCHAR(64) NOT NULL UNIQUE,
            fact_check_results JSONB NOT NULL,
            confidence_score FLOAT,
            verified_claims INTEGER DEFAULT 0,
            unverified_claims INTEGER DEFAULT 0,
            contradictory_claims INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE
        );
        """
        
        create_citation_cache = """
        CREATE TABLE IF NOT EXISTS citation_cache (
            id SERIAL PRIMARY KEY,
            citation_hash VARCHAR(64) NOT NULL UNIQUE,
            citation_data JSONB NOT NULL,
            verification_status VARCHAR(20),
            accessibility_score FLOAT,
            credibility_score FLOAT,
            last_checked TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        # Create indexes
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_quality_checks_report_id ON quality_checks(report_id);",
            "CREATE INDEX IF NOT EXISTS idx_quality_checks_created_at ON quality_checks(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_quality_checks_score ON quality_checks(overall_score);",
            "CREATE INDEX IF NOT EXISTS idx_quality_metrics_date ON quality_metrics(metric_date);",
            "CREATE INDEX IF NOT EXISTS idx_fact_check_hash ON fact_check_cache(content_hash);",
            "CREATE INDEX IF NOT EXISTS idx_citation_hash ON citation_cache(citation_hash);"
        ]
        
        async with self.pool.acquire() as conn:
            await conn.execute(create_quality_checks_table)
            await conn.execute(create_quality_metrics_table)
            await conn.execute(create_fact_check_cache)
            await conn.execute(create_citation_cache)
            
            for index_sql in create_indexes:
                await conn.execute(index_sql)
        
        logger.info("Quality control database tables created/verified")
    
    async def store_quality_check_result(
        self,
        report_id: str,
        results: Dict[str, Any],
        overall_score: float,
        quality_level: str,
        processing_time: float = 0.0,
        analysis_depth: str = "standard",
        check_types: List[str] = None
    ) -> int:
        """Store quality check results"""
        
        insert_sql = """
        INSERT INTO quality_checks (
            report_id, overall_score, quality_level,
            fact_check_results, citation_verification,
            quality_assessment, source_evaluation,
            recommendations, processing_time,
            analysis_depth, check_types
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING id;
        """
        
        # Extract recommendations from results
        recommendations = []
        for result_type, result_data in results.items():
            if isinstance(result_data, dict) and "recommendations" in result_data:
                recommendations.extend(result_data["recommendations"])
        
        try:
            async with self.pool.acquire() as conn:
                result_id = await conn.fetchval(
                    insert_sql,
                    report_id,
                    overall_score,
                    quality_level,
                    json.dumps(results.get("fact_check_results", {})),
                    json.dumps(results.get("citation_verification", {})),
                    json.dumps(results.get("quality_assessment", {})),
                    json.dumps(results.get("source_evaluation", {})),
                    recommendations,
                    processing_time,
                    analysis_depth,
                    check_types or []
                )
                
                # Update daily metrics
                await self._update_daily_metrics(overall_score, quality_level)
                
                logger.info("Quality check result stored", 
                           report_id=report_id, result_id=result_id)
                
                return result_id
                
        except Exception as e:
            logger.error("Failed to store quality check result", 
                        report_id=report_id, error=str(e))
            raise
    
    async def get_quality_check_result(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get latest quality check result for a report"""
        
        query_sql = """
        SELECT * FROM quality_checks 
        WHERE report_id = $1 
        ORDER BY created_at DESC 
        LIMIT 1;
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query_sql, report_id)
                
                if row:
                    return {
                        "id": row["id"],
                        "report_id": row["report_id"],
                        "overall_score": row["overall_score"],
                        "quality_level": row["quality_level"],
                        "fact_check_results": json.loads(row["fact_check_results"] or "{}"),
                        "citation_verification": json.loads(row["citation_verification"] or "{}"),
                        "quality_assessment": json.loads(row["quality_assessment"] or "{}"),
                        "source_evaluation": json.loads(row["source_evaluation"] or "{}"),
                        "recommendations": row["recommendations"] or [],
                        "processing_time": row["processing_time"],
                        "analysis_depth": row["analysis_depth"],
                        "check_types": row["check_types"] or [],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"]
                    }
                
                return None
                
        except Exception as e:
            logger.error("Failed to get quality check result", 
                        report_id=report_id, error=str(e))
            raise
    
    async def get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics and statistics"""
        
        try:
            async with self.pool.acquire() as conn:
                # Get total reports processed
                total_reports = await conn.fetchval(
                    "SELECT COUNT(*) FROM quality_checks;"
                )
                
                # Get average quality score
                avg_score = await conn.fetchval(
                    "SELECT AVG(overall_score) FROM quality_checks;"
                ) or 0.0
                
                # Get quality distribution
                quality_dist_rows = await conn.fetch("""
                    SELECT quality_level, COUNT(*) as count 
                    FROM quality_checks 
                    GROUP BY quality_level;
                """)
                
                quality_distribution = {
                    row["quality_level"]: row["count"] 
                    for row in quality_dist_rows
                }
                
                # Get common issues from recommendations
                common_issues_rows = await conn.fetch("""
                    SELECT unnest(recommendations) as issue, COUNT(*) as frequency
                    FROM quality_checks 
                    WHERE recommendations IS NOT NULL
                    GROUP BY issue
                    ORDER BY frequency DESC
                    LIMIT 10;
                """)
                
                common_issues = [
                    {"issue": row["issue"], "frequency": row["frequency"]}
                    for row in common_issues_rows
                ]
                
                # Get processing statistics
                processing_stats = await conn.fetchrow("""
                    SELECT 
                        AVG(processing_time) as avg_processing_time,
                        MIN(processing_time) as min_processing_time,
                        MAX(processing_time) as max_processing_time,
                        COUNT(CASE WHEN analysis_depth = 'quick' THEN 1 END) as quick_analysis_count,
                        COUNT(CASE WHEN analysis_depth = 'standard' THEN 1 END) as standard_analysis_count,
                        COUNT(CASE WHEN analysis_depth = 'deep' THEN 1 END) as deep_analysis_count
                    FROM quality_checks;
                """)
                
                processing_stats_dict = {
                    "average_processing_time": float(processing_stats["avg_processing_time"] or 0),
                    "min_processing_time": float(processing_stats["min_processing_time"] or 0),
                    "max_processing_time": float(processing_stats["max_processing_time"] or 0),
                    "analysis_depth_distribution": {
                        "quick": processing_stats["quick_analysis_count"] or 0,
                        "standard": processing_stats["standard_analysis_count"] or 0,
                        "deep": processing_stats["deep_analysis_count"] or 0
                    }
                }
                
                return {
                    "total_reports_processed": total_reports,
                    "average_quality_score": float(avg_score),
                    "quality_distribution": quality_distribution,
                    "common_issues": common_issues,
                    "processing_stats": processing_stats_dict
                }
                
        except Exception as e:
            logger.error("Failed to get quality metrics", error=str(e))
            raise
    
    async def get_report_content(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get report content for reprocessing"""
        
        # This would typically query the main reports table
        # For now, return a placeholder structure
        query_sql = """
        SELECT content, sources, metadata 
        FROM twin_reports 
        WHERE id = $1;
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query_sql, report_id)
                
                if row:
                    return {
                        "content": row["content"],
                        "sources": json.loads(row["sources"] or "[]"),
                        "metadata": json.loads(row["metadata"] or "{}")
                    }
                
                # Fallback: return dummy data for testing
                return {
                    "content": f"Sample report content for {report_id}",
                    "sources": [],
                    "metadata": {"report_id": report_id}
                }
                
        except Exception as e:
            logger.warning("Failed to get report content, using fallback", 
                          report_id=report_id, error=str(e))
            return {
                "content": f"Sample report content for {report_id}",
                "sources": [],
                "metadata": {"report_id": report_id}
            }
    
    async def store_fact_check_cache(
        self,
        content_hash: str,
        fact_check_results: Dict[str, Any],
        expires_hours: int = 24
    ):
        """Store fact check results in cache"""
        
        insert_sql = """
        INSERT INTO fact_check_cache (
            content_hash, fact_check_results, confidence_score,
            verified_claims, unverified_claims, contradictory_claims,
            expires_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (content_hash) DO UPDATE SET
            fact_check_results = EXCLUDED.fact_check_results,
            confidence_score = EXCLUDED.confidence_score,
            verified_claims = EXCLUDED.verified_claims,
            unverified_claims = EXCLUDED.unverified_claims,
            contradictory_claims = EXCLUDED.contradictory_claims,
            expires_at = EXCLUDED.expires_at,
            created_at = NOW();
        """
        
        expires_at = datetime.now(timezone.utc).replace(
            hour=datetime.now().hour + expires_hours
        )
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    insert_sql,
                    content_hash,
                    json.dumps(fact_check_results),
                    fact_check_results.get("confidence_score", 0.5),
                    fact_check_results.get("verified_claims", 0),
                    fact_check_results.get("unverified_claims", 0),
                    fact_check_results.get("contradictory_claims", 0),
                    expires_at
                )
                
        except Exception as e:
            logger.error("Failed to store fact check cache", error=str(e))
    
    async def get_fact_check_cache(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached fact check results"""
        
        query_sql = """
        SELECT * FROM fact_check_cache 
        WHERE content_hash = $1 
        AND expires_at > NOW();
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query_sql, content_hash)
                
                if row:
                    return {
                        "fact_check_results": json.loads(row["fact_check_results"]),
                        "confidence_score": row["confidence_score"],
                        "verified_claims": row["verified_claims"],
                        "unverified_claims": row["unverified_claims"],
                        "contradictory_claims": row["contradictory_claims"],
                        "created_at": row["created_at"]
                    }
                
                return None
                
        except Exception as e:
            logger.error("Failed to get fact check cache", error=str(e))
            return None
    
    async def _update_daily_metrics(self, score: float, quality_level: str):
        """Update daily quality metrics"""
        
        today = datetime.now().date()
        
        upsert_sql = """
        INSERT INTO quality_metrics (metric_date, total_reports, average_score, quality_distribution)
        VALUES ($1, 1, $2, $3)
        ON CONFLICT (metric_date) DO UPDATE SET
            total_reports = quality_metrics.total_reports + 1,
            average_score = (quality_metrics.average_score * quality_metrics.total_reports + $2) / (quality_metrics.total_reports + 1),
            quality_distribution = quality_metrics.quality_distribution || $3,
            updated_at = NOW();
        """
        
        quality_dist = {quality_level: 1}
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    upsert_sql,
                    today,
                    score,
                    json.dumps(quality_dist)
                )
                
        except Exception as e:
            logger.error("Failed to update daily metrics", error=str(e)) 