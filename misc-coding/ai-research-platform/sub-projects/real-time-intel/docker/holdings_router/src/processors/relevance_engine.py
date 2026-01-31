"""
Portfolio Relevance Scoring Engine - CORE BUSINESS LOGIC

This is the heart of the Holdings Router that determines how relevant 
a news event is to a user's portfolio using a 4-factor scoring model.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RelevanceLevel(str, Enum):
    """Event relevance levels."""
    CRITICAL = "critical"      # 0.8+ - Immediate action required
    HIGH = "high"             # 0.6-0.8 - Important for portfolio
    MEDIUM = "medium"         # 0.4-0.6 - Moderate interest
    LOW = "low"              # 0.2-0.4 - Background awareness
    IRRELEVANT = "irrelevant" # <0.2 - No portfolio impact


@dataclass
class RelevanceScore:
    """Detailed relevance scoring result."""
    overall_score: float  # 0.0 to 1.0
    level: RelevanceLevel
    
    # Component scores
    entity_match_score: float
    sector_correlation_score: float
    sentiment_impact_score: float
    position_weight_score: float
    
    # Matched entities and reasoning
    matched_entities: List[str]
    affected_positions: List[str]
    reasoning: str
    confidence: float


class RelevanceEngine:
    """
    Portfolio-aware event relevance scoring engine.
    
    SCORING ALGORITHM:
    1. Entity Matching (40%): Direct symbol/company matches
    2. Sector Correlation (25%): Sector-wide impact assessment  
    3. Sentiment Impact (20%): Sentiment strength and direction
    4. Position Weight (15%): Portfolio allocation impact
    
    Final Score = Weighted sum with position size multiplier
    """
    
    def __init__(self):
        self.sector_correlations = {
            'technology': 0.8, 'healthcare': 0.7, 'financials': 0.9,
            'energy': 0.8, 'consumer': 0.6, 'industrials': 0.7,
            'materials': 0.7, 'utilities': 0.5, 'real_estate': 0.6,
            'communications': 0.7
        }
    
    def calculate_relevance(
        self,
        event_text: str,
        event_entities: List[str],
        event_sentiment: Optional[Dict],
        user_portfolio: Dict,
        event_metadata: Optional[Dict] = None
    ) -> RelevanceScore:
        """Calculate comprehensive relevance score for an event."""
        
        # 1. Entity Matching Score (40% weight)
        entity_score, matched_entities, affected_positions = self._calculate_entity_match_score(
            event_entities, event_text, user_portfolio
        )
        
        # 2. Sector Correlation Score (25% weight)
        sector_score = self._calculate_sector_correlation_score(
            event_text, event_entities, user_portfolio, event_metadata
        )
        
        # 3. Sentiment Impact Score (20% weight)
        sentiment_score = self._calculate_sentiment_impact_score(
            event_sentiment, matched_entities, affected_positions
        )
        
        # 4. Position Weight Score (15% weight)
        position_score = self._calculate_position_weight_score(
            affected_positions, user_portfolio
        )
        
        # Calculate weighted overall score
        overall_score = (
            entity_score * 0.40 +
            sector_score * 0.25 +
            sentiment_score * 0.20 +
            position_score * 0.15
        )
        
        # Apply position size multiplier for large holdings
        overall_score = self._apply_position_multiplier(overall_score, affected_positions, user_portfolio)
        overall_score = max(0.0, min(1.0, overall_score))
        
        # Determine relevance level
        level = self._determine_relevance_level(overall_score)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            entity_score, sector_score, sentiment_score, position_score,
            matched_entities, affected_positions
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            event_entities, event_sentiment, user_portfolio, matched_entities
        )
        
        return RelevanceScore(
            overall_score=overall_score,
            level=level,
            entity_match_score=entity_score,
            sector_correlation_score=sector_score,
            sentiment_impact_score=sentiment_score,
            position_weight_score=position_score,
            matched_entities=matched_entities,
            affected_positions=affected_positions,
            reasoning=reasoning,
            confidence=confidence
        )
    
    def _calculate_entity_match_score(self, event_entities: List[str], event_text: str, portfolio: Dict) -> Tuple[float, List[str], List[str]]:
        """Calculate score based on direct entity matches."""
        matched_entities = []
        affected_positions = []
        portfolio_symbols = set(holding['symbol'] for holding in portfolio.get('holdings', []))
        
        # Direct symbol matches
        for entity in event_entities:
            if entity.upper() in portfolio_symbols:
                matched_entities.append(entity)
                affected_positions.append(entity.upper())
        
        # Company name matching
        for holding in portfolio.get('holdings', []):
            company_name = holding.get('name', '').lower()
            symbol = holding['symbol']
            
            if len(company_name) > 3 and company_name in event_text.lower():
                if symbol not in affected_positions:
                    matched_entities.append(company_name)
                    affected_positions.append(symbol)
        
        if not matched_entities:
            return 0.0, [], []
        
        # Score with diminishing returns
        base_score = min(0.9, len(matched_entities) * 0.3)
        exact_matches = sum(1 for entity in event_entities if entity.upper() in portfolio_symbols)
        if exact_matches > 0:
            base_score = min(1.0, base_score + exact_matches * 0.2)
        
        return base_score, matched_entities, affected_positions
    
    def _calculate_sector_correlation_score(self, event_text: str, event_entities: List[str], portfolio: Dict, metadata: Optional[Dict]) -> float:
        """Calculate score based on sector-wide impact."""
        event_sectors = self._extract_event_sectors(event_text, metadata)
        if not event_sectors:
            return 0.0
        
        # Get portfolio sector exposure
        portfolio_sectors = {}
        total_value = portfolio.get('total_value', 1)
        
        for holding in portfolio.get('holdings', []):
            sector = holding.get('sector')
            if sector:
                market_value = holding.get('market_value', 0)
                portfolio_sectors[sector] = portfolio_sectors.get(sector, 0) + market_value
        
        # Calculate correlation
        sector_score = 0.0
        for event_sector in event_sectors:
            if event_sector in portfolio_sectors:
                sector_weight = portfolio_sectors[event_sector] / total_value
                correlation_strength = self.sector_correlations.get(event_sector, 0.5)
                sector_score += sector_weight * correlation_strength
        
        return min(1.0, sector_score)
    
    def _calculate_sentiment_impact_score(self, sentiment: Optional[Dict], matched_entities: List[str], affected_positions: List[str]) -> float:
        """Calculate score based on sentiment strength."""
        if not sentiment or not matched_entities:
            return 0.0
        
        overall_sentiment = sentiment.get('overall', {})
        sentiment_score = overall_sentiment.get('score', 0.0)
        sentiment_confidence = overall_sentiment.get('confidence', 0.0)
        
        # Impact magnitude (absolute value)
        impact_magnitude = abs(sentiment_score)
        weighted_impact = impact_magnitude * sentiment_confidence
        
        # Entity-specific sentiment boost
        entity_sentiments = sentiment.get('entities', [])
        if entity_sentiments:
            entity_boost = 0.0
            for entity_sentiment in entity_sentiments:
                entity = entity_sentiment.get('entity', '')
                if entity in matched_entities:
                    entity_score = abs(entity_sentiment.get('sentiment', {}).get('score', 0.0))
                    entity_boost += entity_score * 0.2
            weighted_impact = min(1.0, weighted_impact + entity_boost)
        
        return weighted_impact
    
    def _calculate_position_weight_score(self, affected_positions: List[str], portfolio: Dict) -> float:
        """Calculate score based on position sizes."""
        if not affected_positions:
            return 0.0
        
        total_value = portfolio.get('total_value', 1)
        position_score = 0.0
        
        for holding in portfolio.get('holdings', []):
            if holding['symbol'] in affected_positions:
                market_value = holding.get('market_value', 0)
                position_weight = market_value / total_value
                
                if position_weight >= 0.10:     # 10%+ positions
                    position_score += 0.8
                elif position_weight >= 0.05:  # 5%+ positions
                    position_score += 0.6
                elif position_weight >= 0.02:  # 2%+ positions
                    position_score += 0.4
                else:
                    position_score += 0.2
        
        return min(1.0, position_score)
    
    def _apply_position_multiplier(self, base_score: float, affected_positions: List[str], portfolio: Dict) -> float:
        """Apply multiplier for large position exposure."""
        if not affected_positions:
            return base_score
        
        total_value = portfolio.get('total_value', 1)
        max_position_weight = 0.0
        
        for holding in portfolio.get('holdings', []):
            if holding['symbol'] in affected_positions:
                market_value = holding.get('market_value', 0)
                position_weight = market_value / total_value
                max_position_weight = max(max_position_weight, position_weight)
        
        # Position size multipliers
        if max_position_weight >= 0.15:    # 15%+ position
            multiplier = 1.3
        elif max_position_weight >= 0.10:  # 10%+ position
            multiplier = 1.2
        elif max_position_weight >= 0.05:  # 5%+ position
            multiplier = 1.1
        else:
            multiplier = 1.0
        
        return min(1.0, base_score * multiplier)
    
    def _determine_relevance_level(self, score: float) -> RelevanceLevel:
        """Determine relevance level from numeric score."""
        if score >= 0.8:
            return RelevanceLevel.CRITICAL
        elif score >= 0.6:
            return RelevanceLevel.HIGH
        elif score >= 0.4:
            return RelevanceLevel.MEDIUM
        elif score >= 0.2:
            return RelevanceLevel.LOW
        else:
            return RelevanceLevel.IRRELEVANT
    
    def _generate_reasoning(self, entity_score: float, sector_score: float, sentiment_score: float, position_score: float, matched_entities: List[str], affected_positions: List[str]) -> str:
        """Generate human-readable reasoning."""
        reasons = []
        
        if entity_score > 0.5:
            reasons.append(f"Direct holdings match: {', '.join(matched_entities[:3])}")
        if sector_score > 0.3:
            reasons.append("Sector correlation detected")
        if sentiment_score > 0.6:
            reasons.append("Strong sentiment impact")
        elif sentiment_score > 0.3:
            reasons.append("Moderate sentiment impact")
        if position_score > 0.6:
            reasons.append("Large position exposure")
        elif position_score > 0.3:
            reasons.append("Notable position exposure")
        
        return "; ".join(reasons) if reasons else "Low relevance to portfolio holdings"
    
    def _calculate_confidence(self, entities: List[str], sentiment: Optional[Dict], portfolio: Dict, matched_entities: List[str]) -> float:
        """Calculate confidence in the relevance score."""
        confidence = 0.5  # Base confidence
        
        if len(entities) >= 3:
            confidence += 0.2
        elif len(entities) >= 1:
            confidence += 0.1
        
        if sentiment:
            sentiment_conf = sentiment.get('overall', {}).get('confidence', 0.0)
            confidence += sentiment_conf * 0.2
        
        if matched_entities:
            confidence += min(0.3, len(matched_entities) * 0.1)
        
        holding_count = len(portfolio.get('holdings', []))
        if holding_count >= 10:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _extract_event_sectors(self, text: str, metadata: Optional[Dict]) -> List[str]:
        """Extract relevant sectors from event text."""
        sectors = []
        
        if metadata and 'sectors' in metadata:
            sectors.extend(metadata['sectors'])
        
        # Sector keywords
        sector_keywords = {
            'technology': ['tech', 'software', 'ai', 'cloud', 'semiconductor'],
            'healthcare': ['pharma', 'biotech', 'medical', 'drug'],
            'financials': ['bank', 'financial', 'credit', 'insurance'],
            'energy': ['oil', 'gas', 'renewable', 'solar', 'energy'],
            'consumer': ['retail', 'consumer', 'shopping', 'brand'],
            'industrials': ['manufacturing', 'aerospace', 'construction'],
            'materials': ['mining', 'metals', 'chemicals'],
            'utilities': ['utility', 'electric', 'water', 'power'],
            'real_estate': ['real estate', 'reit', 'property'],
            'communications': ['telecom', 'media', 'entertainment']
        }
        
        text_lower = text.lower()
        for sector, keywords in sector_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                sectors.append(sector)
        
        return list(set(sectors))


# Global engine instance
relevance_engine = RelevanceEngine()
