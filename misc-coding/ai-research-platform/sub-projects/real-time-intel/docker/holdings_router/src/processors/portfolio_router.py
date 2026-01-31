"""
Portfolio Event Router

Routes incoming events to users based on portfolio relevance.
This is the main orchestration service that uses the RelevanceEngine.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta

from .relevance_engine import relevance_engine, RelevanceLevel, RelevanceScore

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Result of routing an event to users."""
    event_id: str
    total_users_matched: int
    users_by_level: Dict[str, List[str]]  # level -> user_ids
    processing_time_ms: float
    timestamp: datetime


@dataclass
class UserPortfolioCache:
    """Cached user portfolio data."""
    user_id: str
    portfolio: Dict
    last_updated: datetime
    cache_ttl_minutes: int = 30


class PortfolioRouter:
    """
    Main routing service that determines which users should receive which events.
    
    Workflow:
    1. Receive event from Event Processor
    2. Load all active user portfolios
    3. Calculate relevance scores for each user
    4. Route to users based on relevance thresholds
    5. Send to Alert Engine for delivery
    """
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.portfolio_cache: Dict[str, UserPortfolioCache] = {}
        self.routing_thresholds = {
            RelevanceLevel.CRITICAL: 0.8,
            RelevanceLevel.HIGH: 0.6,
            RelevanceLevel.MEDIUM: 0.4,
            RelevanceLevel.LOW: 0.2
        }
        
        # Performance tracking
        self.routing_stats = {
            'total_events_processed': 0,
            'total_users_notified': 0,
            'avg_processing_time_ms': 0.0,
            'cache_hit_rate': 0.0
        }
    
    async def route_event(
        self,
        event_id: str,
        event_text: str,
        event_entities: List[str],
        event_sentiment: Optional[Dict],
        event_metadata: Optional[Dict] = None,
        min_relevance_level: RelevanceLevel = RelevanceLevel.LOW
    ) -> RoutingDecision:
        """
        Route an event to relevant users based on portfolio analysis.
        
        Args:
            event_id: Unique event identifier
            event_text: Event content text
            event_entities: Extracted entities (tickers, companies)
            event_sentiment: Sentiment analysis results
            event_metadata: Additional event metadata
            min_relevance_level: Minimum relevance level to route
            
        Returns:
            RoutingDecision with routing results
        """
        start_time = datetime.now()
        
        logger.info(f"Routing event {event_id} to users")
        
        try:
            # Get all active user portfolios
            user_portfolios = await self._get_active_user_portfolios()
            
            if not user_portfolios:
                logger.warning("No active user portfolios found")
                return RoutingDecision(
                    event_id=event_id,
                    total_users_matched=0,
                    users_by_level={},
                    processing_time_ms=0.0,
                    timestamp=start_time
                )
            
            # Calculate relevance for each user
            routing_results = {}
            users_by_level = {level.value: [] for level in RelevanceLevel}
            
            for user_id, portfolio in user_portfolios.items():
                try:
                    relevance_score = relevance_engine.calculate_relevance(
                        event_text=event_text,
                        event_entities=event_entities,
                        event_sentiment=event_sentiment,
                        user_portfolio=portfolio,
                        event_metadata=event_metadata
                    )
                    
                    # Check if meets minimum threshold
                    if self._meets_threshold(relevance_score.level, min_relevance_level):
                        routing_results[user_id] = relevance_score
                        users_by_level[relevance_score.level.value].append(user_id)
                        
                        # Store routing decision in database
                        await self._store_routing_decision(
                            event_id, user_id, relevance_score
                        )
                    
                except Exception as e:
                    logger.error(f"Error calculating relevance for user {user_id}: {e}")
                    continue
            
            # Send to Alert Engine for delivery
            if routing_results:
                await self._send_to_alert_engine(event_id, routing_results)
            
            # Calculate metrics
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            total_matched = sum(len(users) for users in users_by_level.values())
            
            # Update stats
            self._update_routing_stats(processing_time, total_matched)
            
            logger.info(
                f"Event {event_id} routed to {total_matched} users in {processing_time:.1f}ms"
            )
            
            return RoutingDecision(
                event_id=event_id,
                total_users_matched=total_matched,
                users_by_level=users_by_level,
                processing_time_ms=processing_time,
                timestamp=start_time
            )
            
        except Exception as e:
            logger.error(f"Error routing event {event_id}: {e}")
            raise
    
    async def route_batch_events(
        self,
        events: List[Dict],
        min_relevance_level: RelevanceLevel = RelevanceLevel.LOW
    ) -> List[RoutingDecision]:
        """Route multiple events in batch for efficiency."""
        
        logger.info(f"Batch routing {len(events)} events")
        
        # Pre-load all user portfolios once
        user_portfolios = await self._get_active_user_portfolios()
        
        routing_tasks = []
        for event in events:
            task = self.route_event(
                event_id=event['event_id'],
                event_text=event['text'],
                event_entities=event.get('entities', []),
                event_sentiment=event.get('sentiment'),
                event_metadata=event.get('metadata'),
                min_relevance_level=min_relevance_level
            )
            routing_tasks.append(task)
        
        # Process all events concurrently
        results = await asyncio.gather(*routing_tasks, return_exceptions=True)
        
        # Filter out exceptions
        successful_results = [r for r in results if isinstance(r, RoutingDecision)]
        
        logger.info(f"Batch routing completed: {len(successful_results)}/{len(events)} successful")
        
        return successful_results
    
    async def get_user_relevant_events(
        self,
        user_id: str,
        hours_back: int = 24,
        min_relevance_level: RelevanceLevel = RelevanceLevel.LOW
    ) -> List[Dict]:
        """Get recent events relevant to a specific user's portfolio."""
        
        if not self.db_pool:
            return []
        
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT 
                        er.event_id,
                        er.relevance_score,
                        er.relevance_level,
                        er.matched_entities,
                        er.reasoning,
                        er.created_at,
                        e.title,
                        e.content,
                        e.source_url
                    FROM event_routing er
                    JOIN events e ON er.event_id = e.event_id
                    WHERE er.user_id = $1
                    AND er.created_at >= NOW() - INTERVAL '%s hours'
                    AND er.relevance_level::text = ANY($2)
                    ORDER BY er.relevance_score DESC, er.created_at DESC
                    LIMIT 100
                """ % hours_back
                
                # Get relevance levels that meet threshold
                valid_levels = [level.value for level in RelevanceLevel 
                              if self._meets_threshold(level, min_relevance_level)]
                
                rows = await conn.fetch(query, user_id, valid_levels)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting relevant events for user {user_id}: {e}")
            return []
    
    async def get_routing_analytics(self, hours_back: int = 24) -> Dict:
        """Get routing analytics and performance metrics."""
        
        if not self.db_pool:
            return {}
        
        try:
            async with self.db_pool.acquire() as conn:
                # Event routing stats
                routing_query = """
                    SELECT 
                        relevance_level,
                        COUNT(*) as count,
                        AVG(relevance_score) as avg_score,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT event_id) as unique_events
                    FROM event_routing
                    WHERE created_at >= NOW() - INTERVAL '%s hours'
                    GROUP BY relevance_level
                """ % hours_back
                
                routing_stats = await conn.fetch(routing_query)
                
                # Performance stats
                perf_query = """
                    SELECT 
                        COUNT(*) as total_events,
                        AVG(processing_time_ms) as avg_processing_time,
                        MAX(processing_time_ms) as max_processing_time,
                        MIN(processing_time_ms) as min_processing_time
                    FROM routing_decisions
                    WHERE created_at >= NOW() - INTERVAL '%s hours'
                """ % hours_back
                
                perf_stats = await conn.fetchrow(perf_query)
                
                return {
                    'routing_by_level': [dict(row) for row in routing_stats],
                    'performance': dict(perf_stats) if perf_stats else {},
                    'cache_stats': {
                        'cached_portfolios': len(self.portfolio_cache),
                        'cache_hit_rate': self.routing_stats['cache_hit_rate']
                    },
                    'overall_stats': self.routing_stats
                }
                
        except Exception as e:
            logger.error(f"Error getting routing analytics: {e}")
            return {}
    
    async def _get_active_user_portfolios(self) -> Dict[str, Dict]:
        """Get all active user portfolios with caching."""
        
        if not self.db_pool:
            return {}
        
        portfolios = {}
        cache_hits = 0
        cache_misses = 0
        
        try:
            async with self.db_pool.acquire() as conn:
                # Get list of active users
                users_query = """
                    SELECT user_id, last_portfolio_update
                    FROM users 
                    WHERE is_active = true 
                    AND portfolio_enabled = true
                """
                
                user_rows = await conn.fetch(users_query)
                
                for user_row in user_rows:
                    user_id = user_row['user_id']
                    
                    # Check cache first
                    cached_portfolio = self.portfolio_cache.get(user_id)
                    if (cached_portfolio and 
                        cached_portfolio.last_updated > datetime.now() - timedelta(minutes=cached_portfolio.cache_ttl_minutes)):
                        portfolios[user_id] = cached_portfolio.portfolio
                        cache_hits += 1
                        continue
                    
                    # Load from database
                    portfolio = await self._load_user_portfolio(conn, user_id)
                    if portfolio:
                        portfolios[user_id] = portfolio
                        
                        # Update cache
                        self.portfolio_cache[user_id] = UserPortfolioCache(
                            user_id=user_id,
                            portfolio=portfolio,
                            last_updated=datetime.now()
                        )
                        cache_misses += 1
                
                # Update cache hit rate
                total_requests = cache_hits + cache_misses
                if total_requests > 0:
                    self.routing_stats['cache_hit_rate'] = cache_hits / total_requests
                
                logger.debug(f"Portfolio cache: {cache_hits} hits, {cache_misses} misses")
                
        except Exception as e:
            logger.error(f"Error loading user portfolios: {e}")
        
        return portfolios
    
    async def _load_user_portfolio(self, conn, user_id: str) -> Optional[Dict]:
        """Load a single user's portfolio from database."""
        
        try:
            # Get portfolio summary
            portfolio_query = """
                SELECT 
                    total_value,
                    cash_balance,
                    total_return_pct,
                    risk_level,
                    last_updated
                FROM portfolios 
                WHERE user_id = $1
            """
            
            portfolio_row = await conn.fetchrow(portfolio_query, user_id)
            if not portfolio_row:
                return None
            
            # Get holdings
            holdings_query = """
                SELECT 
                    symbol,
                    name,
                    shares,
                    avg_cost,
                    market_value,
                    sector,
                    position_pct,
                    unrealized_pnl
                FROM holdings 
                WHERE user_id = $1 
                AND shares > 0
                ORDER BY market_value DESC
            """
            
            holdings_rows = await conn.fetch(holdings_query, user_id)
            
            return {
                'user_id': user_id,
                'total_value': float(portfolio_row['total_value']),
                'cash_balance': float(portfolio_row['cash_balance']),
                'total_return_pct': float(portfolio_row['total_return_pct']),
                'risk_level': portfolio_row['risk_level'],
                'last_updated': portfolio_row['last_updated'],
                'holdings': [dict(row) for row in holdings_rows]
            }
            
        except Exception as e:
            logger.error(f"Error loading portfolio for user {user_id}: {e}")
            return None
    
    async def _store_routing_decision(self, event_id: str, user_id: str, relevance_score: RelevanceScore):
        """Store routing decision in database."""
        
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO event_routing (
                        event_id, user_id, relevance_score, relevance_level,
                        entity_match_score, sector_correlation_score,
                        sentiment_impact_score, position_weight_score,
                        matched_entities, affected_positions, reasoning, confidence
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """, 
                    event_id, user_id, relevance_score.overall_score, relevance_score.level.value,
                    relevance_score.entity_match_score, relevance_score.sector_correlation_score,
                    relevance_score.sentiment_impact_score, relevance_score.position_weight_score,
                    relevance_score.matched_entities, relevance_score.affected_positions,
                    relevance_score.reasoning, relevance_score.confidence
                )
                
        except Exception as e:
            logger.error(f"Error storing routing decision: {e}")
    
    async def _send_to_alert_engine(self, event_id: str, routing_results: Dict[str, RelevanceScore]):
        """Send routing results to Alert Engine for delivery."""
        
        # This would integrate with the Alert Engine service
        # For now, just log the routing decisions
        
        logger.info(f"Sending event {event_id} to Alert Engine for {len(routing_results)} users")
        
        for user_id, score in routing_results.items():
            logger.debug(
                f"User {user_id}: {score.level.value} relevance "
                f"(score: {score.overall_score:.3f}, reason: {score.reasoning})"
            )
    
    def _meets_threshold(self, relevance_level: RelevanceLevel, min_level: RelevanceLevel) -> bool:
        """Check if relevance level meets minimum threshold."""
        
        level_order = [
            RelevanceLevel.IRRELEVANT,
            RelevanceLevel.LOW,
            RelevanceLevel.MEDIUM,
            RelevanceLevel.HIGH,
            RelevanceLevel.CRITICAL
        ]
        
        return level_order.index(relevance_level) >= level_order.index(min_level)
    
    def _update_routing_stats(self, processing_time_ms: float, users_notified: int):
        """Update internal routing statistics."""
        
        self.routing_stats['total_events_processed'] += 1
        self.routing_stats['total_users_notified'] += users_notified
        
        # Update rolling average processing time
        current_avg = self.routing_stats['avg_processing_time_ms']
        total_events = self.routing_stats['total_events_processed']
        
        self.routing_stats['avg_processing_time_ms'] = (
            (current_avg * (total_events - 1) + processing_time_ms) / total_events
        )


# Global router instance
portfolio_router = PortfolioRouter()
