"""
Content Enrichment Processor - Advanced content analysis and enrichment
"""

import asyncio
import httpx
import json
import re
import structlog
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import spacy
import nltk
import textstat
from langdetect import detect
try:
    from langdetect.lang_detect_exception import LangDetectException as LangDetectError
except ImportError:
    # Fallback for different langdetect versions
    class LangDetectError(Exception):
        pass
from transformers import pipeline
import yfinance as yf
import numpy as np

from ..models import (
    ContentEnrichment, Entity, NewsEvent
)

logger = structlog.get_logger(__name__)

class ContentEnricher:
    """Advanced content enrichment and analysis"""
    
    def __init__(self, mac_studio_endpoint: str = "http://10.0.0.100:8000"):
        self.mac_studio_endpoint = mac_studio_endpoint
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Initialize NLP components
        self.nlp = None
        self.sentiment_pipeline = None
        self.emotion_pipeline = None
        self.ner_pipeline = None
        
        # Financial data cache
        self.ticker_cache = {}
        
        # Model state
        self.models_loaded = False
    
    async def initialize(self):
        """Initialize NLP models and resources"""
        try:
            logger.info("Initializing Content Enricher")
            
            # Load spaCy model for NER and text processing
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy model not found, using basic enrichment")
            
            # Load sentiment analysis pipeline
            try:
                self.sentiment_pipeline = pipeline(
                    "sentiment-analysis",
                    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                    return_all_scores=True
                )
            except Exception as e:
                logger.warning("Failed to load sentiment pipeline", error=str(e))
            
            # Load emotion analysis pipeline
            try:
                self.emotion_pipeline = pipeline(
                    "text-classification",
                    model="j-hartmann/emotion-english-distilroberta-base",
                    return_all_scores=True
                )
            except Exception as e:
                logger.warning("Failed to load emotion pipeline", error=str(e))
            
            # Load NER pipeline for financial entities
            try:
                self.ner_pipeline = pipeline(
                    "ner",
                    model="dbmdz/bert-large-cased-finetuned-conll03-english",
                    aggregation_strategy="simple"
                )
            except Exception as e:
                logger.warning("Failed to load NER pipeline", error=str(e))
            
            # Download NLTK data if needed
            try:
                nltk.data.find('tokenizers/punkt')
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
            
            self.models_loaded = True
            logger.info("Content Enricher initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Content Enricher", error=str(e))
            raise
    
    async def enrich_content(self, event: NewsEvent) -> ContentEnrichment:
        """Perform comprehensive content enrichment"""
        logger.info("Enriching content", event_id=event.event_id)
        
        try:
            text = f"{event.title} {event.content}"
            
            # Parallel enrichment tasks
            tasks = []
            
            # 1. Sentiment and emotion analysis
            tasks.append(self._analyze_sentiment_emotion(text))
            
            # 2. Language and readability analysis
            tasks.append(self._analyze_language_readability(text))
            
            # 3. Topic and keyword extraction
            tasks.append(self._extract_topics_keywords(text))
            
            # 4. Financial metrics extraction
            tasks.append(self._extract_financial_metrics(text))
            
            # 5. Content quality assessment
            tasks.append(self._assess_content_quality(event))
            
            # Execute all enrichment tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            enrichment = ContentEnrichment()
            
            # Process results safely
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Enrichment task {i} failed", error=str(result))
                    continue
                
                if i == 0:  # Sentiment/emotion
                    self._merge_sentiment_emotion(enrichment, result)
                elif i == 1:  # Language/readability
                    self._merge_language_readability(enrichment, result)
                elif i == 2:  # Topics/keywords
                    self._merge_topics_keywords(enrichment, result)
                elif i == 3:  # Financial metrics
                    self._merge_financial_metrics(enrichment, result)
                elif i == 4:  # Content quality
                    self._merge_content_quality(enrichment, result)
            
            # Calculate basic metrics
            enrichment.word_count = len(text.split())
            enrichment.sentence_count = len(nltk.sent_tokenize(text))
            enrichment.paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
            
            logger.info("Content enrichment completed", 
                       event_id=event.event_id,
                       sentiment=enrichment.sentiment_score,
                       language=enrichment.language)
            
            return enrichment
            
        except Exception as e:
            logger.error("Content enrichment failed", 
                        error=str(e), 
                        event_id=event.event_id)
            
            # Return basic enrichment
            return ContentEnrichment(
                sentiment_score=0.0,
                sentiment_label="neutral",
                language="en",
                word_count=len(event.content.split()) if event.content else 0
            )
    
    async def _analyze_sentiment_emotion(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment and emotions"""
        results = {
            'sentiment_score': 0.0,
            'sentiment_label': 'neutral',
            'emotion_scores': {}
        }
        
        try:
            # Sentiment analysis
            if self.sentiment_pipeline:
                sentiment_results = self.sentiment_pipeline(text[:512])  # Limit text length
                
                if sentiment_results and len(sentiment_results[0]) > 0:
                    # Convert to normalized score (-1 to 1)
                    scores = {result['label'].lower(): result['score'] 
                             for result in sentiment_results[0]}
                    
                    # Calculate compound sentiment score
                    positive = scores.get('positive', 0)
                    negative = scores.get('negative', 0)
                    neutral = scores.get('neutral', 0)
                    
                    # Normalize to -1 to 1 scale
                    if positive > negative and positive > neutral:
                        results['sentiment_score'] = positive * 2 - 1  # 0 to 1
                        results['sentiment_label'] = 'positive'
                    elif negative > positive and negative > neutral:
                        results['sentiment_score'] = -(negative * 2 - 1)  # -1 to 0
                        results['sentiment_label'] = 'negative'
                    else:
                        results['sentiment_score'] = 0.0
                        results['sentiment_label'] = 'neutral'
            
            # Emotion analysis
            if self.emotion_pipeline:
                emotion_results = self.emotion_pipeline(text[:512])
                
                if emotion_results and len(emotion_results[0]) > 0:
                    results['emotion_scores'] = {
                        result['label'].lower(): result['score']
                        for result in emotion_results[0]
                    }
        
        except Exception as e:
            logger.error("Sentiment/emotion analysis failed", error=str(e))
        
        return results
    
    async def _analyze_language_readability(self, text: str) -> Dict[str, Any]:
        """Analyze language and readability"""
        results = {
            'language': 'en',
            'readability_score': 50.0,
            'complexity_score': 0.5
        }
        
        try:
            # Language detection
            try:
                detected_lang = detect(text)
                results['language'] = detected_lang
            except LangDetectError:
                results['language'] = 'en'  # Default to English
            
            # Readability analysis (only for English)
            if results['language'] == 'en':
                # Flesch Reading Ease Score (0-100, higher is easier)
                flesch_score = textstat.flesch_reading_ease(text)
                results['readability_score'] = max(0, min(100, flesch_score))
                
                # Complexity indicators
                avg_sentence_length = textstat.avg_sentence_length(text)
                syllable_count = textstat.syllable_count(text)
                word_count = len(text.split())
                
                # Normalize complexity to 0-1 scale
                complexity_factors = [
                    min(1.0, avg_sentence_length / 25),  # 25+ words = complex
                    min(1.0, (syllable_count / word_count) / 2),  # 2+ syllables per word = complex
                ]
                
                results['complexity_score'] = sum(complexity_factors) / len(complexity_factors)
        
        except Exception as e:
            logger.error("Language/readability analysis failed", error=str(e))
        
        return results
    
    async def _extract_topics_keywords(self, text: str) -> Dict[str, Any]:
        """Extract topics and keywords"""
        results = {
            'topics': [],
            'keywords': []
        }
        
        try:
            # Use LLM for topic extraction
            llm_topics = await self._llm_topic_extraction(text)
            results['topics'] = llm_topics
            
            # Basic keyword extraction using NLP
            if self.nlp:
                doc = self.nlp(text)
                
                # Extract meaningful keywords (nouns, adjectives, proper nouns)
                keywords = []
                for token in doc:
                    if (token.pos_ in ['NOUN', 'ADJ', 'PROPN'] and 
                        not token.is_stop and 
                        not token.is_punct and 
                        len(token.text) > 2):
                        keywords.append(token.lemma_.lower())
                
                # Remove duplicates and limit
                unique_keywords = list(dict.fromkeys(keywords))[:20]
                results['keywords'] = unique_keywords
        
        except Exception as e:
            logger.error("Topic/keyword extraction failed", error=str(e))
        
        return results
    
    async def _extract_financial_metrics(self, text: str) -> Dict[str, Any]:
        """Extract financial metrics and data"""
        results = {
            'financial_metrics': {},
            'price_targets': []
        }
        
        try:
            # Extract price targets and financial numbers
            price_patterns = [
                r'\$(\d+(?:\.\d{2})?)\s*(?:price\s*target|target|pt)',
                r'(?:price\s*target|target|pt)\s*(?:of\s*)?\$(\d+(?:\.\d{2})?)',
                r'(\d+(?:\.\d{2})?)\s*dollar\s*(?:price\s*target|target)',
            ]
            
            price_targets = []
            for pattern in price_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        price = float(match)
                        if 1 <= price <= 10000:  # Reasonable price range
                            price_targets.append({'target': price, 'currency': 'USD'})
                    except ValueError:
                        continue
            
            results['price_targets'] = price_targets[:5]  # Limit to 5 targets
            
            # Extract other financial metrics
            financial_terms = {
                'revenue': r'revenue\s*(?:of\s*)?\$?(\d+(?:\.\d+)?)\s*(?:billion|million|b|m)?',
                'profit': r'profit\s*(?:of\s*)?\$?(\d+(?:\.\d+)?)\s*(?:billion|million|b|m)?',
                'eps': r'eps\s*(?:of\s*)?\$?(\d+(?:\.\d+)?)',
                'dividend': r'dividend\s*(?:of\s*)?\$?(\d+(?:\.\d+)?)',
                'market_cap': r'market\s*cap\s*(?:of\s*)?\$?(\d+(?:\.\d+)?)\s*(?:billion|million|b|m)?'
            }
            
            for metric, pattern in financial_terms.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        value = float(matches[0])
                        results['financial_metrics'][metric] = value
                    except ValueError:
                        continue
        
        except Exception as e:
            logger.error("Financial metrics extraction failed", error=str(e))
        
        return results
    
    async def _assess_content_quality(self, event: NewsEvent) -> Dict[str, Any]:
        """Assess overall content quality"""
        results = {
            'content_quality_score': 0.7,
            'credibility_score': 0.7
        }
        
        try:
            text = f"{event.title} {event.content}"
            
            # Quality indicators
            quality_factors = []
            
            # Length factor (reasonable length content is usually higher quality)
            word_count = len(text.split())
            if 100 <= word_count <= 2000:
                quality_factors.append(0.8)
            elif 50 <= word_count < 100 or 2000 < word_count <= 5000:
                quality_factors.append(0.6)
            else:
                quality_factors.append(0.4)
            
            # Structure factor (paragraphs, sentences)
            sentences = nltk.sent_tokenize(text)
            paragraphs = [p for p in text.split('\n\n') if p.strip()]
            
            if len(sentences) >= 3 and len(paragraphs) >= 1:
                quality_factors.append(0.8)
            else:
                quality_factors.append(0.5)
            
            # Grammar and readability factor
            if hasattr(self, 'readability_score'):
                readability = getattr(self, 'readability_score', 50)
                if 30 <= readability <= 80:  # Good readability range
                    quality_factors.append(0.8)
                else:
                    quality_factors.append(0.6)
            else:
                quality_factors.append(0.7)  # Default
            
            # Professional language indicators
            professional_indicators = [
                'according to', 'reported', 'announced', 'stated', 'said',
                'company', 'business', 'market', 'industry', 'analysis'
            ]
            
            professional_count = sum(1 for indicator in professional_indicators 
                                   if indicator.lower() in text.lower())
            
            if professional_count >= 3:
                quality_factors.append(0.8)
            elif professional_count >= 1:
                quality_factors.append(0.6)
            else:
                quality_factors.append(0.4)
            
            # Calculate overall quality score
            results['content_quality_score'] = sum(quality_factors) / len(quality_factors)
            
            # Credibility assessment (based on source and content)
            credibility_factors = []
            
            # Source credibility (if available)
            # This would be enhanced with source reputation data
            credibility_factors.append(0.7)  # Default moderate credibility
            
            # Content credibility indicators
            if any(indicator in text.lower() for indicator in ['source:', 'according to', 'reported by']):
                credibility_factors.append(0.8)
            else:
                credibility_factors.append(0.6)
            
            # Specificity (dates, numbers, names)
            specificity_patterns = [
                r'\b\d{4}\b',  # Years
                r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # Dates
                r'\$\d+',  # Dollar amounts
                r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'  # Proper names
            ]
            
            specificity_count = sum(len(re.findall(pattern, text)) 
                                  for pattern in specificity_patterns)
            
            if specificity_count >= 5:
                credibility_factors.append(0.8)
            elif specificity_count >= 2:
                credibility_factors.append(0.7)
            else:
                credibility_factors.append(0.5)
            
            results['credibility_score'] = sum(credibility_factors) / len(credibility_factors)
        
        except Exception as e:
            logger.error("Content quality assessment failed", error=str(e))
        
        return results
    
    async def _llm_topic_extraction(self, text: str) -> List[Dict[str, float]]:
        """Use LLM to extract topics from content"""
        try:
            prompt = f"""
Analyze the following news content and identify the main topics. Focus on business, financial, and industry-specific topics.

Content: {text[:1500]}

Identify up to 5 main topics and rate their relevance (0.0 to 1.0). Format your response as:

TOPIC: topic_name - RELEVANCE: 0.8
TOPIC: topic_name - RELEVANCE: 0.7

Focus on:
- Industry sectors (technology, healthcare, finance, etc.)
- Business themes (earnings, mergers, regulation, etc.)
- Market segments (consumer, enterprise, etc.)
- Geographic regions if relevant
"""
            
            response = await self._call_mac_studio_llm(prompt)
            topics = self._parse_topic_response(response)
            
            return topics[:5]  # Limit to 5 topics
            
        except Exception as e:
            logger.error("LLM topic extraction failed", error=str(e))
            return []
    
    async def _call_mac_studio_llm(self, prompt: str) -> str:
        """Call Mac Studio LLM for analysis"""
        try:
            payload = {
                "model": "qwen-3-72b:latest",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing news content and extracting relevant business and financial topics."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
            
            async with self.http_client as client:
                response = await client.post(
                    f"{self.mac_studio_endpoint}/v1/chat/completions",
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data['choices'][0]['message']['content']
                else:
                    return "LLM analysis unavailable"
                    
        except Exception as e:
            logger.error("LLM call failed", error=str(e))
            return f"LLM analysis failed: {str(e)}"
    
    def _parse_topic_response(self, response: str) -> List[Dict[str, float]]:
        """Parse LLM topic extraction response"""
        topics = []
        
        try:
            lines = response.strip().split('\n')
            
            for line in lines:
                if 'TOPIC:' in line and 'RELEVANCE:' in line:
                    try:
                        # Extract topic and relevance
                        topic_match = re.search(r'TOPIC:\s*([^-]+)', line)
                        relevance_match = re.search(r'RELEVANCE:\s*([0-9.]+)', line)
                        
                        if topic_match and relevance_match:
                            topic_name = topic_match.group(1).strip()
                            relevance = float(relevance_match.group(1))
                            
                            topics.append({topic_name: max(0.0, min(1.0, relevance))})
                        
                    except (ValueError, AttributeError):
                        continue
        
        except Exception as e:
            logger.error("Failed to parse topic response", error=str(e))
        
        return topics
    
    # Helper methods to merge enrichment results
    
    def _merge_sentiment_emotion(self, enrichment: ContentEnrichment, result: Dict[str, Any]):
        """Merge sentiment and emotion results"""
        enrichment.sentiment_score = result.get('sentiment_score', 0.0)
        enrichment.sentiment_label = result.get('sentiment_label', 'neutral')
        enrichment.emotion_scores = result.get('emotion_scores', {})
    
    def _merge_language_readability(self, enrichment: ContentEnrichment, result: Dict[str, Any]):
        """Merge language and readability results"""
        enrichment.language = result.get('language', 'en')
        enrichment.readability_score = result.get('readability_score', 50.0)
        enrichment.complexity_score = result.get('complexity_score', 0.5)
    
    def _merge_topics_keywords(self, enrichment: ContentEnrichment, result: Dict[str, Any]):
        """Merge topics and keywords results"""
        enrichment.topics = result.get('topics', [])
        enrichment.keywords = result.get('keywords', [])
    
    def _merge_financial_metrics(self, enrichment: ContentEnrichment, result: Dict[str, Any]):
        """Merge financial metrics results"""
        enrichment.financial_metrics = result.get('financial_metrics', {})
        enrichment.price_targets = result.get('price_targets', [])
    
    def _merge_content_quality(self, enrichment: ContentEnrichment, result: Dict[str, Any]):
        """Merge content quality results"""
        enrichment.content_quality_score = result.get('content_quality_score', 0.7)
        enrichment.credibility_score = result.get('credibility_score', 0.7)
    
    async def close(self):
        """Close HTTP client and cleanup resources"""
        await self.http_client.aclose() 