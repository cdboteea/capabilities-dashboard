"""
Database Manager for Event Processor Service
"""

import asyncio
import asyncpg
import json
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from contextlib import asynccontextmanager

from ..models import (
    NewsEvent, ProcessingStatus, EventType, EventSeverity, EventUrgency,
    EventQuery, ProcessingStatsResponse
)

logger = structlog.get_logger(__name__)

class DatabaseManager:
    """Async PostgreSQL database manager for Event Processor"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None
        
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            logger.info("Initializing database connection pool")
            
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=5,
                max_size=20,
                command_timeout=60,
                server_settings={
                    'application_name': 'event_processor',
                    'timezone': 'UTC'
                }
            )
            
            # Verify connection
            async with self.pool.acquire() as connection:
                await connection.execute('SELECT 1')
            
            logger.info("Database connection pool initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize database connection pool", error=str(e))
            raise
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def store_event(self, event: NewsEvent) -> str:
        """Store processed news event"""
        try:
            async with self.get_connection() as conn:
                # Insert main event record
                event_id = await conn.fetchval("""
                    INSERT INTO processed_events (
                        event_id, article_id, source_id, title, content, summary, url,
                        published_at, discovered_at, author, status, processing_version,
                        created_at, updated_at, created_by, updated_by
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
                    ) RETURNING event_id
                """, 
                event.event_id, event.article_id, event.source_id, event.title, 
                event.content, event.summary, event.url, event.published_at, 
                event.discovered_at, event.author, event.status.value, 
                event.processing_version, event.created_at, event.updated_at,
                event.created_by, event.updated_by)
                
                # Store classification if available
                if event.classification:
                    await conn.execute("""
                        INSERT INTO event_classifications (
                            event_id, event_type, confidence, confidence_level,
                            primary_indicators, secondary_indicators, alternative_types,
                            reasoning, model_used, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    event.event_id, event.classification.event_type.value,
                    event.classification.confidence, event.classification.confidence_level.value,
                    json.dumps(event.classification.primary_indicators),
                    json.dumps(event.classification.secondary_indicators),
                    json.dumps(event.classification.alternative_types),
                    event.classification.reasoning, event.classification.model_used,
                    datetime.now())
                
                # Store severity assessment if available
                if event.severity_assessment:
                    await conn.execute("""
                        INSERT INTO event_severity_assessments (
                            event_id, severity, urgency, market_impact_score,
                            company_impact_score, time_sensitivity_score, stakeholder_impact_score,
                            overall_severity_score, confidence, assessment_factors,
                            reasoning, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                    event.event_id, event.severity_assessment.severity.value,
                    event.severity_assessment.urgency.value,
                    event.severity_assessment.market_impact_score,
                    event.severity_assessment.company_impact_score,
                    event.severity_assessment.time_sensitivity_score,
                    event.severity_assessment.stakeholder_impact_score,
                    event.severity_assessment.overall_severity_score,
                    event.severity_assessment.confidence,
                    json.dumps(event.severity_assessment.assessment_factors),
                    event.severity_assessment.reasoning, datetime.now())
                
                # Store entities if available
                if event.entities:
                    for entity in event.entities:
                        await conn.execute("""
                            INSERT INTO event_entities (
                                event_id, entity_id, entity_type, entity_value, confidence,
                                start_pos, end_pos, context, ticker_symbol, exchange,
                                sector, market_cap, created_at
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        """,
                        event.event_id, entity.entity_id, entity.entity_type,
                        entity.entity_value, entity.confidence, entity.start_pos,
                        entity.end_pos, entity.context, entity.ticker_symbol,
                        entity.exchange, entity.sector, entity.market_cap,
                        datetime.now())
                
                # Store enrichment data if available
                if event.enrichment:
                    await conn.execute("""
                        INSERT INTO event_enrichments (
                            event_id, sentiment_score, sentiment_label, emotion_scores,
                            language, readability_score, complexity_score, word_count,
                            sentence_count, paragraph_count, topics, keywords,
                            financial_metrics, price_targets, content_quality_score,
                            credibility_score, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                    """,
                    event.event_id, event.enrichment.sentiment_score,
                    event.enrichment.sentiment_label,
                    json.dumps(event.enrichment.emotion_scores),
                    event.enrichment.language, event.enrichment.readability_score,
                    event.enrichment.complexity_score, event.enrichment.word_count,
                    event.enrichment.sentence_count, event.enrichment.paragraph_count,
                    json.dumps(event.enrichment.topics),
                    json.dumps(event.enrichment.keywords),
                    json.dumps(event.enrichment.financial_metrics),
                    json.dumps(event.enrichment.price_targets),
                    event.enrichment.content_quality_score,
                    event.enrichment.credibility_score, datetime.now())
                
                # Store routing decision if available
                if event.routing:
                    await conn.execute("""
                        INSERT INTO event_routing (
                            event_id, primary_destination, secondary_destinations,
                            routing_score, routing_criteria, portfolio_relevance,
                            affected_holdings, delivery_method, priority_level,
                            delivery_delay, expiry_time, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                    event.event_id, event.routing.primary_destination,
                    json.dumps(event.routing.secondary_destinations),
                    event.routing.routing_score,
                    json.dumps(event.routing.routing_criteria),
                    event.routing.portfolio_relevance,
                    json.dumps(event.routing.affected_holdings),
                    event.routing.delivery_method, event.routing.priority_level,
                    event.routing.delivery_delay, event.routing.expiry_time,
                    datetime.now())
                
                # Store processing metrics if available
                if event.processing_metrics:
                    await conn.execute("""
                        INSERT INTO event_processing_metrics (
                            event_id, processing_start_time, processing_end_time,
                            total_processing_time, classification_time, enrichment_time,
                            routing_time, memory_usage, cpu_usage, processing_quality_score,
                            error_count, retry_count, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """,
                    event.event_id, event.processing_metrics.processing_start_time,
                    event.processing_metrics.processing_end_time,
                    event.processing_metrics.total_processing_time,
                    event.processing_metrics.classification_time,
                    event.processing_metrics.enrichment_time,
                    event.processing_metrics.routing_time,
                    event.processing_metrics.memory_usage,
                    event.processing_metrics.cpu_usage,
                    event.processing_metrics.processing_quality_score,
                    event.processing_metrics.error_count,
                    event.processing_metrics.retry_count, datetime.now())
                
                logger.info("Event stored successfully", event_id=event_id)
                return event_id
                
        except Exception as e:
            logger.error("Failed to store event", error=str(e), event_id=event.event_id)
            raise
    
    async def get_event(self, event_id: str) -> Optional[NewsEvent]:
        """Retrieve event by ID"""
        try:
            async with self.get_connection() as conn:
                # Get main event record
                event_row = await conn.fetchrow("""
                    SELECT * FROM processed_events WHERE event_id = $1
                """, event_id)
                
                if not event_row:
                    return None
                
                # Build event object
                event = NewsEvent(
                    event_id=event_row['event_id'],
                    article_id=event_row['article_id'],
                    source_id=event_row['source_id'],
                    title=event_row['title'],
                    content=event_row['content'],
                    summary=event_row['summary'],
                    url=event_row['url'],
                    published_at=event_row['published_at'],
                    discovered_at=event_row['discovered_at'],
                    author=event_row['author'],
                    status=ProcessingStatus(event_row['status']),
                    processing_version=event_row['processing_version'],
                    error_details=event_row.get('error_details'),
                    created_at=event_row['created_at'],
                    updated_at=event_row['updated_at'],
                    created_by=event_row['created_by'],
                    updated_by=event_row['updated_by']
                )
                
                # Get related data (classification, entities, etc.)
                await self._load_event_relations(conn, event)
                
                return event
                
        except Exception as e:
            logger.error("Failed to retrieve event", error=str(e), event_id=event_id)
            return None
    
    async def update_event_status(self, event_id: str, status: ProcessingStatus, error_details: Optional[str] = None):
        """Update event processing status"""
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    UPDATE processed_events 
                    SET status = $2, error_details = $3, updated_at = $4
                    WHERE event_id = $1
                """, event_id, status.value, error_details, datetime.now())
                
                logger.info("Event status updated", event_id=event_id, status=status.value)
                
        except Exception as e:
            logger.error("Failed to update event status", error=str(e), event_id=event_id)
            raise
    
    async def search_events(self, query: EventQuery) -> List[NewsEvent]:
        """Search events with filters"""
        try:
            async with self.get_connection() as conn:
                # Build dynamic query
                where_conditions = ["1=1"]
                params = []
                param_count = 0
                
                if query.start_date:
                    param_count += 1
                    where_conditions.append(f"published_at >= ${param_count}")
                    params.append(query.start_date)
                
                if query.end_date:
                    param_count += 1
                    where_conditions.append(f"published_at <= ${param_count}")
                    params.append(query.end_date)
                
                if query.event_types:
                    param_count += 1
                    where_conditions.append(f"""
                        event_id IN (
                            SELECT event_id FROM event_classifications 
                            WHERE event_type = ANY(${param_count})
                        )
                    """)
                    params.append([et.value for et in query.event_types])
                
                if query.severity_levels:
                    param_count += 1
                    where_conditions.append(f"""
                        event_id IN (
                            SELECT event_id FROM event_severity_assessments 
                            WHERE severity = ANY(${param_count})
                        )
                    """)
                    params.append([sl.value for sl in query.severity_levels])
                
                if query.tickers:
                    param_count += 1
                    where_conditions.append(f"""
                        event_id IN (
                            SELECT event_id FROM event_entities 
                            WHERE ticker_symbol = ANY(${param_count})
                        )
                    """)
                    params.append(query.tickers)
                
                if query.keywords:
                    param_count += 1
                    keyword_conditions = []
                    for keyword in query.keywords:
                        keyword_conditions.append(f"(title ILIKE '%{keyword}%' OR content ILIKE '%{keyword}%')")
                    where_conditions.append(f"({' OR '.join(keyword_conditions)})")
                
                # Build full query
                where_clause = " AND ".join(where_conditions)
                
                # Add pagination
                offset = (query.page - 1) * query.page_size
                param_count += 1
                limit_clause = f"LIMIT ${param_count}"
                params.append(query.page_size)
                
                param_count += 1
                offset_clause = f"OFFSET ${param_count}"
                params.append(offset)
                
                # Order by clause
                order_clause = f"ORDER BY {query.sort_by} {query.sort_order.upper()}"
                
                sql = f"""
                    SELECT * FROM processed_events 
                    WHERE {where_clause}
                    {order_clause}
                    {limit_clause}
                    {offset_clause}
                """
                
                rows = await conn.fetch(sql, *params)
                
                # Convert to NewsEvent objects
                events = []
                for row in rows:
                    event = NewsEvent(
                        event_id=row['event_id'],
                        article_id=row['article_id'],
                        source_id=row['source_id'],
                        title=row['title'],
                        content=row['content'],
                        summary=row['summary'],
                        url=row['url'],
                        published_at=row['published_at'],
                        discovered_at=row['discovered_at'],
                        author=row['author'],
                        status=ProcessingStatus(row['status']),
                        processing_version=row['processing_version'],
                        error_details=row.get('error_details'),
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        created_by=row['created_by'],
                        updated_by=row['updated_by']
                    )
                    
                    # Load relations for each event
                    await self._load_event_relations(conn, event)
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error("Failed to search events", error=str(e))
            return []
    
    async def get_event_count(self, query: EventQuery) -> int:
        """Get total count of events matching query"""
        try:
            async with self.get_connection() as conn:
                # Build count query (similar to search but without pagination)
                where_conditions = ["1=1"]
                params = []
                param_count = 0
                
                if query.start_date:
                    param_count += 1
                    where_conditions.append(f"published_at >= ${param_count}")
                    params.append(query.start_date)
                
                if query.end_date:
                    param_count += 1
                    where_conditions.append(f"published_at <= ${param_count}")
                    params.append(query.end_date)
                
                # Add other filters as needed...
                
                where_clause = " AND ".join(where_conditions)
                sql = f"SELECT COUNT(*) FROM processed_events WHERE {where_clause}"
                
                count = await conn.fetchval(sql, *params)
                return count or 0
                
        except Exception as e:
            logger.error("Failed to get event count", error=str(e))
            return 0
    
    async def get_processing_stats(self) -> ProcessingStatsResponse:
        """Get processing statistics"""
        try:
            async with self.get_connection() as conn:
                # Get basic counts
                total_events = await conn.fetchval("""
                    SELECT COUNT(*) FROM processed_events
                """) or 0
                
                events_today = await conn.fetchval("""
                    SELECT COUNT(*) FROM processed_events 
                    WHERE created_at >= CURRENT_DATE
                """) or 0
                
                # Get average processing time
                avg_processing_time = await conn.fetchval("""
                    SELECT AVG(total_processing_time) 
                    FROM event_processing_metrics 
                    WHERE total_processing_time IS NOT NULL
                """) or 0.0
                
                # Get status distribution
                status_rows = await conn.fetch("""
                    SELECT status, COUNT(*) as count 
                    FROM processed_events 
                    GROUP BY status
                """)
                
                status_distribution = {row['status']: row['count'] for row in status_rows}
                
                # Get event type distribution
                type_rows = await conn.fetch("""
                    SELECT ec.event_type, COUNT(*) as count
                    FROM event_classifications ec
                    JOIN processed_events pe ON ec.event_id = pe.event_id
                    WHERE pe.created_at >= CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY ec.event_type
                """)
                
                event_type_distribution = {row['event_type']: row['count'] for row in type_rows}
                
                # Get severity distribution
                severity_rows = await conn.fetch("""
                    SELECT esa.severity, COUNT(*) as count
                    FROM event_severity_assessments esa
                    JOIN processed_events pe ON esa.event_id = pe.event_id
                    WHERE pe.created_at >= CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY esa.severity
                """)
                
                severity_distribution = {row['severity']: row['count'] for row in severity_rows}
                
                # Calculate throughput
                events_per_hour = events_today / 24.0 if events_today > 0 else 0.0
                
                # Get error rate
                error_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM processed_events 
                    WHERE status = 'failed' AND created_at >= CURRENT_DATE
                """) or 0
                
                error_rate = (error_count / events_today) if events_today > 0 else 0.0
                
                # Mock additional metrics
                classification_accuracy = 0.85
                average_confidence = 0.78
                retry_rate = 0.05
                
                system_performance = {
                    'memory_usage': 65.2,
                    'cpu_usage': 23.8,
                    'database_connections': 12,
                    'queue_depth': 45
                }
                
                return ProcessingStatsResponse(
                    events_processed_today=events_today,
                    events_processed_total=total_events,
                    average_processing_time=avg_processing_time,
                    events_per_hour=events_per_hour,
                    classification_accuracy=classification_accuracy,
                    average_confidence=average_confidence,
                    status_distribution=status_distribution,
                    event_type_distribution=event_type_distribution,
                    severity_distribution=severity_distribution,
                    system_performance=system_performance,
                    error_rate=error_rate,
                    retry_rate=retry_rate
                )
                
        except Exception as e:
            logger.error("Failed to get processing stats", error=str(e))
            # Return default stats
            return ProcessingStatsResponse(
                events_processed_today=0,
                events_processed_total=0,
                average_processing_time=0.0,
                events_per_hour=0.0,
                classification_accuracy=0.0,
                average_confidence=0.0,
                status_distribution={},
                event_type_distribution={},
                severity_distribution={},
                system_performance={},
                error_rate=0.0,
                retry_rate=0.0
            )
    
    async def _load_event_relations(self, conn, event: NewsEvent):
        """Load related data for an event"""
        # Load classification
        classification_row = await conn.fetchrow("""
            SELECT * FROM event_classifications WHERE event_id = $1
        """, event.event_id)
        
        if classification_row:
            from ..models import ClassificationResult, ClassificationConfidence
            event.classification = ClassificationResult(
                event_type=EventType(classification_row['event_type']),
                confidence=classification_row['confidence'],
                confidence_level=ClassificationConfidence(classification_row['confidence_level']),
                primary_indicators=json.loads(classification_row['primary_indicators'] or '[]'),
                secondary_indicators=json.loads(classification_row['secondary_indicators'] or '[]'),
                alternative_types=json.loads(classification_row['alternative_types'] or '[]'),
                reasoning=classification_row['reasoning'],
                model_used=classification_row['model_used']
            )
        
        # Load entities
        entity_rows = await conn.fetch("""
            SELECT * FROM event_entities WHERE event_id = $1
        """, event.event_id)
        
        if entity_rows:
            from ..models import Entity
            event.entities = []
            for row in entity_rows:
                entity = Entity(
                    entity_id=row['entity_id'],
                    entity_type=row['entity_type'],
                    entity_value=row['entity_value'],
                    confidence=row['confidence'],
                    start_pos=row['start_pos'],
                    end_pos=row['end_pos'],
                    context=row['context'],
                    ticker_symbol=row['ticker_symbol'],
                    exchange=row['exchange'],
                    sector=row['sector'],
                    market_cap=row['market_cap']
                )
                event.entities.append(entity)
        
        # Load other relations (severity, enrichment, routing, metrics) as needed...
    
    async def cleanup_old_events(self, days_to_keep: int = 30):
        """Clean up old processed events"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            async with self.get_connection() as conn:
                # Delete in order to maintain referential integrity
                deleted_count = await conn.fetchval("""
                    WITH deleted_events AS (
                        DELETE FROM processed_events 
                        WHERE created_at < $1 
                        RETURNING event_id
                    )
                    SELECT COUNT(*) FROM deleted_events
                """, cutoff_date)
                
                logger.info("Cleaned up old events", 
                           deleted_count=deleted_count, 
                           cutoff_date=cutoff_date)
                
                return deleted_count
                
        except Exception as e:
            logger.error("Failed to cleanup old events", error=str(e))
            return 0
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed") 