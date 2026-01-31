"""
Topic Manager Service for Twin-Report KB

Handles topic extraction, classification, and management for the knowledge base.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import asyncio
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TopicExtractionRequest(BaseModel):
    """Request model for topic extraction."""
    text: str = Field(..., description="Text to extract topics from")
    max_topics: int = Field(default=10, description="Maximum number of topics to extract")
    min_confidence: float = Field(default=0.1, description="Minimum confidence threshold")


class TopicResponse(BaseModel):
    """Response model for topic extraction."""
    topics: List[Dict[str, Any]] = Field(..., description="Extracted topics")
    confidence_scores: List[float] = Field(..., description="Confidence scores")
    processing_time: float = Field(..., description="Processing time in seconds")


class TopicClassificationRequest(BaseModel):
    """Request model for topic classification."""
    text: str = Field(..., description="Text to classify")
    existing_topics: List[str] = Field(default_factory=list, description="Existing topic categories")


class TopicClassificationResponse(BaseModel):
    """Response model for topic classification."""
    primary_topic: str = Field(..., description="Primary topic classification")
    secondary_topics: List[str] = Field(..., description="Secondary topic classifications")
    confidence: float = Field(..., description="Classification confidence")


class TopicManagerService:
    """Core topic management service."""
    
    def __init__(self):
        self.topic_database = {}
        self.classification_model = None
        self.extraction_model = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize topic models."""
        logger.info("Initializing topic models...")
        # Placeholder for model initialization
        # In production, this would load actual ML models
        self.topic_database = {
            "technology": ["AI", "machine learning", "deep learning", "neural networks"],
            "finance": ["investment", "trading", "market analysis", "portfolio"],
            "research": ["methodology", "analysis", "findings", "conclusions"],
            "business": ["strategy", "operations", "management", "growth"]
        }
        logger.info("Topic models initialized successfully")
    
    async def extract_topics(self, text: str, max_topics: int = 10, min_confidence: float = 0.1) -> Dict[str, Any]:
        """Extract topics from text."""
        start_time = datetime.now()
        
        try:
            # Simulate topic extraction
            # In production, this would use actual NLP models
            topics = []
            confidence_scores = []
            
            # Simple keyword-based topic extraction for demo
            text_lower = text.lower()
            for category, keywords in self.topic_database.items():
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        confidence = min(0.9, text_lower.count(keyword.lower()) * 0.2)
                        if confidence >= min_confidence:
                            topics.append({
                                "topic": keyword,
                                "category": category,
                                "mentions": text_lower.count(keyword.lower())
                            })
                            confidence_scores.append(confidence)
            
            # Sort by confidence and limit results
            combined = list(zip(topics, confidence_scores))
            combined.sort(key=lambda x: x[1], reverse=True)
            topics = [t for t, _ in combined[:max_topics]]
            confidence_scores = [c for _, c in combined[:max_topics]]
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "topics": topics,
                "confidence_scores": confidence_scores,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error extracting topics: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Topic extraction failed: {str(e)}")
    
    async def classify_topic(self, text: str, existing_topics: List[str] = None) -> Dict[str, Any]:
        """Classify text into topic categories."""
        try:
            if existing_topics is None:
                existing_topics = list(self.topic_database.keys())
            
            # Simple classification based on keyword matching
            text_lower = text.lower()
            category_scores = {}
            
            for category in existing_topics:
                if category in self.topic_database:
                    keywords = self.topic_database[category]
                    score = sum(1 for keyword in keywords if keyword.lower() in text_lower)
                    if score > 0:
                        category_scores[category] = score / len(keywords)
            
            if not category_scores:
                return {
                    "primary_topic": "other",
                    "secondary_topics": [],
                    "confidence": 0.1
                }
            
            # Sort by score
            sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
            
            primary_topic = sorted_categories[0][0]
            secondary_topics = [cat for cat, score in sorted_categories[1:3]]
            confidence = sorted_categories[0][1]
            
            return {
                "primary_topic": primary_topic,
                "secondary_topics": secondary_topics,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error classifying topic: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Topic classification failed: {str(e)}")


# Initialize FastAPI app
app = FastAPI(
    title="Topic Manager Service",
    description="Topic extraction and classification for Twin-Report KB",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
topic_service = TopicManagerService()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "topic_manager",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/extract-topics", response_model=TopicResponse)
async def extract_topics(request: TopicExtractionRequest):
    """Extract topics from text."""
    logger.info(f"Extracting topics from text (length: {len(request.text)})")
    
    result = await topic_service.extract_topics(
        text=request.text,
        max_topics=request.max_topics,
        min_confidence=request.min_confidence
    )
    
    return TopicResponse(**result)


@app.post("/classify-topic", response_model=TopicClassificationResponse)
async def classify_topic(request: TopicClassificationRequest):
    """Classify text into topic categories."""
    logger.info(f"Classifying text into topics (length: {len(request.text)})")
    
    result = await topic_service.classify_topic(
        text=request.text,
        existing_topics=request.existing_topics
    )
    
    return TopicClassificationResponse(**result)


@app.get("/topics")
async def get_available_topics():
    """Get available topic categories."""
    return {
        "categories": list(topic_service.topic_database.keys()),
        "total_keywords": sum(len(keywords) for keywords in topic_service.topic_database.values())
    }


@app.get("/topics/{category}")
async def get_topic_keywords(category: str):
    """Get keywords for a specific topic category."""
    if category not in topic_service.topic_database:
        raise HTTPException(status_code=404, detail=f"Topic category '{category}' not found")
    
    return {
        "category": category,
        "keywords": topic_service.topic_database[category]
    }


if __name__ == "__main__":
    port = int(os.getenv("TOPIC_MANAGER_PORT", 8101))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    ) 