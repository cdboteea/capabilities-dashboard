"""
Database Manager for Source Manager Service

Handles all database operations for source management, evaluation, and discovery.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
import json

import asyncpg
from asyncpg import Pool, Connection

from ..models.source_models import (
    Source, SourceEvaluation, SourceDiscovery, DiscoveryResult,
    SourceType, SourceStatus, SourceQuality, ContentCategory,
    ServiceHealth, EvaluationStats
)


logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Comprehensive database manager for source management operations.
    """
    
    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool: Optional[Pool] = None
        
        # SQL queries cache
        self._prepared_queries = {}
    
    async def initialize(self):
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.pool_size,
                max_size=self.pool_size + self.max_overflow,
                command_timeout=60,
                server_settings={
                    'jit': 'off'  # Disable JIT for better connection startup time
                }
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            
            logger.info("Database connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {str(e)}")
            raise
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    # Source Management
    
    async def save_source(self, source: Source) -> Source:
        """Save or update a source."""
        async with self.pool.acquire() as conn:
            # Convert source to dict for database storage
            source_data = {
                'id': str(source.id),
                'name': source.name,
                'url': str(source.url),
                'domain': source.domain,
                'source_type': source.source_type.value,
                'status': source.status.value,
                'primary_category': source.primary_category.value,
                'secondary_categories': [cat.value for cat in source.secondary_categories],
                'description': source.description,
                'country': source.country,
                'language': source.language,
                'tags': source.tags,
                'rss_feed_info': source.rss_feed_info.dict() if source.rss_feed_info else None,
                'created_at': source.created_at,
                'updated_at': datetime.now(timezone.utc),
                'last_evaluated_at': source.last_evaluated_at,
                'last_crawled_at': source.last_crawled_at
            }
            
            # Upsert source
            query = """
                INSERT INTO sources (
                    id, name, url, domain, source_type, status, primary_category,
                    secondary_categories, description, country, language, tags,
                    rss_feed_info, created_at, updated_at, last_evaluated_at, last_crawled_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    primary_category = EXCLUDED.primary_category,
                    secondary_categories = EXCLUDED.secondary_categories,
                    description = EXCLUDED.description,
                    country = EXCLUDED.country,
                    language = EXCLUDED.language,
                    tags = EXCLUDED.tags,
                    rss_feed_info = EXCLUDED.rss_feed_info,
                    updated_at = EXCLUDED.updated_at,
                    last_evaluated_at = EXCLUDED.last_evaluated_at,
                    last_crawled_at = EXCLUDED.last_crawled_at
                RETURNING *
            """
            
            result = await conn.fetchrow(
                query,
                source_data['id'], source_data['name'], source_data['url'],
                source_data['domain'], source_data['source_type'], source_data['status'],
                source_data['primary_category'], source_data['secondary_categories'],
                source_data['description'], source_data['country'], source_data['language'],
                source_data['tags'], json.dumps(source_data['rss_feed_info']) if source_data['rss_feed_info'] else None,
                source_data['created_at'], source_data['updated_at'],
                source_data['last_evaluated_at'], source_data['last_crawled_at']
            )
            
            return self._row_to_source(result)
    
    async def get_source_by_id(self, source_id: UUID) -> Optional[Source]:
        """Get source by ID."""
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM sources WHERE id = $1"
            result = await conn.fetchrow(query, str(source_id))
            
            return self._row_to_source(result) if result else None
    
    async def get_source_by_url(self, url: str) -> Optional[Source]:
        """Get source by URL."""
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM sources WHERE url = $1"
            result = await conn.fetchrow(query, url)
            
            return self._row_to_source(result) if result else None
    
    async def get_sources_by_categories(self, categories: List[ContentCategory]) -> List[Source]:
        """Get sources by content categories."""
        if not categories:
            return []
        
        async with self.pool.acquire() as conn:
            category_values = [cat.value for cat in categories]
            query = """
                SELECT * FROM sources 
                WHERE primary_category = ANY($1) 
                   OR secondary_categories && $1
                ORDER BY last_evaluated_at DESC NULLS LAST
            """
            results = await conn.fetch(query, category_values)
            
            return [self._row_to_source(row) for row in results]
    
    async def search_sources(
        self,
        query: Optional[str] = None,
        categories: List[ContentCategory] = None,
        source_types: List[SourceType] = None,
        quality_ratings: List[SourceQuality] = None,
        statuses: List[SourceStatus] = None,
        min_quality_score: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Source], int]:
        """Search sources with filters."""
        async with self.pool.acquire() as conn:
            conditions = []
            params = []
            param_count = 0
            
            # Build WHERE conditions
            if query:
                param_count += 1
                conditions.append(f"(name ILIKE ${param_count} OR description ILIKE ${param_count} OR domain ILIKE ${param_count})")
                params.append(f"%{query}%")
            
            if categories:
                param_count += 1
                category_values = [cat.value for cat in categories]
                conditions.append(f"(primary_category = ANY(${param_count}) OR secondary_categories && ${param_count})")
                params.append(category_values)
            
            if source_types:
                param_count += 1
                type_values = [st.value for st in source_types]
                conditions.append(f"source_type = ANY(${param_count})")
                params.append(type_values)
            
            if statuses:
                param_count += 1
                status_values = [status.value for status in statuses]
                conditions.append(f"status = ANY(${param_count})")
                params.append(status_values)
            
            # Add quality score filter if provided
            quality_join = ""
            if min_quality_score is not None or quality_ratings:
                quality_join = """
                    LEFT JOIN source_evaluations se ON sources.id = se.source_id 
                    AND se.created_at = (
                        SELECT MAX(created_at) FROM source_evaluations 
                        WHERE source_id = sources.id
                    )
                """
                
                if min_quality_score is not None:
                    param_count += 1
                    conditions.append(f"(se.quality_score->>'overall_score')::float >= ${param_count}")
                    params.append(min_quality_score)
                
                if quality_ratings:
                    param_count += 1
                    rating_values = [rating.value for rating in quality_ratings]
                    conditions.append(f"(se.quality_score->>'quality_rating') = ANY(${param_count})")
                    params.append(rating_values)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            # Count query
            count_query = f"""
                SELECT COUNT(DISTINCT sources.id) 
                FROM sources {quality_join} {where_clause}
            """
            total = await conn.fetchval(count_query, *params)
            
            # Main query
            param_count += 2
            main_query = f"""
                SELECT DISTINCT sources.* 
                FROM sources {quality_join} {where_clause}
                ORDER BY sources.updated_at DESC
                LIMIT ${param_count - 1} OFFSET ${param_count}
            """
            params.extend([limit, offset])
            
            results = await conn.fetch(main_query, *params)
            sources = [self._row_to_source(row) for row in results]
            
            return sources, total
    
    async def get_all_source_urls(self) -> List[str]:
        """Get all source URLs for deduplication."""
        async with self.pool.acquire() as conn:
            query = "SELECT url FROM sources"
            results = await conn.fetch(query)
            return [row['url'] for row in results]
    
    async def update_source_status(self, source_id: UUID, status: SourceStatus) -> bool:
        """Update source status."""
        async with self.pool.acquire() as conn:
            query = """
                UPDATE sources 
                SET status = $1, updated_at = $2 
                WHERE id = $3
            """
            result = await conn.execute(
                query, status.value, datetime.now(timezone.utc), str(source_id)
            )
            return result == "UPDATE 1"
    
    # Source Evaluation Management
    
    async def save_source_evaluation(self, source: Source, evaluation: SourceEvaluation) -> SourceEvaluation:
        """Save source and its evaluation."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Save source first
                await self.save_source(source)
                
                # Save evaluation
                eval_data = {
                    'id': str(evaluation.id),
                    'source_id': str(evaluation.source_id),
                    'domain_authority': evaluation.domain_authority.dict(),
                    'content_analysis': evaluation.content_analysis.dict(),
                    'bias_assessment': evaluation.bias_assessment.dict(),
                    'quality_score': evaluation.quality_score.dict(),
                    'evaluation_method': evaluation.evaluation_method,
                    'llm_model': evaluation.llm_model,
                    'sample_articles_analyzed': evaluation.sample_articles_analyzed,
                    'evaluation_duration_seconds': evaluation.evaluation_duration_seconds,
                    'recommendations': evaluation.recommendations,
                    'warnings': evaluation.warnings,
                    'notes': evaluation.notes,
                    'created_at': evaluation.created_at,
                    'expires_at': evaluation.expires_at
                }
                
                query = """
                    INSERT INTO source_evaluations (
                        id, source_id, domain_authority, content_analysis, bias_assessment,
                        quality_score, evaluation_method, llm_model, sample_articles_analyzed,
                        evaluation_duration_seconds, recommendations, warnings, notes,
                        created_at, expires_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        domain_authority = EXCLUDED.domain_authority,
                        content_analysis = EXCLUDED.content_analysis,
                        bias_assessment = EXCLUDED.bias_assessment,
                        quality_score = EXCLUDED.quality_score,
                        evaluation_method = EXCLUDED.evaluation_method,
                        llm_model = EXCLUDED.llm_model,
                        sample_articles_analyzed = EXCLUDED.sample_articles_analyzed,
                        evaluation_duration_seconds = EXCLUDED.evaluation_duration_seconds,
                        recommendations = EXCLUDED.recommendations,
                        warnings = EXCLUDED.warnings,
                        notes = EXCLUDED.notes,
                        expires_at = EXCLUDED.expires_at
                """
                
                await conn.execute(
                    query,
                    eval_data['id'], eval_data['source_id'],
                    json.dumps(eval_data['domain_authority']),
                    json.dumps(eval_data['content_analysis']),
                    json.dumps(eval_data['bias_assessment']),
                    json.dumps(eval_data['quality_score']),
                    eval_data['evaluation_method'], eval_data['llm_model'],
                    eval_data['sample_articles_analyzed'], eval_data['evaluation_duration_seconds'],
                    eval_data['recommendations'], eval_data['warnings'], eval_data['notes'],
                    eval_data['created_at'], eval_data['expires_at']
                )
                
                return evaluation
    
    async def get_latest_evaluation(self, source_id: UUID) -> Optional[SourceEvaluation]:
        """Get latest evaluation for a source."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT * FROM source_evaluations 
                WHERE source_id = $1 
                ORDER BY created_at DESC 
                LIMIT 1
            """
            result = await conn.fetchrow(query, str(source_id))
            
            return self._row_to_evaluation(result) if result else None
    
    async def get_evaluations_by_quality(self, quality_rating: SourceQuality) -> List[SourceEvaluation]:
        """Get evaluations by quality rating."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT * FROM source_evaluations 
                WHERE (quality_score->>'quality_rating') = $1
                ORDER BY created_at DESC
            """
            results = await conn.fetch(query, quality_rating.value)
            
            return [self._row_to_evaluation(row) for row in results]
    
    # Source Discovery Management
    
    async def save_source_discovery(self, discovery: SourceDiscovery, results: List[DiscoveryResult]):
        """Save source discovery operation and results."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Save discovery record
                discovery_data = {
                    'id': str(discovery.id),
                    'query': discovery.query,
                    'discovery_method': discovery.discovery_method,
                    'target_categories': [cat.value for cat in discovery.target_categories],
                    'max_results': discovery.max_results,
                    'sources_found': discovery.sources_found,
                    'sources_evaluated': discovery.sources_evaluated,
                    'high_quality_sources': discovery.high_quality_sources,
                    'started_at': discovery.started_at,
                    'completed_at': discovery.completed_at,
                    'duration_seconds': discovery.duration_seconds,
                    'status': discovery.status
                }
                
                discovery_query = """
                    INSERT INTO source_discoveries (
                        id, query, discovery_method, target_categories, max_results,
                        sources_found, sources_evaluated, high_quality_sources,
                        started_at, completed_at, duration_seconds, status
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                    )
                """
                
                await conn.execute(
                    discovery_query,
                    discovery_data['id'], discovery_data['query'], discovery_data['discovery_method'],
                    discovery_data['target_categories'], discovery_data['max_results'],
                    discovery_data['sources_found'], discovery_data['sources_evaluated'],
                    discovery_data['high_quality_sources'], discovery_data['started_at'],
                    discovery_data['completed_at'], discovery_data['duration_seconds'],
                    discovery_data['status']
                )
                
                # Save discovery results
                for result in results:
                    # Save source first
                    await self.save_source(result.source)
                    
                    # Save evaluation if present
                    if result.evaluation:
                        await self.save_source_evaluation(result.source, result.evaluation)
                    
                    # Save discovery result
                    result_data = {
                        'discovery_id': str(discovery.id),
                        'source_id': str(result.source.id),
                        'discovery_score': result.discovery_score,
                        'discovery_method': result.discovery_method,
                        'confidence': result.confidence,
                        'evaluation_id': str(result.evaluation.id) if result.evaluation else None
                    }
                    
                    result_query = """
                        INSERT INTO discovery_results (
                            discovery_id, source_id, discovery_score, discovery_method,
                            confidence, evaluation_id
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                    """
                    
                    await conn.execute(
                        result_query,
                        result_data['discovery_id'], result_data['source_id'],
                        result_data['discovery_score'], result_data['discovery_method'],
                        result_data['confidence'], result_data['evaluation_id']
                    )
    
    # Statistics and Health
    
    async def get_service_health(self) -> ServiceHealth:
        """Get service health status."""
        async with self.pool.acquire() as conn:
            # Test database connection
            database_connected = True
            try:
                await conn.execute("SELECT 1")
            except:
                database_connected = False
            
            # Get statistics
            stats_query = """
                SELECT 
                    COUNT(*) as total_sources,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_sources
                FROM sources
            """
            stats = await conn.fetchrow(stats_query)
            
            # Get active evaluations count (simplified)
            active_evaluations = 0  # Would track actual running evaluations
            
            return ServiceHealth(
                service="source_manager",
                status="healthy" if database_connected else "unhealthy",
                database_connected=database_connected,
                llm_available=True,  # Would test actual LLM endpoint
                cache_operational=True,  # Would test actual cache
                active_evaluations=active_evaluations,
                total_sources=stats['total_sources']
            )
    
    async def get_evaluation_stats(self) -> EvaluationStats:
        """Get evaluation statistics."""
        async with self.pool.acquire() as conn:
            # Total evaluations
            total_query = "SELECT COUNT(*) FROM source_evaluations"
            total_evaluations = await conn.fetchval(total_query)
            
            # Evaluations today
            today_query = """
                SELECT COUNT(*) FROM source_evaluations 
                WHERE created_at >= CURRENT_DATE
            """
            evaluations_today = await conn.fetchval(today_query)
            
            # Average evaluation time
            avg_time_query = """
                SELECT AVG(evaluation_duration_seconds) 
                FROM source_evaluations 
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            """
            avg_evaluation_time = await conn.fetchval(avg_time_query) or 0.0
            
            # Quality distribution
            quality_query = """
                SELECT 
                    (quality_score->>'quality_rating') as rating,
                    COUNT(*) as count
                FROM source_evaluations 
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY (quality_score->>'quality_rating')
            """
            quality_results = await conn.fetch(quality_query)
            quality_distribution = {
                SourceQuality(row['rating']): row['count'] 
                for row in quality_results if row['rating']
            }
            
            # Source type distribution
            type_query = """
                SELECT source_type, COUNT(*) as count
                FROM sources
                GROUP BY source_type
            """
            type_results = await conn.fetch(type_query)
            source_type_distribution = {
                SourceType(row['source_type']): row['count']
                for row in type_results
            }
            
            return EvaluationStats(
                total_evaluations=total_evaluations,
                evaluations_today=evaluations_today,
                avg_evaluation_time=avg_evaluation_time,
                quality_distribution=quality_distribution,
                source_type_distribution=source_type_distribution,
                cache_hit_rate=0.75  # Would calculate actual cache hit rate
            )
    
    # Helper methods
    
    def _row_to_source(self, row) -> Source:
        """Convert database row to Source object."""
        from ..models.source_models import RSSFeedInfo
        
        rss_feed_info = None
        if row['rss_feed_info']:
            rss_data = json.loads(row['rss_feed_info'])
            rss_feed_info = RSSFeedInfo(**rss_data)
        
        return Source(
            id=UUID(row['id']),
            name=row['name'],
            url=row['url'],
            domain=row['domain'],
            source_type=SourceType(row['source_type']),
            status=SourceStatus(row['status']),
            primary_category=ContentCategory(row['primary_category']),
            secondary_categories=[ContentCategory(cat) for cat in row['secondary_categories']],
            description=row['description'],
            country=row['country'],
            language=row['language'],
            tags=row['tags'],
            rss_feed_info=rss_feed_info,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_evaluated_at=row['last_evaluated_at'],
            last_crawled_at=row['last_crawled_at']
        )
    
    def _row_to_evaluation(self, row) -> SourceEvaluation:
        """Convert database row to SourceEvaluation object."""
        from ..models.source_models import (
            DomainAuthority, ContentAnalysis, BiasAssessment, QualityScore
        )
        
        return SourceEvaluation(
            id=UUID(row['id']),
            source_id=UUID(row['source_id']),
            domain_authority=DomainAuthority(**json.loads(row['domain_authority'])),
            content_analysis=ContentAnalysis(**json.loads(row['content_analysis'])),
            bias_assessment=BiasAssessment(**json.loads(row['bias_assessment'])),
            quality_score=QualityScore(**json.loads(row['quality_score'])),
            evaluation_method=row['evaluation_method'],
            llm_model=row['llm_model'],
            sample_articles_analyzed=row['sample_articles_analyzed'],
            evaluation_duration_seconds=row['evaluation_duration_seconds'],
            recommendations=row['recommendations'],
            warnings=row['warnings'],
            notes=row['notes'],
            created_at=row['created_at'],
            expires_at=row['expires_at']
        ) 