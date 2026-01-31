"""API client for Twin-Report KB backend services."""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
import httpx
import structlog
from datetime import datetime

from .config import SERVICES, HEALTH_ENDPOINTS
from .models import (
    ServiceStatus, ServiceHealthResponse, SystemHealthResponse,
    DocumentResult, QualityAssessment, GapAnalysis, TopicCategories
)

logger = structlog.get_logger(__name__)


class TwinReportKBClient:
    """Client for interacting with Twin-Report KB backend services."""
    
    def __init__(self, timeout: int = 30):
        """Initialize the API client."""
        self.timeout = timeout
        self.session = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        """Close the HTTP session."""
        await self.session.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    # Health Check Methods
    async def check_service_health(self, service_name: str) -> ServiceHealthResponse:
        """Check health of a specific service."""
        start_time = time.time()
        
        try:
            if service_name not in HEALTH_ENDPOINTS:
                return ServiceHealthResponse(
                    service=service_name,
                    status=ServiceStatus.UNKNOWN,
                    error=f"Unknown service: {service_name}"
                )
            
            response = await self.session.get(HEALTH_ENDPOINTS[service_name])
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return ServiceHealthResponse(
                    service=service_name,
                    status=ServiceStatus.HEALTHY,
                    response_time=response_time
                )
            else:
                return ServiceHealthResponse(
                    service=service_name,
                    status=ServiceStatus.UNHEALTHY,
                    response_time=response_time,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            logger.error("Service health check failed", service=service_name, error=str(e))
            return ServiceHealthResponse(
                service=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time=response_time,
                error=str(e)
            )
    
    async def check_system_health(self) -> SystemHealthResponse:
        """Check health of all services."""
        tasks = [
            self.check_service_health(service_name)
            for service_name in SERVICES.keys()
        ]
        
        health_responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        services = {}
        healthy_count = 0
        
        for i, response in enumerate(health_responses):
            service_name = list(SERVICES.keys())[i]
            
            if isinstance(response, Exception):
                services[service_name] = ServiceHealthResponse(
                    service=service_name,
                    status=ServiceStatus.UNHEALTHY,
                    error=str(response)
                )
            else:
                services[service_name] = response
                if response.status == ServiceStatus.HEALTHY:
                    healthy_count += 1
        
        # Determine overall status
        total_services = len(SERVICES)
        if healthy_count == total_services:
            overall_status = ServiceStatus.HEALTHY
        elif healthy_count > 0:
            overall_status = ServiceStatus.UNHEALTHY  # Partial failure
        else:
            overall_status = ServiceStatus.UNHEALTHY
        
        return SystemHealthResponse(
            services=services,
            overall_status=overall_status
        )
    
    # Document Parser Methods
    async def parse_document(
        self,
        file_data: bytes,
        filename: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Parse a document using the Document Parser service."""
        try:
            files = {"file": (filename, file_data)}
            data = options or {}
            
            response = await self.session.post(
                f"{SERVICES['document_parser']}/parse/upload",
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error("Document parsing failed", filename=filename, error=str(e))
            raise
    
    async def parse_url(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse a URL using the Document Parser service."""
        try:
            data = {"url": url}
            if options:
                data.update(options)
            
            response = await self.session.post(
                f"{SERVICES['document_parser']}/parse/url",
                json=data
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error("URL parsing failed", url=url, error=str(e))
            raise
    
    async def parse_google_doc(
        self,
        doc_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Parse a Google Doc using the Document Parser service."""
        try:
            data = {"doc_id": doc_id}
            if options:
                data.update(options)
            
            response = await self.session.post(
                f"{SERVICES['document_parser']}/parse/google-doc",
                json=data
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error("Google Doc parsing failed", doc_id=doc_id, error=str(e))
            raise
    
    async def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get a parsed document by ID."""
        try:
            response = await self.session.get(
                f"{SERVICES['document_parser']}/document/{document_id}"
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error("Get document failed", document_id=document_id, error=str(e))
            raise
    
    # Topic Manager Methods
    async def categorize_content(
        self,
        content: str,
        options: Optional[Dict[str, Any]] = None
    ) -> TopicCategories:
        """Categorize content using the Topic Manager service."""
        try:
            data = {"content": content}
            if options:
                data.update(options)
            
            response = await self.session.post(
                f"{SERVICES['topic_manager']}/categorize",
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            return TopicCategories(**result)
            
        except Exception as e:
            logger.error("Content categorization failed", error=str(e))
            raise
    
    # Quality Controller Methods
    async def check_quality(
        self,
        content: str,
        options: Optional[Dict[str, Any]] = None
    ) -> QualityAssessment:
        """Check content quality using the Quality Controller service."""
        try:
            data = {"content": content}
            if options:
                data.update(options)
            
            response = await self.session.post(
                f"{SERVICES['quality_controller']}/quality-check",
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            return QualityAssessment(**result)
            
        except Exception as e:
            logger.error("Quality check failed", error=str(e))
            raise
    
    # Diff Worker Methods
    async def analyze_diff(
        self,
        content1: str,
        content2: str,
        analysis_type: str = "comprehensive",
        options: Optional[Dict[str, Any]] = None
    ) -> GapAnalysis:
        """Analyze differences using the Diff Worker service."""
        try:
            data = {
                "content1": content1,
                "content2": content2,
                "analysis_type": analysis_type
            }
            if options:
                data.update(options)
            
            response = await self.session.post(
                f"{SERVICES['diff_worker']}/analyze-diff",
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            return GapAnalysis(**result)
            
        except Exception as e:
            logger.error("Diff analysis failed", error=str(e))
            raise
    
    # Integrated Workflow Methods
    async def process_document_full_pipeline(
        self,
        file_data: bytes,
        filename: str,
        analysis_depth: str = "comprehensive",
        compare_with: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a document through the complete analysis pipeline."""
        try:
            # Step 1: Parse document
            logger.info("Starting document parsing", filename=filename)
            parse_result = await self.parse_document(file_data, filename)
            content = parse_result.get("content", "")
            document_id = parse_result.get("document_id")
            
            # Step 2: Categorize content
            logger.info("Categorizing content", document_id=document_id)
            categories = await self.categorize_content(content)
            
            # Step 3: Check quality
            logger.info("Checking quality", document_id=document_id)
            quality = await self.check_quality(content)
            
            # Step 4: Analyze gaps (if comparison content provided)
            gap_analysis = None
            if compare_with:
                logger.info("Analyzing gaps", document_id=document_id)
                gap_analysis = await self.analyze_diff(content, compare_with, analysis_depth)
            
            # Combine results
            result = {
                "document_id": document_id,
                "filename": filename,
                "content": content,
                "parse_result": parse_result,
                "categories": categories.dict(),
                "quality_assessment": quality.dict(),
                "gap_analysis": gap_analysis.dict() if gap_analysis else None,
                "processing_time": parse_result.get("processing_time", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info("Document processing completed", document_id=document_id)
            return result
            
        except Exception as e:
            logger.error("Full pipeline processing failed", filename=filename, error=str(e))
            raise
    
    async def process_url_full_pipeline(
        self,
        url: str,
        analysis_depth: str = "comprehensive",
        compare_with: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a URL through the complete analysis pipeline."""
        try:
            # Step 1: Parse URL
            logger.info("Starting URL parsing", url=url)
            parse_result = await self.parse_url(url)
            content = parse_result.get("content", "")
            document_id = parse_result.get("document_id")
            
            # Step 2: Categorize content
            logger.info("Categorizing content", document_id=document_id)
            categories = await self.categorize_content(content)
            
            # Step 3: Check quality
            logger.info("Checking quality", document_id=document_id)
            quality = await self.check_quality(content)
            
            # Step 4: Analyze gaps (if comparison content provided)
            gap_analysis = None
            if compare_with:
                logger.info("Analyzing gaps", document_id=document_id)
                gap_analysis = await self.analyze_diff(content, compare_with, analysis_depth)
            
            # Combine results
            result = {
                "document_id": document_id,
                "url": url,
                "content": content,
                "parse_result": parse_result,
                "categories": categories.dict(),
                "quality_assessment": quality.dict(),
                "gap_analysis": gap_analysis.dict() if gap_analysis else None,
                "processing_time": parse_result.get("processing_time", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info("URL processing completed", document_id=document_id)
            return result
            
        except Exception as e:
            logger.error("Full pipeline URL processing failed", url=url, error=str(e))
            raise


# Global client instance
client = TwinReportKBClient() 