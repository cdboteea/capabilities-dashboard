"""
Event Classification Processor - LLM-powered content classification
"""

import asyncio
import httpx
import json
import re
import structlog
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import spacy
from transformers import pipeline
import numpy as np

from ..models import (
    EventType, ClassificationResult, ClassificationConfidence,
    KeywordMatch, NewsEvent
)

logger = structlog.get_logger(__name__)

class EventClassifier:
    """Advanced event classification using multiple approaches"""
    
    def __init__(self, mac_studio_endpoint: str = "http://10.0.0.100:8000"):
        self.mac_studio_endpoint = mac_studio_endpoint
        self.http_client = httpx.AsyncClient(timeout=60.0)
        
        # Initialize NLP models
        self.nlp = None
        self.sentiment_pipeline = None
        
        # Classification keywords and patterns
        self.keyword_patterns = self._load_keyword_patterns()
        
        # Model state
        self.model_loaded = False
    
    async def initialize(self):
        """Initialize NLP models and resources"""
        try:
            logger.info("Initializing Event Classifier")
            
            # Load spaCy model
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy model not found, using basic classification")
            
            # Load sentiment analysis pipeline
            try:
                self.sentiment_pipeline = pipeline(
                    "sentiment-analysis",
                    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                    return_all_scores=True
                )
            except Exception as e:
                logger.warning("Failed to load sentiment pipeline", error=str(e))
            
            self.model_loaded = True
            logger.info("Event Classifier initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Event Classifier", error=str(e))
            raise
    
    async def classify_event(self, event: NewsEvent) -> ClassificationResult:
        """Classify a news event using multiple classification methods"""
        logger.info("Classifying event", event_id=event.event_id)
        
        try:
            # Multi-stage classification
            results = {}
            
            # 1. Keyword-based classification (fast baseline)
            keyword_result = self._keyword_classification(event.title, event.content)
            results['keyword'] = keyword_result
            
            # 2. Pattern-based classification
            pattern_result = self._pattern_classification(event.title, event.content)
            results['pattern'] = pattern_result
            
            # 3. LLM-based classification (most accurate)
            llm_result = await self._llm_classification(event)
            results['llm'] = llm_result
            
            # 4. Ensemble classification (combine all methods)
            final_result = self._ensemble_classification(results, event)
            
            logger.info("Event classification completed", 
                       event_id=event.event_id,
                       event_type=final_result.event_type.value,
                       confidence=final_result.confidence)
            
            return final_result
            
        except Exception as e:
            logger.error("Event classification failed", 
                        error=str(e), 
                        event_id=event.event_id)
            
            # Fallback classification
            return ClassificationResult(
                event_type=EventType.GENERAL_NEWS,
                confidence=0.5,
                confidence_level=ClassificationConfidence.MEDIUM,
                primary_indicators=["fallback_classification"],
                reasoning="Classification failed, using fallback",
                model_used="fallback"
            )
    
    def _keyword_classification(self, title: str, content: str) -> Dict[str, Any]:
        """Fast keyword-based classification"""
        text = f"{title} {content}".lower()
        
        # Score each event type based on keyword matches
        type_scores = {}
        keyword_matches = []
        
        for event_type, keywords in self.keyword_patterns.items():
            score = 0
            matches = []
            
            for keyword_data in keywords:
                keyword = keyword_data['keyword'].lower()
                weight = keyword_data['weight']
                category = keyword_data['category']
                
                # Count matches
                match_count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text))
                if match_count > 0:
                    score += match_count * weight
                    
                    # Find positions
                    positions = [m.start() for m in re.finditer(r'\b' + re.escape(keyword) + r'\b', text)]
                    
                    match = KeywordMatch(
                        keyword=keyword,
                        category=category,
                        weight=weight,
                        match_count=match_count,
                        positions=positions
                    )
                    matches.append(match)
            
            if score > 0:
                type_scores[event_type] = score
                keyword_matches.extend(matches)
        
        # Determine best match
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            max_score = type_scores[best_type]
            
            # Normalize score to confidence
            confidence = min(1.0, max_score / 10.0)  # Adjust scaling as needed
            
            return {
                'event_type': best_type,
                'confidence': confidence,
                'scores': type_scores,
                'keyword_matches': keyword_matches
            }
        
        return {
            'event_type': EventType.GENERAL_NEWS.value,
            'confidence': 0.3,
            'scores': {},
            'keyword_matches': []
        }
    
    def _pattern_classification(self, title: str, content: str) -> Dict[str, Any]:
        """Pattern-based classification using regex and structure"""
        text = f"{title} {content}"
        
        # Define classification patterns
        patterns = {
            EventType.EARNINGS_ANNOUNCEMENT.value: [
                r'\b(earnings|quarterly|q[1-4]|revenue|profit|loss)\b.*\b(report|results|announcement)\b',
                r'\b(eps|earnings per share)\b',
                r'\b(guidance|outlook)\b.*\b(quarter|year)\b'
            ],
            EventType.MERGER_ACQUISITION.value: [
                r'\b(merger|acquisition|acquire|merge|buyout|takeover)\b',
                r'\b(deal|transaction)\b.*\b(billion|million)\b',
                r'\b(combine|consolidate)\b.*\b(companies|firms)\b'
            ],
            EventType.REGULATORY_UPDATE.value: [
                r'\b(fda|sec|ftc|doj|regulator|regulatory)\b',
                r'\b(approval|approve|regulation|rule|compliance)\b',
                r'\b(investigation|probe|lawsuit|settlement)\b'
            ],
            EventType.ANALYST_UPGRADE.value: [
                r'\b(upgrade|raises|increases)\b.*\b(target|rating|price)\b',
                r'\b(outperform|buy|strong buy)\b',
                r'\b(analyst|research|rating)\b.*\b(positive|bullish)\b'
            ],
            EventType.ANALYST_DOWNGRADE.value: [
                r'\b(downgrade|lowers|reduces|cuts)\b.*\b(target|rating|price)\b',
                r'\b(underperform|sell|strong sell)\b',
                r'\b(analyst|research|rating)\b.*\b(negative|bearish)\b'
            ],
            EventType.EXECUTIVE_CHANGE.value: [
                r'\b(ceo|cfo|coo|president|chairman)\b.*\b(resign|retire|leave|appoint|hire|name)\b',
                r'\b(leadership|management)\b.*\b(change|transition)\b',
                r'\b(successor|replacement|interim)\b'
            ],
            EventType.PRODUCT_LAUNCH.value: [
                r'\b(launch|introduce|release|unveil)\b.*\b(product|service|feature)\b',
                r'\b(new|latest)\b.*\b(version|model|generation)\b',
                r'\b(announce|debut)\b.*\b(innovation|technology)\b'
            ]
        }
        
        # Score each pattern
        pattern_scores = {}
        
        for event_type, type_patterns in patterns.items():
            score = 0
            for pattern in type_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                score += len(matches) * 2  # Weight pattern matches higher
            
            if score > 0:
                pattern_scores[event_type] = score
        
        if pattern_scores:
            best_type = max(pattern_scores, key=pattern_scores.get)
            max_score = pattern_scores[best_type]
            
            # Pattern matching tends to be more reliable than keywords
            confidence = min(1.0, max_score / 5.0)
            
            return {
                'event_type': best_type,
                'confidence': confidence,
                'scores': pattern_scores
            }
        
        return {
            'event_type': EventType.GENERAL_NEWS.value,
            'confidence': 0.2,
            'scores': {}
        }
    
    async def _llm_classification(self, event: NewsEvent) -> Dict[str, Any]:
        """LLM-based classification using Mac Studio"""
        try:
            # Prepare classification prompt
            prompt = self._build_classification_prompt(event)
            
            # Call Mac Studio LLM
            llm_response = await self._call_mac_studio_llm(prompt)
            
            # Parse LLM response
            classification = self._parse_llm_classification(llm_response)
            
            return classification
            
        except Exception as e:
            logger.error("LLM classification failed", error=str(e), event_id=event.event_id)
            return {
                'event_type': EventType.GENERAL_NEWS.value,
                'confidence': 0.5,
                'reasoning': f"LLM classification failed: {str(e)}",
                'model_used': 'llm_fallback'
            }
    
    def _build_classification_prompt(self, event: NewsEvent) -> str:
        """Build classification prompt for LLM"""
        
        # Get available event types for context
        event_types_desc = {
            EventType.BREAKING_NEWS: "Urgent, time-sensitive news requiring immediate attention",
            EventType.EARNINGS_ANNOUNCEMENT: "Quarterly or annual financial results, earnings reports",
            EventType.MERGER_ACQUISITION: "Company mergers, acquisitions, buyouts, takeovers",
            EventType.REGULATORY_UPDATE: "Regulatory approvals, investigations, compliance news",
            EventType.MARKET_MOVEMENT: "Significant stock price movements, market volatility",
            EventType.ECONOMIC_INDICATOR: "Economic data releases, inflation, employment, GDP",
            EventType.CORPORATE_ACTION: "Dividends, stock splits, spin-offs, buybacks",
            EventType.ANALYST_UPGRADE: "Analyst upgrades, price target increases, positive ratings",
            EventType.ANALYST_DOWNGRADE: "Analyst downgrades, price target cuts, negative ratings",
            EventType.PRODUCT_LAUNCH: "New product announcements, launches, innovations",
            EventType.EXECUTIVE_CHANGE: "CEO, executive appointments, resignations, leadership changes",
            EventType.PARTNERSHIP: "Strategic partnerships, joint ventures, collaborations",
            EventType.IPO_NEWS: "Initial public offerings, listing announcements",
            EventType.BANKRUPTCY: "Bankruptcy filings, financial distress, insolvency",
            EventType.LITIGATION: "Lawsuits, legal disputes, court decisions",
            EventType.CYBER_SECURITY: "Data breaches, cyber attacks, security incidents",
            EventType.ESG_NEWS: "Environmental, social, governance news, sustainability",
            EventType.GENERAL_NEWS: "General news that doesn't fit other categories"
        }
        
        types_list = "\n".join([f"- {t.value}: {desc}" for t, desc in event_types_desc.items()])
        
        prompt = f"""
You are an expert financial news analyst. Classify the following news event into the most appropriate category.

TITLE: {event.title}

CONTENT: {event.content[:2000]}  

SOURCE: {event.source_id}
PUBLISHED: {event.published_at.isoformat()}

AVAILABLE CATEGORIES:
{types_list}

Analyze this news event and respond with:

1. PRIMARY_CLASSIFICATION: Choose the most appropriate category from the list above
2. CONFIDENCE: Your confidence in this classification (0.0 to 1.0)
3. REASONING: Explain why you chose this classification (1-2 sentences)
4. SECONDARY_OPTIONS: List 2 alternative classifications with confidence scores
5. KEY_INDICATORS: List 3-5 key words/phrases that influenced your decision
6. MARKET_IMPACT: Assess potential market impact (LOW/MEDIUM/HIGH)
7. TIME_SENSITIVITY: Assess time sensitivity (LOW/MEDIUM/HIGH/URGENT)

Be precise and analytical in your classification. Focus on the core business impact and news type.
"""
        
        return prompt
    
    async def _call_mac_studio_llm(self, prompt: str) -> str:
        """Call Mac Studio LLM for classification"""
        try:
            payload = {
                "model": "qwen-3-72b:latest",  # Use main model for classification
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert financial news analyst specializing in event classification. Provide precise, analytical classifications based on business impact and news type."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,  # Low temperature for consistent classification
                "max_tokens": 1000
            }
            
            async with self.http_client as client:
                response = await client.post(
                    f"{self.mac_studio_endpoint}/v1/chat/completions",
                    json=payload,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data['choices'][0]['message']['content']
                else:
                    logger.error("LLM request failed", 
                               status_code=response.status_code,
                               response=response.text)
                    return "LLM classification unavailable"
                    
        except Exception as e:
            logger.error("LLM call failed", error=str(e))
            return f"LLM classification failed: {str(e)}"
    
    def _parse_llm_classification(self, response: str) -> Dict[str, Any]:
        """Parse LLM classification response"""
        classification = {
            'event_type': EventType.GENERAL_NEWS.value,
            'confidence': 0.7,
            'reasoning': response,
            'model_used': 'mac_studio_llm',
            'market_impact': 'MEDIUM',
            'time_sensitivity': 'MEDIUM',
            'key_indicators': [],
            'secondary_options': []
        }
        
        try:
            # Extract structured information using regex
            
            # Primary classification
            primary_match = re.search(r'PRIMARY_CLASSIFICATION:\s*([^\n]+)', response, re.IGNORECASE)
            if primary_match:
                classification_text = primary_match.group(1).strip().lower()
                
                # Map to EventType
                for event_type in EventType:
                    if event_type.value in classification_text or event_type.name.lower() in classification_text:
                        classification['event_type'] = event_type.value
                        break
            
            # Confidence
            confidence_match = re.search(r'CONFIDENCE:\s*([0-9.]+)', response, re.IGNORECASE)
            if confidence_match:
                try:
                    confidence = float(confidence_match.group(1))
                    classification['confidence'] = max(0.0, min(1.0, confidence))
                except ValueError:
                    pass
            
            # Reasoning
            reasoning_match = re.search(r'REASONING:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\d+\.|$)', response, re.IGNORECASE)
            if reasoning_match:
                classification['reasoning'] = reasoning_match.group(1).strip()
            
            # Key indicators
            indicators_match = re.search(r'KEY_INDICATORS:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\d+\.|$)', response, re.IGNORECASE)
            if indicators_match:
                indicators_text = indicators_match.group(1)
                indicators = [ind.strip('- ').strip() for ind in indicators_text.split('\n') if ind.strip()]
                classification['key_indicators'] = indicators[:5]
            
            # Market impact
            impact_match = re.search(r'MARKET_IMPACT:\s*([^\n]+)', response, re.IGNORECASE)
            if impact_match:
                classification['market_impact'] = impact_match.group(1).strip().upper()
            
            # Time sensitivity
            time_match = re.search(r'TIME_SENSITIVITY:\s*([^\n]+)', response, re.IGNORECASE)
            if time_match:
                classification['time_sensitivity'] = time_match.group(1).strip().upper()
            
            # Secondary options
            secondary_match = re.search(r'SECONDARY_OPTIONS:\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\d+\.|$)', response, re.IGNORECASE)
            if secondary_match:
                secondary_text = secondary_match.group(1)
                # Parse secondary options (simplified)
                classification['secondary_options'] = secondary_text.split('\n')[:2]
            
        except Exception as e:
            logger.error("Failed to parse LLM classification", error=str(e))
        
        return classification
    
    def _ensemble_classification(
        self, 
        results: Dict[str, Dict[str, Any]], 
        event: NewsEvent
    ) -> ClassificationResult:
        """Combine classification results using ensemble method"""
        
        # Weight different classification methods
        weights = {
            'keyword': 0.2,
            'pattern': 0.3,
            'llm': 0.5
        }
        
        # Aggregate scores for each event type
        type_scores = {}
        all_keyword_matches = []
        
        for method, result in results.items():
            if not result:
                continue
            
            event_type = result.get('event_type', EventType.GENERAL_NEWS.value)
            confidence = result.get('confidence', 0.0)
            weight = weights.get(method, 0.0)
            
            # Add weighted score
            if event_type not in type_scores:
                type_scores[event_type] = 0.0
            
            type_scores[event_type] += confidence * weight
            
            # Collect keyword matches
            if 'keyword_matches' in result:
                all_keyword_matches.extend(result['keyword_matches'])
        
        # Determine final classification
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            final_confidence = type_scores[best_type]
            
            # Adjust confidence based on agreement between methods
            agreement_bonus = 0.0
            if len(type_scores) == 1:  # All methods agree
                agreement_bonus = 0.1
            elif best_type in [r.get('event_type') for r in results.values()]:
                agreement_count = sum(1 for r in results.values() 
                                    if r and r.get('event_type') == best_type)
                agreement_bonus = (agreement_count / len(results)) * 0.1
            
            final_confidence = min(1.0, final_confidence + agreement_bonus)
        else:
            best_type = EventType.GENERAL_NEWS.value
            final_confidence = 0.5
        
        # Determine confidence level
        confidence_level = self._get_confidence_level(final_confidence)
        
        # Create alternative classifications
        sorted_types = sorted(type_scores.items(), key=lambda x: x[1], reverse=True)
        alternatives = [
            {event_type: score} 
            for event_type, score in sorted_types[1:4]  # Top 3 alternatives
        ]
        
        # Extract key indicators
        llm_result = results.get('llm', {})
        key_indicators = llm_result.get('key_indicators', [])
        
        # Build reasoning
        reasoning_parts = []
        if llm_result.get('reasoning'):
            reasoning_parts.append(f"LLM: {llm_result['reasoning']}")
        
        method_scores = [f"{method}: {result.get('confidence', 0):.2f}" 
                        for method, result in results.items() if result]
        reasoning_parts.append(f"Method scores: {', '.join(method_scores)}")
        
        final_reasoning = ". ".join(reasoning_parts)
        
        return ClassificationResult(
            event_type=EventType(best_type),
            confidence=final_confidence,
            confidence_level=confidence_level,
            primary_indicators=key_indicators[:5],
            secondary_indicators=[],
            keyword_matches=all_keyword_matches,
            alternative_types=alternatives,
            reasoning=final_reasoning,
            model_used="ensemble_classifier"
        )
    
    def _get_confidence_level(self, confidence: float) -> ClassificationConfidence:
        """Convert numeric confidence to confidence level"""
        if confidence >= 0.9:
            return ClassificationConfidence.VERY_HIGH
        elif confidence >= 0.8:
            return ClassificationConfidence.HIGH
        elif confidence >= 0.6:
            return ClassificationConfidence.MEDIUM
        elif confidence >= 0.4:
            return ClassificationConfidence.LOW
        else:
            return ClassificationConfidence.VERY_LOW
    
    def _load_keyword_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load keyword patterns for classification"""
        
        patterns = {
            EventType.EARNINGS_ANNOUNCEMENT.value: [
                {'keyword': 'earnings', 'weight': 3.0, 'category': 'financial'},
                {'keyword': 'quarterly', 'weight': 2.5, 'category': 'financial'},
                {'keyword': 'revenue', 'weight': 2.5, 'category': 'financial'},
                {'keyword': 'profit', 'weight': 2.0, 'category': 'financial'},
                {'keyword': 'eps', 'weight': 3.0, 'category': 'financial'},
                {'keyword': 'guidance', 'weight': 2.0, 'category': 'financial'},
                {'keyword': 'results', 'weight': 1.5, 'category': 'financial'},
                {'keyword': 'outlook', 'weight': 1.5, 'category': 'financial'}
            ],
            EventType.MERGER_ACQUISITION.value: [
                {'keyword': 'merger', 'weight': 3.0, 'category': 'corporate'},
                {'keyword': 'acquisition', 'weight': 3.0, 'category': 'corporate'},
                {'keyword': 'acquire', 'weight': 2.5, 'category': 'corporate'},
                {'keyword': 'buyout', 'weight': 2.5, 'category': 'corporate'},
                {'keyword': 'takeover', 'weight': 2.5, 'category': 'corporate'},
                {'keyword': 'deal', 'weight': 1.5, 'category': 'corporate'},
                {'keyword': 'combine', 'weight': 1.5, 'category': 'corporate'}
            ],
            EventType.REGULATORY_UPDATE.value: [
                {'keyword': 'fda', 'weight': 3.0, 'category': 'regulatory'},
                {'keyword': 'sec', 'weight': 3.0, 'category': 'regulatory'},
                {'keyword': 'approval', 'weight': 2.5, 'category': 'regulatory'},
                {'keyword': 'regulatory', 'weight': 2.5, 'category': 'regulatory'},
                {'keyword': 'investigation', 'weight': 2.0, 'category': 'regulatory'},
                {'keyword': 'probe', 'weight': 2.0, 'category': 'regulatory'},
                {'keyword': 'lawsuit', 'weight': 2.0, 'category': 'regulatory'},
                {'keyword': 'settlement', 'weight': 2.0, 'category': 'regulatory'}
            ],
            EventType.ANALYST_UPGRADE.value: [
                {'keyword': 'upgrade', 'weight': 3.0, 'category': 'analyst'},
                {'keyword': 'raises', 'weight': 2.0, 'category': 'analyst'},
                {'keyword': 'target', 'weight': 2.0, 'category': 'analyst'},
                {'keyword': 'outperform', 'weight': 2.5, 'category': 'analyst'},
                {'keyword': 'buy', 'weight': 2.0, 'category': 'analyst'},
                {'keyword': 'bullish', 'weight': 2.0, 'category': 'analyst'}
            ],
            EventType.ANALYST_DOWNGRADE.value: [
                {'keyword': 'downgrade', 'weight': 3.0, 'category': 'analyst'},
                {'keyword': 'lowers', 'weight': 2.0, 'category': 'analyst'},
                {'keyword': 'cuts', 'weight': 2.0, 'category': 'analyst'},
                {'keyword': 'underperform', 'weight': 2.5, 'category': 'analyst'},
                {'keyword': 'sell', 'weight': 2.0, 'category': 'analyst'},
                {'keyword': 'bearish', 'weight': 2.0, 'category': 'analyst'}
            ],
            EventType.EXECUTIVE_CHANGE.value: [
                {'keyword': 'ceo', 'weight': 2.5, 'category': 'executive'},
                {'keyword': 'cfo', 'weight': 2.5, 'category': 'executive'},
                {'keyword': 'president', 'weight': 2.0, 'category': 'executive'},
                {'keyword': 'resign', 'weight': 2.5, 'category': 'executive'},
                {'keyword': 'retire', 'weight': 2.0, 'category': 'executive'},
                {'keyword': 'appoint', 'weight': 2.0, 'category': 'executive'},
                {'keyword': 'leadership', 'weight': 1.5, 'category': 'executive'}
            ],
            EventType.PRODUCT_LAUNCH.value: [
                {'keyword': 'launch', 'weight': 2.5, 'category': 'product'},
                {'keyword': 'introduce', 'weight': 2.0, 'category': 'product'},
                {'keyword': 'release', 'weight': 2.0, 'category': 'product'},
                {'keyword': 'unveil', 'weight': 2.0, 'category': 'product'},
                {'keyword': 'new product', 'weight': 2.5, 'category': 'product'},
                {'keyword': 'innovation', 'weight': 1.5, 'category': 'product'}
            ],
            EventType.BREAKING_NEWS.value: [
                {'keyword': 'breaking', 'weight': 3.0, 'category': 'urgency'},
                {'keyword': 'urgent', 'weight': 2.5, 'category': 'urgency'},
                {'keyword': 'alert', 'weight': 2.5, 'category': 'urgency'},
                {'keyword': 'immediate', 'weight': 2.0, 'category': 'urgency'},
                {'keyword': 'emergency', 'weight': 2.5, 'category': 'urgency'}
            ]
        }
        
        return patterns
    
    async def close(self):
        """Close HTTP client and cleanup resources"""
        await self.http_client.aclose() 