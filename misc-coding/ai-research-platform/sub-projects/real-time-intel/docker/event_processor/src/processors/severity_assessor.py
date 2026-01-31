"""
Severity Assessment Processor - Event impact and urgency evaluation
"""

import asyncio
import httpx
import json
import re
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np

from ..models import (
    EventSeverity, EventUrgency, SeverityAssessment, 
    EventType, NewsEvent, Entity
)

logger = structlog.get_logger(__name__)

class SeverityAssessor:
    """Advanced event severity and urgency assessment"""
    
    def __init__(self, mac_studio_endpoint: str = "http://10.0.0.100:8000"):
        self.mac_studio_endpoint = mac_studio_endpoint
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Assessment criteria and weights
        self.severity_weights = self._load_severity_weights()
        self.urgency_factors = self._load_urgency_factors()
        self.market_impact_keywords = self._load_market_impact_keywords()
        
    async def initialize(self):
        """Initialize severity assessor"""
        logger.info("Initializing Severity Assessor")
        
    async def assess_severity(self, event: NewsEvent, entities: List[Entity]) -> SeverityAssessment:
        """Assess event severity and urgency"""
        logger.info("Assessing event severity", event_id=event.event_id)
        
        try:
            # Multiple assessment approaches
            assessment_tasks = [
                self._assess_market_impact(event, entities),
                self._assess_company_impact(event, entities),
                self._assess_time_sensitivity(event),
                self._assess_stakeholder_impact(event, entities)
            ]
            
            # Execute all assessment tasks
            results = await asyncio.gather(*assessment_tasks, return_exceptions=True)
            
            # Process results
            market_impact = 0.5
            company_impact = 0.5
            time_sensitivity = 0.5
            stakeholder_impact = 0.5
            
            assessment_factors = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Assessment task {i} failed", error=str(result))
                    continue
                
                if i == 0:  # Market impact
                    market_impact = result.get('score', 0.5)
                    assessment_factors.extend(result.get('factors', []))
                elif i == 1:  # Company impact
                    company_impact = result.get('score', 0.5)
                    assessment_factors.extend(result.get('factors', []))
                elif i == 2:  # Time sensitivity
                    time_sensitivity = result.get('score', 0.5)
                    assessment_factors.extend(result.get('factors', []))
                elif i == 3:  # Stakeholder impact
                    stakeholder_impact = result.get('score', 0.5)
                    assessment_factors.extend(result.get('factors', []))
            
            # Calculate overall severity score
            overall_severity = self._calculate_overall_severity(
                market_impact, company_impact, time_sensitivity, stakeholder_impact, event
            )
            
            # Determine severity and urgency levels
            severity_level = self._determine_severity_level(overall_severity)
            urgency_level = self._determine_urgency_level(time_sensitivity, overall_severity, event)
            
            # Calculate confidence based on assessment quality
            confidence = self._calculate_assessment_confidence(
                market_impact, company_impact, time_sensitivity, stakeholder_impact, entities
            )
            
            # Generate reasoning
            reasoning = await self._generate_reasoning(
                event, market_impact, company_impact, time_sensitivity, stakeholder_impact
            )
            
            assessment = SeverityAssessment(
                severity=severity_level,
                urgency=urgency_level,
                market_impact_score=market_impact,
                company_impact_score=company_impact,
                time_sensitivity_score=time_sensitivity,
                stakeholder_impact_score=stakeholder_impact,
                overall_severity_score=overall_severity,
                confidence=confidence,
                assessment_factors=assessment_factors[:10],  # Limit factors
                reasoning=reasoning
            )
            
            logger.info("Severity assessment completed", 
                       event_id=event.event_id,
                       severity=severity_level.value,
                       urgency=urgency_level.value,
                       overall_score=overall_severity)
            
            return assessment
            
        except Exception as e:
            logger.error("Severity assessment failed", 
                        error=str(e), 
                        event_id=event.event_id)
            
            # Return default assessment
            return SeverityAssessment(
                severity=EventSeverity.MEDIUM,
                urgency=EventUrgency.NORMAL,
                market_impact_score=0.5,
                company_impact_score=0.5,
                time_sensitivity_score=0.5,
                stakeholder_impact_score=0.5,
                overall_severity_score=0.5,
                confidence=0.5,
                assessment_factors=["default_assessment"],
                reasoning="Assessment failed, using default severity"
            )
    
    async def _assess_market_impact(self, event: NewsEvent, entities: List[Entity]) -> Dict[str, Any]:
        """Assess potential market impact"""
        score = 0.5
        factors = []
        
        try:
            text = f"{event.title} {event.content}".lower()
            
            # Check for high-impact keywords
            high_impact_keywords = self.market_impact_keywords.get('high', [])
            medium_impact_keywords = self.market_impact_keywords.get('medium', [])
            
            high_matches = sum(1 for keyword in high_impact_keywords if keyword in text)
            medium_matches = sum(1 for keyword in medium_impact_keywords if keyword in text)
            
            # Base score from keywords
            keyword_score = min(1.0, (high_matches * 0.3 + medium_matches * 0.15))
            
            # Event type factor
            event_type_score = self._get_event_type_market_impact(event.classification.event_type if event.classification else None)
            
            # Entity-based impact (tickers, large companies)
            entity_score = self._assess_entity_market_impact(entities)
            
            # Financial metrics factor
            financial_score = self._assess_financial_metrics_impact(text)
            
            # Combine scores
            scores = [keyword_score, event_type_score, entity_score, financial_score]
            weights = [0.3, 0.3, 0.25, 0.15]
            
            score = sum(s * w for s, w in zip(scores, weights))
            
            # Add assessment factors
            if high_matches > 0:
                factors.append(f"High-impact keywords: {high_matches}")
            if event_type_score > 0.7:
                factors.append("High-impact event type")
            if entity_score > 0.7:
                factors.append("Major market entities involved")
            if financial_score > 0.7:
                factors.append("Significant financial metrics")
            
        except Exception as e:
            logger.error("Market impact assessment failed", error=str(e))
        
        return {'score': score, 'factors': factors}
    
    async def _assess_company_impact(self, event: NewsEvent, entities: List[Entity]) -> Dict[str, Any]:
        """Assess company-specific impact"""
        score = 0.5
        factors = []
        
        try:
            text = f"{event.title} {event.content}".lower()
            
            # Check for company-specific impact indicators
            company_indicators = [
                ('earnings', 0.8), ('revenue', 0.7), ('profit', 0.7), ('loss', 0.7),
                ('guidance', 0.6), ('outlook', 0.5), ('restructuring', 0.8),
                ('layoffs', 0.7), ('expansion', 0.6), ('acquisition', 0.8),
                ('merger', 0.8), ('partnership', 0.5), ('ipo', 0.9),
                ('bankruptcy', 1.0), ('lawsuit', 0.6), ('investigation', 0.7)
            ]
            
            max_impact = 0.0
            for indicator, impact in company_indicators:
                if indicator in text:
                    max_impact = max(max_impact, impact)
                    factors.append(f"Company indicator: {indicator}")
            
            # Entity-based company impact
            company_entities = [e for e in entities if e.entity_type in ['COMPANY', 'ORG', 'TICKER']]
            
            if company_entities:
                # More entities = potentially broader impact
                entity_factor = min(1.0, len(company_entities) / 5.0)
                
                # Check for major companies (by market cap if available)
                major_company_factor = 0.0
                for entity in company_entities:
                    if entity.market_cap and 'B' in entity.market_cap:  # Billion+ market cap
                        major_company_factor = 0.8
                        factors.append(f"Major company: {entity.entity_value}")
                    elif entity.ticker_symbol in ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']:
                        major_company_factor = 0.9
                        factors.append(f"Mega-cap company: {entity.entity_value}")
                
                entity_score = (entity_factor + major_company_factor) / 2
            else:
                entity_score = 0.3  # Low impact if no clear company entities
            
            # Combine scores
            score = max(max_impact, entity_score)
            
        except Exception as e:
            logger.error("Company impact assessment failed", error=str(e))
        
        return {'score': score, 'factors': factors}
    
    async def _assess_time_sensitivity(self, event: NewsEvent) -> Dict[str, Any]:
        """Assess time sensitivity and urgency"""
        score = 0.5
        factors = []
        
        try:
            text = f"{event.title} {event.content}".lower()
            
            # Time-sensitive keywords
            urgent_keywords = [
                'breaking', 'urgent', 'alert', 'immediate', 'emergency',
                'halt', 'suspend', 'stop', 'pause', 'crisis'
            ]
            
            time_keywords = [
                'today', 'now', 'just', 'moments ago', 'minutes ago',
                'this morning', 'this afternoon', 'developing'
            ]
            
            # Check for urgency indicators
            urgent_matches = sum(1 for keyword in urgent_keywords if keyword in text)
            time_matches = sum(1 for keyword in time_keywords if keyword in text)
            
            keyword_score = min(1.0, urgent_matches * 0.4 + time_matches * 0.2)
            
            # Publication recency
            now = datetime.now()
            if event.published_at:
                time_diff = now - event.published_at
                
                if time_diff <= timedelta(hours=1):
                    recency_score = 1.0
                    factors.append("Published within 1 hour")
                elif time_diff <= timedelta(hours=4):
                    recency_score = 0.8
                    factors.append("Published within 4 hours")
                elif time_diff <= timedelta(hours=24):
                    recency_score = 0.6
                    factors.append("Published within 24 hours")
                else:
                    recency_score = 0.3
            else:
                recency_score = 0.5
            
            # Market hours consideration
            market_hours_score = self._assess_market_hours_impact(event.published_at)
            
            # Combine scores
            score = max(keyword_score, (recency_score + market_hours_score) / 2)
            
            if urgent_matches > 0:
                factors.append(f"Urgent keywords: {urgent_matches}")
            if time_matches > 0:
                factors.append(f"Time-sensitive keywords: {time_matches}")
            
        except Exception as e:
            logger.error("Time sensitivity assessment failed", error=str(e))
        
        return {'score': score, 'factors': factors}
    
    async def _assess_stakeholder_impact(self, event: NewsEvent, entities: List[Entity]) -> Dict[str, Any]:
        """Assess impact on various stakeholders"""
        score = 0.5
        factors = []
        
        try:
            text = f"{event.title} {event.content}".lower()
            
            # Stakeholder groups
            stakeholder_indicators = {
                'investors': ['investor', 'shareholder', 'stock', 'share', 'dividend', 'return'],
                'customers': ['customer', 'consumer', 'user', 'client', 'subscriber'],
                'employees': ['employee', 'worker', 'staff', 'layoff', 'hiring', 'job'],
                'regulators': ['sec', 'fda', 'ftc', 'regulatory', 'compliance', 'investigation'],
                'partners': ['partner', 'supplier', 'vendor', 'alliance', 'collaboration'],
                'competitors': ['competitor', 'rival', 'competition', 'market share']
            }
            
            affected_stakeholders = []
            max_impact = 0.0
            
            for stakeholder, keywords in stakeholder_indicators.items():
                matches = sum(1 for keyword in keywords if keyword in text)
                if matches > 0:
                    affected_stakeholders.append(stakeholder)
                    # Different stakeholder types have different impact weights
                    weight = 0.8 if stakeholder in ['investors', 'regulators'] else 0.6
                    impact = min(1.0, matches * 0.2) * weight
                    max_impact = max(max_impact, impact)
            
            # Broad stakeholder impact increases severity
            if len(affected_stakeholders) > 3:
                score = min(1.0, max_impact + 0.2)
                factors.append(f"Multiple stakeholder groups affected: {len(affected_stakeholders)}")
            else:
                score = max_impact
            
            if affected_stakeholders:
                factors.append(f"Stakeholders: {', '.join(affected_stakeholders)}")
            
        except Exception as e:
            logger.error("Stakeholder impact assessment failed", error=str(e))
        
        return {'score': score, 'factors': factors}
    
    def _calculate_overall_severity(
        self, 
        market_impact: float, 
        company_impact: float, 
        time_sensitivity: float, 
        stakeholder_impact: float,
        event: NewsEvent
    ) -> float:
        """Calculate overall severity score"""
        
        # Base weighted score
        weights = self.severity_weights
        base_score = (
            market_impact * weights['market_impact'] +
            company_impact * weights['company_impact'] +
            time_sensitivity * weights['time_sensitivity'] +
            stakeholder_impact * weights['stakeholder_impact']
        )
        
        # Event type modifier
        if event.classification:
            event_type_modifier = self._get_event_type_severity_modifier(event.classification.event_type)
            base_score *= event_type_modifier
        
        # Ensure score is within bounds
        return max(0.0, min(1.0, base_score))
    
    def _determine_severity_level(self, overall_score: float) -> EventSeverity:
        """Convert numeric score to severity level"""
        if overall_score >= 0.9:
            return EventSeverity.CRITICAL
        elif overall_score >= 0.7:
            return EventSeverity.HIGH
        elif overall_score >= 0.5:
            return EventSeverity.MEDIUM
        elif overall_score >= 0.3:
            return EventSeverity.LOW
        else:
            return EventSeverity.INFO
    
    def _determine_urgency_level(
        self, 
        time_sensitivity: float, 
        overall_severity: float, 
        event: NewsEvent
    ) -> EventUrgency:
        """Determine urgency level based on time sensitivity and severity"""
        
        # High severity events are generally more urgent
        urgency_score = (time_sensitivity * 0.7) + (overall_severity * 0.3)
        
        # Market hours consideration
        if event.published_at:
            market_hours_factor = self._assess_market_hours_impact(event.published_at)
            urgency_score *= (0.8 + market_hours_factor * 0.2)
        
        if urgency_score >= 0.9:
            return EventUrgency.IMMEDIATE
        elif urgency_score >= 0.7:
            return EventUrgency.HIGH
        elif urgency_score >= 0.4:
            return EventUrgency.NORMAL
        elif urgency_score >= 0.2:
            return EventUrgency.LOW
        else:
            return EventUrgency.BATCH
    
    def _calculate_assessment_confidence(
        self,
        market_impact: float,
        company_impact: float, 
        time_sensitivity: float,
        stakeholder_impact: float,
        entities: List[Entity]
    ) -> float:
        """Calculate confidence in the assessment"""
        
        # Factors that increase confidence
        confidence_factors = []
        
        # Clear entity identification increases confidence
        if entities:
            high_confidence_entities = [e for e in entities if e.confidence > 0.8]
            if high_confidence_entities:
                confidence_factors.append(0.2)
        
        # Consistent scores across dimensions
        scores = [market_impact, company_impact, time_sensitivity, stakeholder_impact]
        score_variance = np.var(scores)
        
        if score_variance < 0.1:  # Low variance = consistent assessment
            confidence_factors.append(0.15)
        
        # High or low extreme scores are usually more confident
        extreme_scores = [s for s in scores if s > 0.8 or s < 0.2]
        if extreme_scores:
            confidence_factors.append(0.15)
        
        # Base confidence
        base_confidence = 0.6
        bonus_confidence = sum(confidence_factors)
        
        return min(1.0, base_confidence + bonus_confidence)
    
    async def _generate_reasoning(
        self,
        event: NewsEvent,
        market_impact: float,
        company_impact: float,
        time_sensitivity: float,
        stakeholder_impact: float
    ) -> str:
        """Generate human-readable reasoning for the assessment"""
        
        reasoning_parts = []
        
        # Market impact reasoning
        if market_impact > 0.8:
            reasoning_parts.append("High market impact due to significant financial implications")
        elif market_impact > 0.6:
            reasoning_parts.append("Moderate market impact expected")
        
        # Company impact reasoning
        if company_impact > 0.8:
            reasoning_parts.append("Major company-specific implications")
        elif company_impact > 0.6:
            reasoning_parts.append("Notable company impact")
        
        # Time sensitivity reasoning
        if time_sensitivity > 0.8:
            reasoning_parts.append("High time sensitivity - immediate attention required")
        elif time_sensitivity > 0.6:
            reasoning_parts.append("Time-sensitive information")
        
        # Event type consideration
        if event.classification:
            event_type = event.classification.event_type
            if event_type in [EventType.BREAKING_NEWS, EventType.EARNINGS_ANNOUNCEMENT]:
                reasoning_parts.append(f"High-priority event type: {event_type.value}")
        
        if not reasoning_parts:
            reasoning_parts.append("Standard assessment based on content analysis")
        
        return ". ".join(reasoning_parts) + "."
    
    # Helper methods for specific assessments
    
    def _get_event_type_market_impact(self, event_type: Optional[EventType]) -> float:
        """Get market impact score based on event type"""
        if not event_type:
            return 0.5
        
        impact_scores = {
            EventType.BREAKING_NEWS: 0.9,
            EventType.EARNINGS_ANNOUNCEMENT: 0.8,
            EventType.MERGER_ACQUISITION: 0.9,
            EventType.REGULATORY_UPDATE: 0.7,
            EventType.MARKET_MOVEMENT: 0.8,
            EventType.ECONOMIC_INDICATOR: 0.7,
            EventType.ANALYST_UPGRADE: 0.6,
            EventType.ANALYST_DOWNGRADE: 0.6,
            EventType.IPO_NEWS: 0.7,
            EventType.BANKRUPTCY: 1.0,
            EventType.EXECUTIVE_CHANGE: 0.5,
            EventType.PRODUCT_LAUNCH: 0.4,
            EventType.GENERAL_NEWS: 0.3
        }
        
        return impact_scores.get(event_type, 0.5)
    
    def _get_event_type_severity_modifier(self, event_type: EventType) -> float:
        """Get severity modifier based on event type"""
        modifiers = {
            EventType.BREAKING_NEWS: 1.2,
            EventType.BANKRUPTCY: 1.3,
            EventType.MERGER_ACQUISITION: 1.1,
            EventType.EARNINGS_ANNOUNCEMENT: 1.1,
            EventType.REGULATORY_UPDATE: 1.1,
            EventType.IPO_NEWS: 1.1,
            EventType.GENERAL_NEWS: 0.9,
            EventType.PRODUCT_LAUNCH: 0.9
        }
        
        return modifiers.get(event_type, 1.0)
    
    def _assess_entity_market_impact(self, entities: List[Entity]) -> float:
        """Assess market impact based on entities involved"""
        if not entities:
            return 0.3
        
        # Major companies and tickers have higher impact
        major_entities = 0
        total_entities = len(entities)
        
        for entity in entities:
            if entity.entity_type == 'TICKER':
                if entity.ticker_symbol in ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA']:
                    major_entities += 2  # Mega-cap stocks
                else:
                    major_entities += 1
            elif entity.entity_type in ['COMPANY', 'ORG']:
                if entity.market_cap and ('B' in entity.market_cap or 'T' in entity.market_cap):
                    major_entities += 1
        
        # Calculate impact score
        if major_entities >= 3:
            return 0.9
        elif major_entities >= 2:
            return 0.7
        elif major_entities >= 1:
            return 0.6
        else:
            return 0.4
    
    def _assess_financial_metrics_impact(self, text: str) -> float:
        """Assess impact based on financial metrics mentioned"""
        high_impact_metrics = [
            r'\$\d+\.?\d*\s*billion', r'\$\d+\.?\d*b\b', 
            r'\d+%\s*(?:increase|decrease|drop|rise)',
            r'eps.*\$\d+\.\d+', r'revenue.*\$\d+\.?\d*\s*(?:billion|million)'
        ]
        
        matches = 0
        for pattern in high_impact_metrics:
            matches += len(re.findall(pattern, text, re.IGNORECASE))
        
        return min(1.0, matches * 0.3)
    
    def _assess_market_hours_impact(self, published_at: Optional[datetime]) -> float:
        """Assess urgency based on market hours"""
        if not published_at:
            return 0.5
        
        # Convert to EST/EDT (market hours)
        # Simplified: assume published_at is in UTC
        hour = published_at.hour
        
        # Market hours: 9:30 AM - 4:00 PM EST (14:30 - 21:00 UTC)
        if 14 <= hour <= 21:  # During market hours
            return 1.0
        elif 12 <= hour <= 23:  # Extended hours
            return 0.8
        else:  # Outside market hours
            return 0.5
    
    def _load_severity_weights(self) -> Dict[str, float]:
        """Load severity assessment weights"""
        return {
            'market_impact': 0.35,
            'company_impact': 0.25,
            'time_sensitivity': 0.25,
            'stakeholder_impact': 0.15
        }
    
    def _load_urgency_factors(self) -> Dict[str, float]:
        """Load urgency assessment factors"""
        return {
            'breaking_news': 0.9,
            'market_hours': 0.3,
            'after_hours': 0.2,
            'weekend': 0.1
        }
    
    def _load_market_impact_keywords(self) -> Dict[str, List[str]]:
        """Load market impact keywords"""
        return {
            'high': [
                'bankruptcy', 'chapter 11', 'insolvency', 'default',
                'merger', 'acquisition', 'takeover', 'buyout',
                'earnings miss', 'earnings beat', 'guidance',
                'fda approval', 'fda rejection', 'recall',
                'investigation', 'lawsuit', 'settlement',
                'ceo', 'resignation', 'fired', 'stepping down',
                'halt', 'suspend', 'delisted'
            ],
            'medium': [
                'revenue', 'profit', 'loss', 'sales',
                'upgrade', 'downgrade', 'target',
                'partnership', 'agreement', 'contract',
                'expansion', 'growth', 'decline',
                'announcement', 'launch', 'release'
            ]
        }
    
    async def close(self):
        """Close HTTP client and cleanup resources"""
        await self.http_client.aclose() 