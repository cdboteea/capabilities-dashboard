"""
Twin-Report KB Diff Worker
Compares twin reports to identify gaps, overlaps, and contradictions
"""

import os
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import asyncpg
import httpx
import structlog

from src.diff_analyzer import DiffAnalyzer
from src.gap_detector import GapDetector
from src.quality_scorer import QualityScorer
from src.database import DatabaseManager

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Twin-Report Diff Worker",
    description="Compares twin reports to identify gaps, overlaps, and contradictions",
    version="1.0.0"
)

# Pydantic models
class ArticleData(BaseModel):
    id: str
    topic_id: str
    model_origin: str
    title: str
    body_md: str
    word_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DiffRequest(BaseModel):
    twin_set_id: str
    article_1_id: str
    article_2_id: str
    analysis_type: str = Field(default="comprehensive", description="Types: quick, comprehensive, detailed")

class DiffResult(BaseModel):
    id: str
    twin_set_id: str
    article_1_id: str
    article_2_id: str
    diff_summary: str
    gaps: List[str]
    overlaps: List[str]
    contradictions: List[str]
    confidence_score: float
    analysis_metadata: Dict[str, Any]

class GapAnalysisRequest(BaseModel):
    twin_set_id: str
    articles: List[str]  # Article IDs
    analysis_depth: str = Field(default="standard", description="Depths: quick, standard, deep")

# Global components
db_manager: Optional[DatabaseManager] = None
diff_analyzer: Optional[DiffAnalyzer] = None
gap_detector: Optional[GapDetector] = None
quality_scorer: Optional[QualityScorer] = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db_manager, diff_analyzer, gap_detector, quality_scorer
    
    logger.info("Starting Twin-Report Diff Worker...")
    
    # Initialize database connection
    postgres_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL", "postgresql://twin_report:secure_password@postgres:5432/twin_report_kb")
    db_manager = DatabaseManager(postgres_url)
    await db_manager.connect()
    
    # Initialize analysis components
    mac_studio_endpoint = os.getenv("MAC_STUDIO_ENDPOINT", "https://matiass-mac-studio.tail174e9b.ts.net/v1")
    diff_model = os.getenv("DIFF_MODEL", "deepseek-r1")
    
    diff_analyzer = DiffAnalyzer(mac_studio_endpoint, diff_model)
    gap_detector = GapDetector(mac_studio_endpoint, diff_model)
    quality_scorer = QualityScorer(mac_studio_endpoint, diff_model)
    
    logger.info("Diff Worker started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global db_manager
    
    logger.info("Shutting down Diff Worker...")
    
    if db_manager:
        await db_manager.disconnect()
    
    logger.info("Diff Worker shutdown complete")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "twin-report-diff-worker",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": "connected" if db_manager and db_manager.is_connected() else "disconnected",
            "diff_analyzer": "initialized" if diff_analyzer else "not_initialized",
            "gap_detector": "initialized" if gap_detector else "not_initialized",
            "quality_scorer": "initialized" if quality_scorer else "not_initialized"
        }
    }

@app.post("/analyze-diff", response_model=DiffResult)
async def analyze_diff(
    diff_request: DiffRequest,
    background_tasks: BackgroundTasks
):
    """
    Analyze differences between twin reports
    """
    logger.info("Starting diff analysis", twin_set_id=diff_request.twin_set_id)
    
    try:
        # Fetch articles from database
        article_1 = await db_manager.get_article(diff_request.article_1_id)
        article_2 = await db_manager.get_article(diff_request.article_2_id)
        
        if not article_1 or not article_2:
            raise HTTPException(status_code=404, detail="One or both articles not found")
        
        # Perform diff analysis
        diff_result = await diff_analyzer.analyze_differences(
            article_1, article_2, diff_request.analysis_type
        )
        
        # Store results in database
        diff_id = str(uuid4())
        await db_manager.store_diff_result(diff_id, diff_result)
        
        # Schedule background quality scoring
        background_tasks.add_task(
            score_diff_quality,
            diff_id,
            diff_result
        )
        
        logger.info("Diff analysis completed", diff_id=diff_id)
        
        return DiffResult(
            id=diff_id,
            twin_set_id=diff_request.twin_set_id,
            article_1_id=diff_request.article_1_id,
            article_2_id=diff_request.article_2_id,
            diff_summary=diff_result["summary"],
            gaps=diff_result["gaps"],
            overlaps=diff_result["overlaps"],
            contradictions=diff_result["contradictions"],
            confidence_score=diff_result["confidence_score"],
            analysis_metadata=diff_result["metadata"]
        )
        
    except Exception as e:
        logger.error("Diff analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Diff analysis failed: {str(e)}")

@app.post("/analyze-gaps")
async def analyze_gaps(gap_request: GapAnalysisRequest):
    """
    Analyze gaps across multiple articles in a twin set
    """
    logger.info("Starting gap analysis", twin_set_id=gap_request.twin_set_id)
    
    try:
        # Fetch all articles
        articles = []
        for article_id in gap_request.articles:
            article = await db_manager.get_article(article_id)
            if article:
                articles.append(article)
        
        if len(articles) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 articles for gap analysis")
        
        # Perform gap analysis
        gap_result = await gap_detector.detect_gaps(
            articles, gap_request.analysis_depth
        )
        
        # Store gap scan results
        gap_scan_id = str(uuid4())
        await db_manager.store_gap_scan_result(gap_scan_id, gap_result)
        
        logger.info("Gap analysis completed", gap_scan_id=gap_scan_id)
        
        return {
            "gap_scan_id": gap_scan_id,
            "twin_set_id": gap_request.twin_set_id,
            "identified_gaps": gap_result["gaps"],
            "coverage_analysis": gap_result["coverage"],
            "recommendations": gap_result["recommendations"],
            "priority_scores": gap_result["priorities"]
        }
        
    except Exception as e:
        logger.error("Gap analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Gap analysis failed: {str(e)}")

@app.get("/twin-set/{twin_set_id}/diffs")
async def get_twin_set_diffs(twin_set_id: str):
    """
    Get all diff analyses for a twin set
    """
    try:
        diffs = await db_manager.get_twin_set_diffs(twin_set_id)
        return {
            "twin_set_id": twin_set_id,
            "diff_analyses": diffs,
            "total_count": len(diffs)
        }
    except Exception as e:
        logger.error("Failed to fetch twin set diffs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch diffs: {str(e)}")

@app.get("/diff/{diff_id}")
async def get_diff_result(diff_id: str):
    """
    Get specific diff analysis result
    """
    try:
        diff_result = await db_manager.get_diff_result(diff_id)
        if not diff_result:
            raise HTTPException(status_code=404, detail="Diff result not found")
        
        return diff_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch diff result", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch diff: {str(e)}")

async def score_diff_quality(diff_id: str, diff_result: Dict[str, Any]):
    """
    Background task to score the quality of a diff analysis
    """
    try:
        quality_score = await quality_scorer.score_diff_quality(diff_result)
        await db_manager.update_diff_quality_score(diff_id, quality_score)
        logger.info("Diff quality scoring completed", diff_id=diff_id, score=quality_score)
    except Exception as e:
        logger.error("Diff quality scoring failed", diff_id=diff_id, error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 