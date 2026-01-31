"""
Base Crawler Adapter Interface
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, List, Optional
import asyncio
from datetime import datetime

from ..models.job_config import CrawlJobConfig, ProcessedArticle
from ..models.implementations import ImplementationInfo, PerformanceMetrics, CapabilityFeatures


class BaseCrawlerAdapter(ABC):
    """
    Base interface for all crawler implementations.
    
    Each implementation (Browser-Use, Web Actions AI, etc.) must inherit from this
    and implement all abstract methods to provide a consistent interface.
    """
    
    def __init__(self):
        self.name: str = "base"
        self.version: str = "1.0.0"
        self.initialized: bool = False
        self.health_status: bool = False
        self.last_health_check: Optional[datetime] = None
        self.performance_metrics: PerformanceMetrics = PerformanceMetrics()
        self.error_message: Optional[str] = None
    
    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the crawler implementation.
        
        This should set up any required resources, validate configuration,
        and prepare the implementation for use.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> bool:
        """
        Clean up resources used by the implementation.
        
        This should gracefully shut down any connections, close browser instances,
        and clean up temporary resources.
        
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Perform a health check on the implementation.
        
        This should verify that the implementation is ready to accept new jobs
        and all dependencies are available.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        pass
    
    # ========================================================================
    # CRAWLING METHODS
    # ========================================================================
    
    @abstractmethod
    async def execute_crawl(
        self, 
        job_id: str, 
        job_config: CrawlJobConfig
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a crawl job using this implementation.
        
        This is the main crawling method that should:
        1. Parse the job configuration
        2. Execute the crawling according to the configuration
        3. Yield progress updates throughout the process
        4. Handle errors gracefully
        
        Args:
            job_id: Unique identifier for this crawl job
            job_config: Complete crawl job configuration
            
        Yields:
            Dict[str, Any]: Progress updates with keys like:
                - type: "progress_update", "article_extracted", "error", "completion"
                - status: Current status string
                - articles_processed: Number of articles processed so far
                - current_source: Currently processing source URL
                - errors_encountered: Number of errors encountered
                - completion_percentage: Progress percentage (0-100)
                - estimated_remaining: Estimated time remaining
                - article_data: Complete article data (when type="article_extracted")
                - error_message: Error details (when type="error")
        """
        pass
    
    @abstractmethod
    async def extract_article(
        self, 
        url: str, 
        job_config: CrawlJobConfig
    ) -> Optional[ProcessedArticle]:
        """
        Extract a single article from a URL.
        
        This method should handle the extraction of a single article,
        including content extraction, metadata parsing, and quality assessment.
        
        Args:
            url: The URL to extract content from
            job_config: Job configuration with processing options
            
        Returns:
            ProcessedArticle: Extracted and processed article data, or None if failed
        """
        pass
    
    @abstractmethod
    async def validate_source(self, url: str) -> Dict[str, Any]:
        """
        Validate that a source URL is accessible and scrapeable.
        
        This should check if the URL is accessible, returns valid content,
        and can be processed by this implementation.
        
        Args:
            url: The source URL to validate
            
        Returns:
            Dict[str, Any]: Validation result with keys:
                - valid: bool
                - accessible: bool
                - content_type: str
                - estimated_articles: int
                - robots_txt_allowed: bool
                - error_message: str (if any)
        """
        pass
    
    # ========================================================================
    # INFORMATION METHODS
    # ========================================================================
    
    @abstractmethod
    async def get_implementation_info(self) -> ImplementationInfo:
        """
        Get complete information about this implementation.
        
        Returns:
            ImplementationInfo: Complete implementation details
        """
        pass
    
    @abstractmethod
    async def get_supported_sources(self) -> List[str]:
        """
        Get list of supported source types.
        
        Returns:
            List[str]: List of supported source types (e.g., "rss_feed", "news_website")
        """
        pass
    
    @abstractmethod
    async def estimate_job_duration(self, job_config: CrawlJobConfig) -> int:
        """
        Estimate how long a job will take to complete.
        
        Args:
            job_config: The job configuration to estimate
            
        Returns:
            int: Estimated duration in seconds
        """
        pass
    
    # ========================================================================
    # HELPER METHODS (Default implementations provided)
    # ========================================================================
    
    async def update_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Update performance metrics for this implementation.
        
        Args:
            metrics: Dictionary of metrics to update
        """
        if "avg_articles_per_minute" in metrics:
            self.performance_metrics.avg_articles_per_minute = metrics["avg_articles_per_minute"]
        if "success_rate" in metrics:
            self.performance_metrics.success_rate = metrics["success_rate"]
        if "avg_response_time_ms" in metrics:
            self.performance_metrics.avg_response_time_ms = metrics["avg_response_time_ms"]
        if "memory_usage_mb" in metrics:
            self.performance_metrics.memory_usage_mb = metrics["memory_usage_mb"]
        if "cpu_usage_percent" in metrics:
            self.performance_metrics.cpu_usage_percent = metrics["cpu_usage_percent"]
        if "error_rate" in metrics:
            self.performance_metrics.error_rate = metrics["error_rate"]
        if "uptime_hours" in metrics:
            self.performance_metrics.uptime_hours = metrics["uptime_hours"]
    
    async def log_error(self, error_message: str) -> None:
        """
        Log an error for this implementation.
        
        Args:
            error_message: The error message to log
        """
        self.error_message = error_message
        self.health_status = False
        # TODO: Add structured logging here
        print(f"[{self.name}] ERROR: {error_message}")
    
    async def log_info(self, message: str) -> None:
        """
        Log an info message for this implementation.
        
        Args:
            message: The info message to log
        """
        # TODO: Add structured logging here
        print(f"[{self.name}] INFO: {message}")
    
    async def calculate_quality_score(self, article: ProcessedArticle) -> float:
        """
        Calculate a quality score for an extracted article.
        
        This is a default implementation that can be overridden by specific implementations.
        
        Args:
            article: The article to score
            
        Returns:
            float: Quality score between 0.0 and 1.0
        """
        score = 0.0
        
        # Basic scoring criteria
        if article.metadata.title and len(article.metadata.title) > 10:
            score += 0.2
        
        if article.content and len(article.content) > 100:
            score += 0.3
        
        if article.metadata.word_count > 200:
            score += 0.2
        
        if article.metadata.author:
            score += 0.1
        
        if article.metadata.published_at:
            score += 0.1
        
        if article.summary and len(article.summary) > 50:
            score += 0.1
        
        return min(score, 1.0)
    
    # ========================================================================
    # CONTEXT MANAGER SUPPORT
    # ========================================================================
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
        return False 