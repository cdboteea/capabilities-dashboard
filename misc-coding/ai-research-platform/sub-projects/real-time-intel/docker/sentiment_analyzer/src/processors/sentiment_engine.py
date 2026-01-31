from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Dict, List, Optional

import numpy as np
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from ..models.sentiment_models import SentimentResult, SentimentScore, EntitySentiment
from ..config import settings
from .financial_lexicon import (
    get_financial_sentiment_weight,
    detect_emotions,
    extract_financial_entities
)


class SentimentEngine:
    """Enhanced sentiment analysis engine with financial context and emotion detection."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._sentiment_pipe = None
        self._vader_analyzer = None

    async def _load(self):
        """Load sentiment analysis models."""
        async with self._lock:
            if self._sentiment_pipe is None:
                # Load FinBERT model for financial sentiment
                model = AutoModelForSequenceClassification.from_pretrained(settings.sentiment_model_name)
                tokenizer = AutoTokenizer.from_pretrained(settings.sentiment_model_name)
                
                self._sentiment_pipe = pipeline(
                    "sentiment-analysis",
                    model=model,
                    tokenizer=tokenizer,
                    return_all_scores=True,
                    device=0 if hasattr(model, "to") else -1,
                )
                
                # Load VADER for emotion detection
                self._vader_analyzer = SentimentIntensityAnalyzer()

    async def analyze(self, text: str, entities: Optional[List[str]] = None, sector: Optional[str] = None) -> SentimentResult:
        """Perform comprehensive sentiment analysis with financial context."""
        if self._sentiment_pipe is None:
            await self._load()

        # 1. Base sentiment analysis using FinBERT
        overall_sentiment = await self._analyze_base_sentiment(text)
        
        # 2. Financial context adjustment
        financial_sentiment = await self._analyze_financial_sentiment(text, sector)
        
        # 3. Emotion detection
        emotions = await self._analyze_emotions(text)
        
        # 4. Entity-specific sentiment
        entity_sentiments = []
        if entities:
            entity_sentiments = await self._analyze_entity_sentiment(text, entities)

        return SentimentResult(
            overall=overall_sentiment,
            financial=financial_sentiment,
            emotions=emotions,
            entities=entity_sentiments if entity_sentiments else None
        )

    async def _analyze_base_sentiment(self, text: str) -> SentimentScore:
        """Analyze base sentiment using FinBERT."""
        # Truncate text to model limits
        text_truncated = text[:512]
        
        scores = await asyncio.to_thread(self._sentiment_pipe, text_truncated)
        class_scores = scores[0]
        
        # FinBERT typically returns [negative, neutral, positive]
        neg_score = next(s["score"] for s in class_scores if s["label"] == "negative")
        pos_score = next(s["score"] for s in class_scores if s["label"] == "positive")
        
        # Calculate sentiment score (-1 to 1)
        sentiment_score = pos_score - neg_score
        
        # Confidence is the maximum class probability
        confidence = max(s["score"] for s in class_scores)
        
        return SentimentScore(score=sentiment_score, confidence=confidence)

    async def _analyze_financial_sentiment(self, text: str, sector: Optional[str] = None) -> SentimentScore:
        """Analyze sentiment with financial context weighting."""
        # Get base sentiment
        base_sentiment = await self._analyze_base_sentiment(text)
        
        # Apply financial lexicon weighting
        financial_weight = get_financial_sentiment_weight(text, sector)
        
        # Adjust sentiment score based on financial context
        adjusted_score = base_sentiment.score * financial_weight
        
        # Clamp to [-1, 1] range
        adjusted_score = max(-1.0, min(1.0, adjusted_score))
        
        # Confidence remains the same for now
        return SentimentScore(score=adjusted_score, confidence=base_sentiment.confidence)

    async def _analyze_emotions(self, text: str) -> Dict[str, SentimentScore]:
        """Detect emotions using VADER and financial lexicon."""
        emotions = {}
        
        # Use VADER for general emotional analysis
        vader_scores = await asyncio.to_thread(self._vader_analyzer.polarity_scores, text)
        
        # Add VADER-based emotions
        if vader_scores['compound'] > 0.1:
            emotions['positive'] = SentimentScore(score=vader_scores['pos'], confidence=0.8)
        if vader_scores['compound'] < -0.1:
            emotions['negative'] = SentimentScore(score=-vader_scores['neg'], confidence=0.8)
        
        # Add financial-specific emotions
        financial_emotions = detect_emotions(text)
        for emotion, score in financial_emotions.items():
            emotions[emotion] = SentimentScore(score=score, confidence=0.7)
        
        return emotions

    async def _analyze_entity_sentiment(self, text: str, entities: List[str]) -> List[EntitySentiment]:
        """Analyze sentiment for specific entities mentioned in text."""
        entity_sentiments = []
        
        for entity in entities:
            # Find sentences containing the entity
            sentences = self._extract_entity_context(text, entity)
            
            if sentences:
                # Analyze sentiment of entity context
                context_text = " ".join(sentences)
                entity_sentiment = await self._analyze_base_sentiment(context_text)
                
                entity_sentiments.append(
                    EntitySentiment(entity=entity, sentiment=entity_sentiment)
                )
        
        return entity_sentiments

    def _extract_entity_context(self, text: str, entity: str, window_size: int = 2) -> List[str]:
        """Extract sentences containing the entity with context window."""
        import re
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        entity_sentences = []
        
        for i, sentence in enumerate(sentences):
            if entity.lower() in sentence.lower():
                # Include context window
                start_idx = max(0, i - window_size)
                end_idx = min(len(sentences), i + window_size + 1)
                context = sentences[start_idx:end_idx]
                entity_sentences.extend(context)
        
        return list(set(entity_sentences))  # Remove duplicates

    async def analyze_batch(self, texts: List[str], entities: Optional[List[str]] = None, sector: Optional[str] = None) -> List[SentimentResult]:
        """Analyze multiple texts in batch for efficiency."""
        # Process in batches to avoid overwhelming the model
        batch_size = min(settings.max_batch_size, len(texts))
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_tasks = [self.analyze(text, entities, sector) for text in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)
        
        return results


@lru_cache
def get_engine() -> SentimentEngine:
    """Get cached sentiment engine instance."""
    return SentimentEngine() 