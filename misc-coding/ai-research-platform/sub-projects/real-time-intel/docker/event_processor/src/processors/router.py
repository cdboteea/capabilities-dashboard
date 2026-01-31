"""
Event Routing Engine - Intelligent routing decisions for processed events
"""

import asyncio
import httpx
import json
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..models import (
    RoutingDecision, EventSeverity, EventUrgency, EventType,
    NewsEvent, Entity, SeverityAssessment
)

logger = structlog.get_logger(__name__)

class EventRouter:
    """Intelligent event routing and delivery decisions"""
    
    def __init__(self, mac_studio_endpoint: str = "http://10.0.0.100:8000"):
        self.mac_studio_endpoint = mac_studio_endpoint
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Routing configuration
        self.routing_rules = self._load_routing_rules()
        self.delivery_channels = self._load_delivery_channels()
        self.portfolio_holdings = {}  # This would be loaded from holdings service
        
    async def initialize(self):
        """Initialize event router"""
        logger.info("Initializing Event Router")
        # Load portfolio holdings (would be from external service)
        await self._load_portfolio_holdings()
        
    async def route_event(
        self, 
        event: NewsEvent, 
        entities: List[Entity],
        severity_assessment: SeverityAssessment
    ) -> RoutingDecision:
        """Determine routing for processed event"""
        logger.info("Routing event", event_id=event.event_id)
        
        try:
            # Multiple routing factors
            routing_tasks = [
                self._assess_portfolio_relevance(event, entities),
                self._determine_delivery_channels(severity_assessment, event),
                self._calculate_routing_priority(severity_assessment, event),
                self._assess_audience_targeting(event, entities, severity_assessment)
            ]
            
            # Execute routing analysis
            results = await asyncio.gather(*routing_tasks, return_exceptions=True)
            
            # Process results
            portfolio_relevance = 0.0
            affected_holdings = []
            delivery_channels = ["standard"]
            priority_level = 1
            audience_targets = []
            routing_criteria = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Routing task {i} failed", error=str(result))
                    continue
                
                if i == 0:  # Portfolio relevance
                    portfolio_relevance = result.get('relevance_score', 0.0)
                    affected_holdings = result.get('affected_holdings', [])
                    routing_criteria.extend(result.get('criteria', []))
                elif i == 1:  # Delivery channels
                    delivery_channels = result.get('channels', ["standard"])
                    routing_criteria.extend(result.get('criteria', []))
                elif i == 2:  # Priority
                    priority_level = result.get('priority', 1)
                    routing_criteria.extend(result.get('criteria', []))
                elif i == 3:  # Audience targeting
                    audience_targets = result.get('targets', [])
                    routing_criteria.extend(result.get('criteria', []))
            
            # Determine primary and secondary destinations
            primary_destination, secondary_destinations = self._determine_destinations(
                severity_assessment, portfolio_relevance, audience_targets, delivery_channels
            )
            
            # Calculate routing confidence
            routing_score = self._calculate_routing_confidence(
                portfolio_relevance, severity_assessment, len(entities)
            )
            
            # Determine delivery method and timing
            delivery_method = self._determine_delivery_method(severity_assessment)
            delivery_delay = self._calculate_delivery_delay(severity_assessment)
            expiry_time = self._calculate_expiry_time(event, severity_assessment)
            
            routing_decision = RoutingDecision(
                primary_destination=primary_destination,
                secondary_destinations=secondary_destinations,
                routing_score=routing_score,
                routing_criteria=routing_criteria[:10],  # Limit criteria
                portfolio_relevance=portfolio_relevance,
                affected_holdings=affected_holdings,
                delivery_method=delivery_method,
                priority_level=priority_level,
                delivery_delay=delivery_delay,
                expiry_time=expiry_time
            )
            
            logger.info("Event routing completed", 
                       event_id=event.event_id,
                       primary_destination=primary_destination,
                       portfolio_relevance=portfolio_relevance,
                       priority=priority_level)
            
            return routing_decision
            
        except Exception as e:
            logger.error("Event routing failed", 
                        error=str(e), 
                        event_id=event.event_id)
            
            # Return default routing
            return RoutingDecision(
                primary_destination="general_feed",
                secondary_destinations=[],
                routing_score=0.5,
                routing_criteria=["default_routing"],
                delivery_method="standard",
                priority_level=1
            )
    
    async def _assess_portfolio_relevance(self, event: NewsEvent, entities: List[Entity]) -> Dict[str, Any]:
        """Assess relevance to portfolio holdings"""
        relevance_score = 0.0
        affected_holdings = []
        criteria = []
        
        try:
            # Check for ticker matches
            ticker_entities = [e for e in entities if e.entity_type == "TICKER" and e.ticker_symbol]
            
            for entity in ticker_entities:
                ticker = entity.ticker_symbol
                
                if ticker in self.portfolio_holdings:
                    holding = self.portfolio_holdings[ticker]
                    
                    # Calculate relevance based on holding size and entity confidence
                    position_weight = holding.get('weight', 0.0)  # Portfolio weight
                    entity_confidence = entity.confidence
                    
                    # Higher relevance for larger positions and high-confidence entities
                    ticker_relevance = (position_weight * 0.7) + (entity_confidence * 0.3)
                    relevance_score = max(relevance_score, ticker_relevance)
                    
                    affected_holdings.append({
                        'ticker': ticker,
                        'company': entity.entity_value,
                        'position_weight': position_weight,
                        'relevance': ticker_relevance
                    })
                    
                    criteria.append(f"Portfolio holding: {ticker} ({position_weight:.1%})")
            
            # Check for company name matches
            company_entities = [e for e in entities if e.entity_type in ["COMPANY", "ORG"]]
            
            for entity in company_entities:
                # Try to map company name to ticker
                ticker = self._map_company_to_ticker(entity.entity_value)
                
                if ticker and ticker in self.portfolio_holdings:
                    holding = self.portfolio_holdings[ticker]
                    position_weight = holding.get('weight', 0.0)
                    
                    # Lower confidence for company name matches
                    company_relevance = position_weight * 0.5 * entity.confidence
                    relevance_score = max(relevance_score, company_relevance)
                    
                    if not any(h['ticker'] == ticker for h in affected_holdings):
                        affected_holdings.append({
                            'ticker': ticker,
                            'company': entity.entity_value,
                            'position_weight': position_weight,
                            'relevance': company_relevance
                        })
                        
                        criteria.append(f"Company match: {entity.entity_value} -> {ticker}")
            
            # Sector/industry relevance
            sector_relevance = self._assess_sector_relevance(entities)
            if sector_relevance > 0.1:
                relevance_score = max(relevance_score, sector_relevance)
                criteria.append(f"Sector relevance: {sector_relevance:.2f}")
            
        except Exception as e:
            logger.error("Portfolio relevance assessment failed", error=str(e))
        
        return {
            'relevance_score': relevance_score,
            'affected_holdings': affected_holdings,
            'criteria': criteria
        }
    
    async def _determine_delivery_channels(
        self, 
        severity_assessment: SeverityAssessment, 
        event: NewsEvent
    ) -> Dict[str, Any]:
        """Determine appropriate delivery channels"""
        channels = ["standard"]
        criteria = []
        
        try:
            severity = severity_assessment.severity
            urgency = severity_assessment.urgency
            
            # Channel selection based on severity and urgency
            if severity == EventSeverity.CRITICAL:
                channels = ["immediate_alert", "email", "dashboard", "api"]
                criteria.append("Critical severity - all channels")
            elif severity == EventSeverity.HIGH:
                if urgency in [EventUrgency.IMMEDIATE, EventUrgency.HIGH]:
                    channels = ["priority_alert", "email", "dashboard"]
                    criteria.append("High severity + urgent - priority channels")
                else:
                    channels = ["email", "dashboard", "api"]
                    criteria.append("High severity - standard channels")
            elif severity == EventSeverity.MEDIUM:
                if urgency == EventUrgency.IMMEDIATE:
                    channels = ["priority_alert", "dashboard"]
                    criteria.append("Medium severity + immediate - priority alert")
                else:
                    channels = ["dashboard", "api"]
                    criteria.append("Medium severity - dashboard and API")
            else:
                channels = ["api", "batch_feed"]
                criteria.append("Low severity - background channels")
            
            # Event type specific channels
            if event.classification:
                event_type = event.classification.event_type
                
                if event_type == EventType.EARNINGS_ANNOUNCEMENT:
                    if "earnings_feed" not in channels:
                        channels.append("earnings_feed")
                    criteria.append("Earnings event - earnings feed")
                elif event_type == EventType.BREAKING_NEWS:
                    if "breaking_news" not in channels:
                        channels.append("breaking_news")
                    criteria.append("Breaking news - breaking news feed")
                elif event_type in [EventType.REGULATORY_UPDATE, EventType.LITIGATION]:
                    if "regulatory_feed" not in channels:
                        channels.append("regulatory_feed")
                    criteria.append("Regulatory event - regulatory feed")
        
        except Exception as e:
            logger.error("Delivery channel determination failed", error=str(e))
        
        return {'channels': channels, 'criteria': criteria}
    
    async def _calculate_routing_priority(
        self, 
        severity_assessment: SeverityAssessment, 
        event: NewsEvent
    ) -> Dict[str, Any]:
        """Calculate routing priority level"""
        priority = 1
        criteria = []
        
        try:
            severity = severity_assessment.severity
            urgency = severity_assessment.urgency
            
            # Base priority from severity
            severity_priority = {
                EventSeverity.CRITICAL: 5,
                EventSeverity.HIGH: 4,
                EventSeverity.MEDIUM: 3,
                EventSeverity.LOW: 2,
                EventSeverity.INFO: 1
            }
            
            # Base priority from urgency
            urgency_priority = {
                EventUrgency.IMMEDIATE: 5,
                EventUrgency.HIGH: 4,
                EventUrgency.NORMAL: 3,
                EventUrgency.LOW: 2,
                EventUrgency.BATCH: 1
            }
            
            # Take the maximum of severity and urgency priority
            priority = max(
                severity_priority.get(severity, 1),
                urgency_priority.get(urgency, 1)
            )
            
            criteria.append(f"Severity: {severity.value} -> {severity_priority.get(severity, 1)}")
            criteria.append(f"Urgency: {urgency.value} -> {urgency_priority.get(urgency, 1)}")
            
            # Market hours boost
            if event.published_at:
                market_hours_factor = self._is_market_hours(event.published_at)
                if market_hours_factor and priority < 5:
                    priority = min(5, priority + 1)
                    criteria.append("Market hours priority boost")
        
        except Exception as e:
            logger.error("Priority calculation failed", error=str(e))
        
        return {'priority': priority, 'criteria': criteria}
    
    async def _assess_audience_targeting(
        self,
        event: NewsEvent,
        entities: List[Entity],
        severity_assessment: SeverityAssessment
    ) -> Dict[str, Any]:
        """Determine target audiences for the event"""
        targets = []
        criteria = []
        
        try:
            # Investor targeting
            if severity_assessment.market_impact_score > 0.6:
                targets.append("investors")
                criteria.append("High market impact - investor targeting")
            
            # Analyst targeting
            if event.classification and event.classification.event_type in [
                EventType.EARNINGS_ANNOUNCEMENT, 
                EventType.ANALYST_UPGRADE, 
                EventType.ANALYST_DOWNGRADE
            ]:
                targets.append("analysts")
                criteria.append("Analyst-relevant event type")
            
            # Trader targeting
            if severity_assessment.urgency in [EventUrgency.IMMEDIATE, EventUrgency.HIGH]:
                targets.append("traders")
                criteria.append("High urgency - trader targeting")
            
            # Risk manager targeting
            if severity_assessment.severity in [EventSeverity.CRITICAL, EventSeverity.HIGH]:
                targets.append("risk_managers")
                criteria.append("High severity - risk manager targeting")
            
            # Portfolio manager targeting
            portfolio_entities = [e for e in entities if e.entity_type in ["TICKER", "COMPANY"]]
            if portfolio_entities:
                targets.append("portfolio_managers")
                criteria.append("Portfolio-relevant entities")
            
            # Compliance targeting
            if event.classification and event.classification.event_type in [
                EventType.REGULATORY_UPDATE, 
                EventType.LITIGATION,
                EventType.INVESTIGATION
            ]:
                targets.append("compliance")
                criteria.append("Regulatory/compliance event")
            
        except Exception as e:
            logger.error("Audience targeting failed", error=str(e))
        
        return {'targets': targets, 'criteria': criteria}
    
    def _determine_destinations(
        self,
        severity_assessment: SeverityAssessment,
        portfolio_relevance: float,
        audience_targets: List[str],
        delivery_channels: List[str]
    ) -> tuple[str, List[str]]:
        """Determine primary and secondary routing destinations"""
        
        # Primary destination logic
        if portfolio_relevance > 0.7:
            primary = "portfolio_alerts"
        elif severity_assessment.severity == EventSeverity.CRITICAL:
            primary = "critical_alerts"
        elif severity_assessment.urgency == EventUrgency.IMMEDIATE:
            primary = "immediate_feed"
        elif "investors" in audience_targets:
            primary = "investor_feed"
        elif severity_assessment.severity == EventSeverity.HIGH:
            primary = "priority_feed"
        else:
            primary = "general_feed"
        
        # Secondary destinations
        secondary = []
        
        if "email" in delivery_channels:
            secondary.append("email_queue")
        
        if "api" in delivery_channels:
            secondary.append("api_feed")
        
        if "dashboard" in delivery_channels:
            secondary.append("dashboard_feed")
        
        # Audience-specific feeds
        for target in audience_targets:
            if target not in primary:
                secondary.append(f"{target}_feed")
        
        # Remove duplicates and primary from secondary
        secondary = list(set(secondary))
        if primary in secondary:
            secondary.remove(primary)
        
        return primary, secondary
    
    def _calculate_routing_confidence(
        self,
        portfolio_relevance: float,
        severity_assessment: SeverityAssessment,
        entity_count: int
    ) -> float:
        """Calculate confidence in routing decision"""
        
        confidence_factors = []
        
        # Portfolio relevance increases confidence
        confidence_factors.append(portfolio_relevance * 0.3)
        
        # Assessment confidence
        confidence_factors.append(severity_assessment.confidence * 0.3)
        
        # Entity identification confidence
        if entity_count > 0:
            entity_factor = min(1.0, entity_count / 5.0) * 0.2
            confidence_factors.append(entity_factor)
        
        # Base confidence
        confidence_factors.append(0.2)
        
        return min(1.0, sum(confidence_factors))
    
    def _determine_delivery_method(self, severity_assessment: SeverityAssessment) -> str:
        """Determine delivery method based on severity"""
        
        if severity_assessment.severity == EventSeverity.CRITICAL:
            return "push_notification"
        elif severity_assessment.urgency == EventUrgency.IMMEDIATE:
            return "priority_delivery"
        elif severity_assessment.severity == EventSeverity.HIGH:
            return "priority_delivery"
        else:
            return "standard"
    
    def _calculate_delivery_delay(self, severity_assessment: SeverityAssessment) -> Optional[int]:
        """Calculate delivery delay in minutes"""
        
        if severity_assessment.urgency == EventUrgency.IMMEDIATE:
            return 0  # No delay
        elif severity_assessment.urgency == EventUrgency.HIGH:
            return 5  # 5 minute delay
        elif severity_assessment.urgency == EventUrgency.NORMAL:
            return 15  # 15 minute delay
        elif severity_assessment.urgency == EventUrgency.LOW:
            return 60  # 1 hour delay
        else:  # BATCH
            return 240  # 4 hour delay
    
    def _calculate_expiry_time(
        self, 
        event: NewsEvent, 
        severity_assessment: SeverityAssessment
    ) -> Optional[datetime]:
        """Calculate when event becomes stale"""
        
        if not event.published_at:
            return None
        
        # Expiry based on event type and severity
        if severity_assessment.severity == EventSeverity.CRITICAL:
            expiry_hours = 4  # Critical events expire quickly
        elif severity_assessment.urgency == EventUrgency.IMMEDIATE:
            expiry_hours = 8
        elif event.classification and event.classification.event_type == EventType.BREAKING_NEWS:
            expiry_hours = 12
        else:
            expiry_hours = 24  # Standard expiry
        
        return event.published_at + timedelta(hours=expiry_hours)
    
    def _assess_sector_relevance(self, entities: List[Entity]) -> float:
        """Assess relevance to portfolio sectors"""
        # Simplified sector relevance calculation
        # In practice, this would analyze portfolio sector allocation
        
        sector_entities = [e for e in entities if e.sector]
        if not sector_entities:
            return 0.0
        
        # Mock sector weights (would come from portfolio analysis)
        portfolio_sectors = {
            'Technology': 0.3,
            'Healthcare': 0.2,
            'Financial Services': 0.15,
            'Consumer Cyclical': 0.1
        }
        
        max_relevance = 0.0
        for entity in sector_entities:
            sector_weight = portfolio_sectors.get(entity.sector, 0.0)
            entity_relevance = sector_weight * entity.confidence * 0.5  # Sector relevance is lower than direct holdings
            max_relevance = max(max_relevance, entity_relevance)
        
        return max_relevance
    
    def _map_company_to_ticker(self, company_name: str) -> Optional[str]:
        """Map company name to ticker symbol"""
        # Simplified mapping - would use comprehensive database
        company_mappings = {
            'apple': 'AAPL',
            'microsoft': 'MSFT',
            'google': 'GOOGL',
            'alphabet': 'GOOGL',
            'amazon': 'AMZN',
            'tesla': 'TSLA',
            'meta': 'META',
            'facebook': 'META',
            'nvidia': 'NVDA',
            'netflix': 'NFLX'
        }
        
        normalized_name = company_name.lower()
        for key, ticker in company_mappings.items():
            if key in normalized_name:
                return ticker
        
        return None
    
    def _is_market_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is during market hours"""
        # Simplified market hours check (9:30 AM - 4:00 PM EST)
        hour = timestamp.hour
        weekday = timestamp.weekday()
        
        # Monday = 0, Sunday = 6
        if weekday >= 5:  # Weekend
            return False
        
        # Market hours in UTC (assuming timestamp is UTC)
        # 9:30 AM EST = 14:30 UTC, 4:00 PM EST = 21:00 UTC
        return 14 <= hour <= 21
    
    async def _load_portfolio_holdings(self):
        """Load portfolio holdings (mock implementation)"""
        # In practice, this would call the Holdings Router service
        self.portfolio_holdings = {
            'AAPL': {'weight': 0.08, 'shares': 1000, 'sector': 'Technology'},
            'MSFT': {'weight': 0.07, 'shares': 800, 'sector': 'Technology'},
            'GOOGL': {'weight': 0.06, 'shares': 500, 'sector': 'Technology'},
            'AMZN': {'weight': 0.05, 'shares': 300, 'sector': 'Consumer Cyclical'},
            'TSLA': {'weight': 0.04, 'shares': 200, 'sector': 'Consumer Cyclical'},
            'META': {'weight': 0.03, 'shares': 400, 'sector': 'Communication Services'},
            'NVDA': {'weight': 0.05, 'shares': 600, 'sector': 'Technology'},
            'JNJ': {'weight': 0.03, 'shares': 700, 'sector': 'Healthcare'},
            'V': {'weight': 0.02, 'shares': 300, 'sector': 'Financial Services'},
            'WMT': {'weight': 0.02, 'shares': 400, 'sector': 'Consumer Defensive'}
        }
    
    def _load_routing_rules(self) -> Dict[str, Any]:
        """Load routing rules configuration"""
        return {
            'critical_threshold': 0.9,
            'high_priority_threshold': 0.7,
            'portfolio_relevance_threshold': 0.5,
            'immediate_routing_types': [
                EventType.BREAKING_NEWS,
                EventType.EARNINGS_ANNOUNCEMENT,
                EventType.MERGER_ACQUISITION
            ]
        }
    
    def _load_delivery_channels(self) -> Dict[str, Any]:
        """Load delivery channel configuration"""
        return {
            'immediate_alert': {'latency': 0, 'reliability': 0.99},
            'priority_alert': {'latency': 30, 'reliability': 0.98},
            'email': {'latency': 300, 'reliability': 0.95},
            'dashboard': {'latency': 60, 'reliability': 0.99},
            'api': {'latency': 10, 'reliability': 0.99},
            'batch_feed': {'latency': 3600, 'reliability': 0.99}
        }
    
    async def close(self):
        """Close HTTP client and cleanup resources"""
        await self.http_client.aclose() 