#!/usr/bin/env python3
"""
Quality Controller - Twin-Report KB
Fact-checking, citation verification, and quality assessment service
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog
import uvicorn

from src.database import DatabaseManager
from src.fact_checker import FactChecker
from src.citation_verifier import CitationVerifier
from src.quality_assessor import QualityAssessor
from src.source_evaluator import SourceEvaluator
from src.config_loader import get_config_loader

# Configure structured logging
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

# Pydantic models
class QualityCheckRequest(BaseModel):
    content: str = Field(..., description="Content to analyze")
    sources: List[Dict[str, Any]] = Field(default=[], description="Source references")
    analysis_depth: str = Field(default="standard", description="Analysis depth: quick, standard, deep")
    check_types: List[str] = Field(default=["all"], description="Types of checks to perform")

class QualityCheckResponse(BaseModel):
    overall_score: float = Field(..., description="Overall quality score (0-1)")
    component_scores: Dict[str, float] = Field(..., description="Individual component scores")
    fact_checking: Optional[Dict[str, Any]] = None
    citation_verification: Optional[Dict[str, Any]] = None
    quality_assessment: Optional[Dict[str, Any]] = None
    source_evaluation: Optional[Dict[str, Any]] = None
    recommendations: List[str] = Field(..., description="Improvement recommendations")
    metadata: Dict[str, Any] = Field(..., description="Analysis metadata")

# Global instances
db_manager: Optional[DatabaseManager] = None
fact_checker: Optional[FactChecker] = None
citation_verifier: Optional[CitationVerifier] = None
quality_assessor: Optional[QualityAssessor] = None
source_evaluator: Optional[SourceEvaluator] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_manager, fact_checker, citation_verifier, quality_assessor, source_evaluator
    
    logger.info("Starting Quality Controller service")
    
    # Initialize database
    postgres_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL", "postgresql://twin_report:secure_password@postgres:5432/twin_report_kb")
    db_manager = DatabaseManager(postgres_url)
    await db_manager.initialize()
    
    # Initialize AI components
    mac_studio_endpoint = os.getenv("MAC_STUDIO_ENDPOINT", "http://localhost:8080")
    model_name = os.getenv("MODEL_NAME", "deepseek-r1")
    
    fact_checker = FactChecker(mac_studio_endpoint, model_name)
    citation_verifier = CitationVerifier(mac_studio_endpoint, model_name)
    quality_assessor = QualityAssessor(mac_studio_endpoint, model_name)
    source_evaluator = SourceEvaluator(mac_studio_endpoint, model_name)
    
    logger.info("Quality Controller service initialized")
    
    yield
    
    logger.info("Shutting down Quality Controller service")
    if db_manager:
        await db_manager.close()

# Create FastAPI app
app = FastAPI(
    title="Quality Controller",
    description="Twin-Report KB Quality Control Service",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "quality_controller"}

@app.post("/quality-check", response_model=QualityCheckResponse)
async def quality_check(request: QualityCheckRequest, background_tasks: BackgroundTasks):
    """Perform comprehensive quality check on content"""
    
    logger.info("Quality check requested", 
               content_length=len(request.content),
               source_count=len(request.sources),
               analysis_depth=request.analysis_depth)
    
    try:
        # Determine which checks to perform
        check_types = request.check_types
        if "all" in check_types:
            check_types = ["fact_checking", "citation_verification", "quality_assessment", "source_evaluation"]
        
        # Initialize results
        results = {
            "component_scores": {},
            "recommendations": [],
            "metadata": {
                "analysis_depth": request.analysis_depth,
                "timestamp": datetime.now().isoformat(),
                "checks_performed": check_types
            }
        }
        
        # Perform fact checking
        if "fact_checking" in check_types:
            fact_check_result = await fact_checker.check_facts(request.content, request.analysis_depth)
            results["fact_checking"] = fact_check_result
            results["component_scores"]["fact_checking"] = fact_check_result["overall_score"]
            results["recommendations"].extend(fact_check_result.get("recommendations", []))
        
        # Perform citation verification
        if "citation_verification" in check_types:
            citation_result = await citation_verifier.verify_citations(
                request.content, request.sources, request.analysis_depth
            )
            results["citation_verification"] = citation_result
            results["component_scores"]["citation_verification"] = citation_result["overall_score"]
            results["recommendations"].extend(citation_result.get("recommendations", []))
        
        # Perform quality assessment
        if "quality_assessment" in check_types:
            quality_result = await quality_assessor.assess_quality(request.content, request.analysis_depth)
            results["quality_assessment"] = quality_result
            results["component_scores"]["quality_assessment"] = quality_result["overall_score"]
            results["recommendations"].extend(quality_result.get("recommendations", []))
        
        # Perform source evaluation
        if "source_evaluation" in check_types and request.sources:
            source_result = await source_evaluator.evaluate_sources(request.sources, request.analysis_depth)
            results["source_evaluation"] = source_result
            results["component_scores"]["source_evaluation"] = source_result["overall_score"]
            results["recommendations"].extend(source_result.get("recommendations", []))
        
        # Calculate overall score
        config_loader = get_config_loader()
        weights = config_loader.get_quality_controller_weights()
        
        overall_score = 0.0
        total_weight = 0.0
        
        for component, score in results["component_scores"].items():
            weight = weights.get(component, 0.25)
            overall_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            overall_score = overall_score / total_weight
        else:
            overall_score = 0.5
        
        results["overall_score"] = overall_score
        
        # Store results in database
        background_tasks.add_task(store_quality_check_results, results, request)
        
        logger.info("Quality check completed", overall_score=overall_score)
        
        return QualityCheckResponse(**results)
        
    except Exception as e:
        logger.error("Quality check failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Quality check failed: {str(e)}")

@app.get("/quality-check/{check_id}")
async def get_quality_check(check_id: str):
    """Get quality check results by ID"""
    
    try:
        results = await db_manager.get_quality_check_results(check_id)
        if not results:
            raise HTTPException(status_code=404, detail="Quality check not found")
        
        return results
        
    except Exception as e:
        logger.error("Failed to retrieve quality check", check_id=check_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve quality check: {str(e)}")

@app.get("/config")
async def get_configuration():
    """Get current configuration"""
    config_loader = get_config_loader()
    return {
        "weights": config_loader.get_quality_controller_weights(),
        "thresholds": config_loader.get_quality_thresholds(),
        "fact_checking": config_loader.get_fact_checking_config(),
        "citation_verification": config_loader.get_citation_verification_config(),
        "quality_assessment": config_loader.get_quality_assessment_config(),
        "source_evaluation": config_loader.get_source_evaluation_config()
    }

@app.post("/config/reload")
async def reload_configuration():
    """Reload configuration from file"""
    try:
        config_loader = get_config_loader()
        config_loader.reload_config()
        logger.info("Configuration reloaded successfully")
        return {"status": "success", "message": "Configuration reloaded"}
    except Exception as e:
        logger.error("Failed to reload configuration", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to reload configuration: {str(e)}")

async def store_quality_check_results(results: Dict[str, Any], request: QualityCheckRequest):
    """Store quality check results in database"""
    try:
        await db_manager.store_quality_check_results(results, request.dict())
        logger.info("Quality check results stored successfully")
    except Exception as e:
        logger.error("Failed to store quality check results", error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # Use structlog configuration
    )

logger = structlog.get_logger(__name__)

# Global instances
db_manager = None
fact_checker = None
citation_verifier = None
quality_assessor = None
source_evaluator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_manager, fact_checker, citation_verifier, quality_assessor, source_evaluator
    
    logger.info("Starting Quality Controller service")
    
    # Initialize database
    postgres_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL", "postgresql://twin_report:secure_password@postgres:5432/twin_report_kb")
    mac_studio_endpoint = os.getenv("MAC_STUDIO_ENDPOINT", "https://matiass-mac-studio.tail174e9b.ts.net/v1")
    model_name = os.getenv("QUALITY_MODEL", "deepseek-r1")
    
    db_manager = DatabaseManager(postgres_url)
    await db_manager.initialize()
    
    # Initialize quality control components
    fact_checker = FactChecker(mac_studio_endpoint, model_name)
    citation_verifier = CitationVerifier(mac_studio_endpoint, model_name)
    quality_assessor = QualityAssessor(mac_studio_endpoint, model_name)
    source_evaluator = SourceEvaluator(mac_studio_endpoint, model_name)
    
    logger.info("Quality Controller service initialized successfully")
    
    yield
    
    # Cleanup
    if db_manager:
        await db_manager.close()
    logger.info("Quality Controller service stopped")

# Create FastAPI app
app = FastAPI(
    title="Twin-Report KB Quality Controller",
    description="Fact-checking, citation verification, and quality assessment service",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class QualityCheckRequest(BaseModel):
    """Request model for quality check"""
    report_id: str = Field(..., description="Report ID to check")
    content: str = Field(..., description="Report content to analyze")
    sources: List[Dict[str, Any]] = Field(default=[], description="Source references")
    check_types: List[str] = Field(
        default=["fact_check", "citation_verify", "quality_assess", "source_evaluate"],
        description="Types of checks to perform"
    )
    analysis_depth: str = Field(default="standard", description="Analysis depth: quick, standard, deep")

class BatchQualityCheckRequest(BaseModel):
    """Request model for batch quality check"""
    reports: List[QualityCheckRequest] = Field(..., description="Reports to check")
    priority: str = Field(default="normal", description="Processing priority: low, normal, high")

class QualityCheckResponse(BaseModel):
    """Response model for quality check"""
    report_id: str
    overall_score: float
    quality_level: str
    fact_check_results: Dict[str, Any]
    citation_verification: Dict[str, Any]
    quality_assessment: Dict[str, Any]
    source_evaluation: Dict[str, Any]
    recommendations: List[str]
    processing_time: float
    metadata: Dict[str, Any]

class QualityMetrics(BaseModel):
    """Quality metrics response"""
    total_reports_processed: int
    average_quality_score: float
    quality_distribution: Dict[str, int]
    common_issues: List[Dict[str, Any]]
    processing_stats: Dict[str, Any]

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "quality_controller",
        "version": "1.0.0",
        "components": {
            "database": "connected" if db_manager else "disconnected",
            "fact_checker": "ready" if fact_checker else "not_ready",
            "citation_verifier": "ready" if citation_verifier else "not_ready",
            "quality_assessor": "ready" if quality_assessor else "not_ready",
            "source_evaluator": "ready" if source_evaluator else "not_ready"
        }
    }

@app.post("/quality-check", response_model=QualityCheckResponse)
async def perform_quality_check(request: QualityCheckRequest):
    """Perform comprehensive quality check on a report"""
    logger.info("Starting quality check", report_id=request.report_id, 
                analysis_depth=request.analysis_depth)
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Initialize results
        results = {
            "fact_check_results": {},
            "citation_verification": {},
            "quality_assessment": {},
            "source_evaluation": {}
        }
        
        # Perform requested checks
        if "fact_check" in request.check_types:
            results["fact_check_results"] = await fact_checker.check_facts(
                request.content, request.analysis_depth
            )
        
        if "citation_verify" in request.check_types:
            results["citation_verification"] = await citation_verifier.verify_citations(
                request.content, request.sources, request.analysis_depth
            )
        
        if "quality_assess" in request.check_types:
            results["quality_assessment"] = await quality_assessor.assess_quality(
                request.content, request.analysis_depth
            )
        
        if "source_evaluate" in request.check_types:
            results["source_evaluation"] = await source_evaluator.evaluate_sources(
                request.sources, request.analysis_depth
            )
        
        # Calculate overall score and quality level
        overall_score = _calculate_overall_score(results)
        quality_level = _determine_quality_level(overall_score)
        
        # Generate recommendations
        recommendations = _generate_recommendations(results)
        
        # Store results in database
        await db_manager.store_quality_check_result(
            report_id=request.report_id,
            results=results,
            overall_score=overall_score,
            quality_level=quality_level
        )
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        logger.info("Quality check completed", 
                   report_id=request.report_id,
                   overall_score=overall_score,
                   quality_level=quality_level,
                   processing_time=processing_time)
        
        return QualityCheckResponse(
            report_id=request.report_id,
            overall_score=overall_score,
            quality_level=quality_level,
            fact_check_results=results["fact_check_results"],
            citation_verification=results["citation_verification"],
            quality_assessment=results["quality_assessment"],
            source_evaluation=results["source_evaluation"],
            recommendations=recommendations,
            processing_time=processing_time,
            metadata={
                "analysis_depth": request.analysis_depth,
                "check_types": request.check_types,
                "timestamp": asyncio.get_event_loop().time()
            }
        )
        
    except Exception as e:
        logger.error("Quality check failed", 
                    report_id=request.report_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Quality check failed: {str(e)}")

@app.post("/batch-quality-check")
async def perform_batch_quality_check(
    request: BatchQualityCheckRequest,
    background_tasks: BackgroundTasks
):
    """Perform batch quality check on multiple reports"""
    logger.info("Starting batch quality check", 
                report_count=len(request.reports),
                priority=request.priority)
    
    try:
        # Process reports based on priority
        if request.priority == "high":
            # Process immediately
            results = []
            for report_request in request.reports:
                result = await perform_quality_check(report_request)
                results.append(result)
            return {"results": results, "status": "completed"}
        else:
            # Process in background
            background_tasks.add_task(
                _process_batch_quality_check, 
                request.reports, 
                request.priority
            )
            return {
                "status": "queued",
                "message": f"Batch quality check queued for {len(request.reports)} reports"
            }
            
    except Exception as e:
        logger.error("Batch quality check failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch quality check failed: {str(e)}")

@app.get("/quality-metrics", response_model=QualityMetrics)
async def get_quality_metrics():
    """Get quality metrics and statistics"""
    try:
        metrics = await db_manager.get_quality_metrics()
        return QualityMetrics(**metrics)
        
    except Exception as e:
        logger.error("Failed to get quality metrics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get quality metrics: {str(e)}")

@app.get("/reports/{report_id}/quality")
async def get_report_quality(report_id: str):
    """Get quality check results for a specific report"""
    try:
        results = await db_manager.get_quality_check_result(report_id)
        if not results:
            raise HTTPException(status_code=404, detail="Quality check results not found")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get report quality", report_id=report_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get report quality: {str(e)}")

@app.post("/recheck/{report_id}")
async def recheck_report_quality(report_id: str):
    """Recheck quality for a specific report"""
    try:
        # Get original report content
        report_data = await db_manager.get_report_content(report_id)
        if not report_data:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Create quality check request
        request = QualityCheckRequest(
            report_id=report_id,
            content=report_data["content"],
            sources=report_data.get("sources", []),
            analysis_depth="standard"
        )
        
        # Perform quality check
        result = await perform_quality_check(request)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to recheck report quality", report_id=report_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to recheck report quality: {str(e)}")

# Helper functions

def _calculate_overall_score(results: Dict[str, Any]) -> float:
    """Calculate overall quality score from component results"""
    config_loader = get_config_loader()
    weights = config_loader.get_quality_controller_weights()
    
    scores = []
    total_weight = 0
    
    if results.get("fact_check_results"):
        fact_score = results["fact_check_results"].get("overall_score", 0.5)
        weight = weights.get("fact_checking", 0.3)
        scores.append(fact_score * weight)
        total_weight += weight
    
    if results.get("citation_verification"):
        citation_score = results["citation_verification"].get("overall_score", 0.5)
        weight = weights.get("citation_verification", 0.25)
        scores.append(citation_score * weight)
        total_weight += weight
    
    if results.get("quality_assessment"):
        quality_score = results["quality_assessment"].get("overall_score", 0.5)
        weight = weights.get("quality_assessment", 0.25)
        scores.append(quality_score * weight)
        total_weight += weight
    
    if results.get("source_evaluation"):
        source_score = results["source_evaluation"].get("overall_score", 0.5)
        weight = weights.get("source_evaluation", 0.2)
        scores.append(source_score * weight)
        total_weight += weight
    
    if total_weight > 0:
        return sum(scores) / total_weight
    else:
        return 0.5

def _determine_quality_level(score: float) -> str:
    """Determine quality level from score"""
    config_loader = get_config_loader()
    thresholds = config_loader.get_quality_thresholds()
    
    if score >= thresholds.get("excellent", 0.9):
        return "excellent"
    elif score >= thresholds.get("very_good", 0.8):
        return "very_good"
    elif score >= thresholds.get("good", 0.7):
        return "good"
    elif score >= thresholds.get("satisfactory", 0.6):
        return "satisfactory"
    elif score >= thresholds.get("needs_improvement", 0.5):
        return "needs_improvement"
    else:
        return "poor"

def _generate_recommendations(results: Dict[str, Any]) -> List[str]:
    """Generate quality improvement recommendations"""
    recommendations = []
    
    # Fact-checking recommendations
    if results.get("fact_check_results"):
        fact_results = results["fact_check_results"]
        if fact_results.get("unverified_claims"):
            recommendations.append("Verify or provide sources for unverified claims")
        if fact_results.get("contradictory_information"):
            recommendations.append("Resolve contradictory information with additional sources")
    
    # Citation recommendations
    if results.get("citation_verification"):
        citation_results = results["citation_verification"]
        if citation_results.get("missing_citations"):
            recommendations.append("Add citations for unsupported statements")
        if citation_results.get("invalid_citations"):
            recommendations.append("Fix or replace invalid citations")
    
    # Quality recommendations
    if results.get("quality_assessment"):
        quality_results = results["quality_assessment"]
        if quality_results.get("readability_issues"):
            recommendations.append("Improve readability and structure")
        if quality_results.get("coherence_issues"):
            recommendations.append("Enhance logical flow and coherence")
    
    # Source recommendations
    if results.get("source_evaluation"):
        source_results = results["source_evaluation"]
        if source_results.get("low_credibility_sources"):
            recommendations.append("Replace low-credibility sources with authoritative ones")
        if source_results.get("outdated_sources"):
            recommendations.append("Update outdated sources with recent information")
    
    return recommendations

async def _process_batch_quality_check(reports: List[QualityCheckRequest], priority: str):
    """Process batch quality check in background"""
    logger.info("Processing batch quality check", 
                report_count=len(reports), priority=priority)
    
    for report_request in reports:
        try:
            await perform_quality_check(report_request)
        except Exception as e:
            logger.error("Failed to process report in batch", 
                        report_id=report_request.report_id, error=str(e))
    
    logger.info("Batch quality check completed", report_count=len(reports))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    ) 