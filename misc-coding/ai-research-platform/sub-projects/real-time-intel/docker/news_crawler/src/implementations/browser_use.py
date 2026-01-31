"""
Browser-Use Implementation Adapter
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
import traceback

from browser_use import Browser
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import httpx
from bs4 import BeautifulSoup
import feedparser
from langdetect import detect
import re

from .base import BaseCrawlerAdapter
from ..models.job_config import (
    CrawlJobConfig, ProcessedArticle, ArticleMetadata, 
    ArticleSentiment, ArticleEntities, SourceType
)
from ..models.implementations import (
    ImplementationInfo, ImplementationType, ImplementationStatus,
    PerformanceMetrics, CapabilityFeatures
)


class BrowserUseAdapter(BaseCrawlerAdapter):
    """
    Browser-Use implementation for intelligent web crawling.
    
    This adapter uses the Browser-Use library to provide AI-powered
    web interaction capabilities for extracting news content.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "browser_use"
        self.version = "1.2.0"
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.httpx_client: Optional[httpx.AsyncClient] = None
        self.articles_processed = 0
        self.jobs_completed = 0
        self.start_time = datetime.now()
    
    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================
    
    async def initialize(self) -> bool:
        """Initialize Browser-Use adapter."""
        try:
            await self.log_info("Initializing Browser-Use adapter...")
            
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            
            # Initialize HTTP client for RSS feeds and simple requests
            self.httpx_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
            )
            
            # Initialize Browser-Use
            self.browser = Browser(
                task_description="Extract news articles and content",
                headless=True,
                browser_type="chromium"
            )
            
            # Test basic functionality
            await self._test_browser_functionality()
            
            self.initialized = True
            self.health_status = True
            self.last_health_check = datetime.now()
            
            await self.log_info("Browser-Use adapter initialized successfully")
            return True
            
        except Exception as e:
            await self.log_error(f"Failed to initialize Browser-Use adapter: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """Clean up Browser-Use resources."""
        try:
            await self.log_info("Cleaning up Browser-Use adapter...")
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.httpx_client:
                await self.httpx_client.aclose()
                self.httpx_client = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            self.initialized = False
            await self.log_info("Browser-Use adapter cleanup complete")
            return True
            
        except Exception as e:
            await self.log_error(f"Error during cleanup: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            if not self.initialized:
                return False
            
            # Test HTTP client
            if self.httpx_client:
                response = await self.httpx_client.get("https://httpbin.org/get")
                if response.status_code != 200:
                    return False
            
            # Test Browser-Use functionality
            if self.browser:
                # Simple browser test - just create and close a page
                await self._test_browser_functionality()
            
            self.health_status = True
            self.last_health_check = datetime.now()
            
            # Update uptime metrics
            uptime = (datetime.now() - self.start_time).total_seconds() / 3600
            await self.update_performance_metrics({"uptime_hours": uptime})
            
            return True
            
        except Exception as e:
            await self.log_error(f"Health check failed: {e}")
            self.health_status = False
            return False
    
    # ========================================================================
    # CRAWLING METHODS
    # ========================================================================
    
    async def execute_crawl(
        self, 
        job_id: str, 
        job_config: CrawlJobConfig
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a crawl job using Browser-Use."""
        
        start_time = datetime.now()
        articles_processed = 0
        errors_encountered = 0
        
        try:
            await self.log_info(f"Starting crawl job {job_id}")
            
            # Initial progress update
            yield {
                "type": "progress_update",
                "status": "initializing",
                "articles_processed": 0,
                "articles_total": job_config.source_config.parameters.max_articles,
                "current_source": job_config.source_config.parameters.url,
                "errors_encountered": 0,
                "completion_percentage": 0.0,
                "estimated_remaining": "calculating..."
            }
            
            # Validate source
            validation_result = await self.validate_source(job_config.source_config.parameters.url)
            if not validation_result["valid"]:
                yield {
                    "type": "error",
                    "error_message": f"Source validation failed: {validation_result.get('error_message', 'Unknown error')}"
                }
                return
            
            # Get article URLs based on source type
            article_urls = await self._get_article_urls(job_config)
            total_articles = min(len(article_urls), job_config.source_config.parameters.max_articles)
            
            yield {
                "type": "progress_update",
                "status": "processing",
                "articles_processed": 0,
                "articles_total": total_articles,
                "current_source": job_config.source_config.parameters.url,
                "errors_encountered": 0,
                "completion_percentage": 0.0,
                "estimated_remaining": f"{total_articles * 30}s"  # Estimate 30s per article
            }
            
            # Process each article
            for i, url in enumerate(article_urls[:job_config.source_config.parameters.max_articles]):
                try:
                    # Rate limiting
                    if i > 0:
                        delay = 1.0 / job_config.source_config.parameters.rate_limit
                        await asyncio.sleep(delay)
                    
                    # Extract article
                    article = await self.extract_article(url, job_config)
                    
                    if article:
                        articles_processed += 1
                        self.articles_processed += 1
                        
                        # Calculate quality score
                        quality_score = await self.calculate_quality_score(article)
                        article.quality_score = quality_score
                        
                        # Yield article extracted event
                        yield {
                            "type": "article_extracted",
                            "article_data": article.dict()
                        }
                        
                        # Progress update
                        completion = (i + 1) / total_articles * 100
                        elapsed = (datetime.now() - start_time).total_seconds()
                        avg_time_per_article = elapsed / (i + 1)
                        remaining_articles = total_articles - (i + 1)
                        estimated_remaining = int(remaining_articles * avg_time_per_article)
                        
                        yield {
                            "type": "progress_update",
                            "status": "processing",
                            "articles_processed": articles_processed,
                            "articles_total": total_articles,
                            "current_source": url,
                            "errors_encountered": errors_encountered,
                            "completion_percentage": completion,
                            "estimated_remaining": f"{estimated_remaining}s"
                        }
                    else:
                        errors_encountered += 1
                        await self.log_error(f"Failed to extract article from {url}")
                
                except Exception as e:
                    errors_encountered += 1
                    await self.log_error(f"Error processing {url}: {e}")
                    
                    yield {
                        "type": "error",
                        "error_message": f"Error processing {url}: {str(e)}"
                    }
            
            # Final completion update
            self.jobs_completed += 1
            
            # Update performance metrics
            total_time = (datetime.now() - start_time).total_seconds()
            articles_per_minute = (articles_processed / total_time) * 60 if total_time > 0 else 0
            success_rate = articles_processed / total_articles if total_articles > 0 else 0
            error_rate = errors_encountered / total_articles if total_articles > 0 else 0
            
            await self.update_performance_metrics({
                "avg_articles_per_minute": articles_per_minute,
                "success_rate": success_rate,
                "error_rate": error_rate
            })
            
            yield {
                "type": "progress_update",
                "status": "completed",
                "articles_processed": articles_processed,
                "articles_total": total_articles,
                "errors_encountered": errors_encountered,
                "completion_percentage": 100.0,
                "estimated_remaining": "0s"
            }
            
            await self.log_info(f"Crawl job {job_id} completed: {articles_processed} articles extracted")
            
        except Exception as e:
            await self.log_error(f"Crawl job {job_id} failed: {e}")
            yield {
                "type": "error",
                "error_message": f"Crawl job failed: {str(e)}"
            }
    
    async def extract_article(
        self, 
        url: str, 
        job_config: CrawlJobConfig
    ) -> Optional[ProcessedArticle]:
        """Extract a single article using Browser-Use."""
        
        try:
            await self.log_info(f"Extracting article from {url}")
            
            # Use Browser-Use (or shim) for intelligent content extraction
            result = await self._compat_get_content(
                url=url,
                task="Extract the main article content, title, author, and publication date from this page",
                timeout=job_config.source_config.parameters.timeout * 1000
            )
            
            if not result or not result.get("success"):
                await self.log_error(f"Browser-Use failed to extract content from {url}")
                return None
            
            content_data = result.get("content", {})
            
            # Create article metadata
            metadata = ArticleMetadata(
                title=content_data.get("title", "").strip(),
                url=url,
                source_domain=urlparse(url).netloc,
                published_at=self._parse_date(content_data.get("published_date")),
                author=content_data.get("author"),
                language=self._detect_language(content_data.get("content", "")),
                word_count=len(content_data.get("content", "").split()),
                reading_time_minutes=max(1, len(content_data.get("content", "").split()) // 200)
            )
            
            # Extract entities if requested
            entities = None
            if job_config.processing_options.extract_entities:
                entities = await self._extract_entities(content_data.get("content", ""))
            
            # Analyze sentiment if requested
            sentiment = None
            if job_config.processing_options.analyze_sentiment:
                sentiment = await self._analyze_sentiment(content_data.get("content", ""))
            
            # Generate summary if requested
            summary = None
            if job_config.processing_options.generate_summary:
                summary = await self._generate_summary(content_data.get("content", ""))
            
            # Extract keywords if requested
            keywords = []
            if job_config.processing_options.extract_keywords:
                keywords = await self._extract_keywords(content_data.get("content", ""))
            
            # Create processed article
            article = ProcessedArticle(
                article_id=str(uuid.uuid4()),
                metadata=metadata,
                content=content_data.get("content", ""),
                summary=summary,
                keywords=keywords,
                sentiment=sentiment,
                entities=entities,
                processed_at=datetime.now()
            )
            
            return article
            
        except Exception as e:
            await self.log_error(f"Error extracting article from {url}: {e}")
            return None
    
    async def validate_source(self, url: str) -> Dict[str, Any]:
        """Validate a source URL."""
        try:
            # Basic URL validation
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {
                    "valid": False,
                    "accessible": False,
                    "error_message": "Invalid URL format"
                }
            
            # Check accessibility
            response = await self.httpx_client.head(url, follow_redirects=True)
            accessible = response.status_code == 200
            
            if not accessible:
                return {
                    "valid": False,
                    "accessible": False,
                    "error_message": f"URL returned status {response.status_code}"
                }
            
            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            
            # Estimate articles (basic heuristic)
            estimated_articles = 1  # Default for single page
            
            if "rss" in content_type or "xml" in content_type:
                # RSS feed - try to parse and count entries
                feed_response = await self.httpx_client.get(url)
                feed = feedparser.parse(feed_response.text)
                estimated_articles = len(feed.entries)
            
            return {
                "valid": True,
                "accessible": True,
                "content_type": content_type,
                "estimated_articles": estimated_articles,
                "robots_txt_allowed": True,  # TODO: Implement robots.txt checking
                "error_message": None
            }
            
        except Exception as e:
            return {
                "valid": False,
                "accessible": False,
                "error_message": str(e)
            }
    
    # ========================================================================
    # INFORMATION METHODS
    # ========================================================================
    
    async def get_implementation_info(self) -> ImplementationInfo:
        """Get implementation information."""
        capabilities = CapabilityFeatures(
            javascript_support=True,
            dynamic_content=True,
            captcha_solving=False,  # Could be added with additional services
            rate_limiting=True,
            proxy_support=False,    # Could be added
            user_agent_rotation=False,
            session_persistence=True,
            multi_threading=False,  # Browser-Use is single-threaded per instance
            cloud_integration=True  # Can integrate with cloud services
        )
        
        return ImplementationInfo(
            name=self.name,
            type=ImplementationType.BROWSER_USE,
            version=self.version,
            description="AI-powered web crawling using Browser-Use library with intelligent content extraction",
            status=ImplementationStatus.AVAILABLE if self.health_status else ImplementationStatus.UNAVAILABLE,
            capabilities=capabilities,
            performance=self.performance_metrics,
            supported_sources=await self.get_supported_sources(),
            configuration_options={
                "headless": "Run browser in headless mode",
                "timeout": "Request timeout in seconds",
                "rate_limit": "Maximum requests per second",
                "browser_type": "Browser type (chromium, firefox, webkit)"
            },
            last_health_check=self.last_health_check,
            error_message=self.error_message
        )
    
    async def get_supported_sources(self) -> List[str]:
        """Get supported source types."""
        return [
            "news_website",
            "rss_feed", 
            "custom_url",
            "search_results"
        ]
    
    async def estimate_job_duration(self, job_config: CrawlJobConfig) -> int:
        """Estimate job duration in seconds."""
        # Base time per article (includes Browser-Use processing time)
        base_time_per_article = 45  # seconds
        
        # Adjust based on processing options
        multiplier = 1.0
        if job_config.processing_options.analyze_sentiment:
            multiplier += 0.2
        if job_config.processing_options.extract_entities:
            multiplier += 0.3
        if job_config.processing_options.generate_summary:
            multiplier += 0.4
        if job_config.processing_options.quality_assessment:
            multiplier += 0.1
        
        # Adjust for rate limiting
        rate_delay = 1.0 / job_config.source_config.parameters.rate_limit
        
        estimated_time = (
            job_config.source_config.parameters.max_articles * 
            base_time_per_article * 
            multiplier +
            job_config.source_config.parameters.max_articles * rate_delay
        )
        
        return int(estimated_time)
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _test_browser_functionality(self) -> bool:
        """Test basic browser functionality."""
        try:
            if not self.browser:
                return False
                
            # Simple test - navigate to a test page
            result = await self._compat_get_content(
                url="https://httpbin.org/html",
                task="Get the page title",
                timeout=10000
            )
            
            return result and result.get("success", False)
            
        except Exception as e:
            await self.log_error(f"Browser functionality test failed: {e}")
            return False
    
    async def _get_article_urls(self, job_config: CrawlJobConfig) -> List[str]:
        """Get list of article URLs to process."""
        source_url = job_config.source_config.parameters.url
        source_type = job_config.source_config.source_type
        
        if source_type == SourceType.RSS_FEED:
            return await self._get_rss_article_urls(source_url)
        elif source_type == SourceType.NEWS_WEBSITE:
            return await self._get_website_article_urls(source_url, job_config)
        else:
            # For custom URLs, just return the URL itself
            return [source_url]
    
    async def _get_rss_article_urls(self, rss_url: str) -> List[str]:
        """Extract article URLs from RSS feed."""
        try:
            response = await self.httpx_client.get(rss_url)
            feed = feedparser.parse(response.text)
            
            urls = []
            for entry in feed.entries:
                if hasattr(entry, 'link'):
                    urls.append(entry.link)
            
            return urls
            
        except Exception as e:
            await self.log_error(f"Error parsing RSS feed {rss_url}: {e}")
            return []
    
    async def _get_website_article_urls(self, website_url: str, job_config: CrawlJobConfig) -> List[str]:
        """Extract article URLs from a news website."""
        try:
            # Use Browser-Use (or shim) for intelligent content extraction
            result = await self._compat_get_content(
                url=website_url,
                task="Find and extract all article links from this news website homepage",
                timeout=job_config.source_config.parameters.timeout * 1000
            )
            
            if result and result.get("success"):
                links = result.get("content", {}).get("article_links", [])
                
                # Convert relative URLs to absolute
                absolute_urls = []
                for link in links:
                    if link.startswith('http'):
                        absolute_urls.append(link)
                    else:
                        absolute_urls.append(urljoin(website_url, link))
                
                return absolute_urls
            
            return []
            
        except Exception as e:
            await self.log_error(f"Error extracting article URLs from {website_url}: {e}")
            return []
    
    def _parse_date(self, date_string: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_string:
            return None
        
        try:
            # Try common date formats
            from dateutil.parser import parse
            return parse(date_string)
        except:
            return None
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language of text."""
        try:
            if not text or len(text) < 50:
                return None
            return detect(text)
        except:
            return None
    
    async def _extract_entities(self, content: str) -> Optional[ArticleEntities]:
        """Extract named entities from content."""
        # This is a placeholder - in a real implementation, you would use
        # NLP libraries like spaCy or integrate with the Mac Studio LLM endpoint
        try:
            # Basic regex-based entity extraction as placeholder
            entities = ArticleEntities()
            
            # Extract potential stock tickers (e.g., $AAPL, NASDAQ:GOOGL)
            ticker_pattern = r'\$[A-Z]{1,5}|[A-Z]{1,5}:[A-Z]{1,5}'
            entities.tickers = list(set(re.findall(ticker_pattern, content)))
            
            # Extract potential currency mentions
            currency_pattern = r'\b(?:USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY)\b'
            entities.currencies = list(set(re.findall(currency_pattern, content, re.IGNORECASE)))
            
            return entities
            
        except Exception as e:
            await self.log_error(f"Error extracting entities: {e}")
            return None
    
    async def _analyze_sentiment(self, content: str) -> Optional[ArticleSentiment]:
        """Analyze sentiment of content."""
        # This is a placeholder - in a real implementation, you would use
        # sentiment analysis libraries or integrate with the Mac Studio LLM endpoint
        try:
            # Basic keyword-based sentiment analysis as placeholder
            positive_words = ['good', 'great', 'excellent', 'positive', 'bullish', 'growth', 'gain']
            negative_words = ['bad', 'terrible', 'negative', 'bearish', 'decline', 'loss', 'crash']
            
            content_lower = content.lower()
            positive_count = sum(1 for word in positive_words if word in content_lower)
            negative_count = sum(1 for word in negative_words if word in content_lower)
            
            if positive_count > negative_count:
                overall_sentiment = "positive"
                confidence = min(0.8, 0.5 + (positive_count - negative_count) * 0.1)
            elif negative_count > positive_count:
                overall_sentiment = "negative"
                confidence = min(0.8, 0.5 + (negative_count - positive_count) * 0.1)
            else:
                overall_sentiment = "neutral"
                confidence = 0.5
            
            return ArticleSentiment(
                overall_sentiment=overall_sentiment,
                confidence_score=confidence,
                sentiment_scores={
                    "positive": positive_count / max(1, positive_count + negative_count),
                    "negative": negative_count / max(1, positive_count + negative_count),
                    "neutral": 1.0 - (positive_count + negative_count) / max(1, positive_count + negative_count)
                }
            )
            
        except Exception as e:
            await self.log_error(f"Error analyzing sentiment: {e}")
            return None
    
    async def _generate_summary(self, content: str) -> Optional[str]:
        """Generate a summary of the content."""
        try:
            # Simple extractive summarization - take first few sentences
            sentences = content.split('.')
            summary_sentences = sentences[:3]  # Take first 3 sentences
            return '. '.join(summary_sentences).strip() + '.'
            
        except Exception as e:
            await self.log_error(f"Error generating summary: {e}")
            return None
    
    async def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content."""
        try:
            # Simple keyword extraction - find common financial/news terms
            financial_keywords = [
                'stock', 'market', 'trading', 'investment', 'revenue', 'profit', 
                'earnings', 'shares', 'dividend', 'acquisition', 'merger', 'IPO',
                'quarterly', 'annual', 'growth', 'decline', 'bullish', 'bearish'
            ]
            
            content_lower = content.lower()
            found_keywords = []
            
            for keyword in financial_keywords:
                if keyword in content_lower:
                    found_keywords.append(keyword)
            
            return found_keywords[:10]  # Return top 10 keywords
            
        except Exception as e:
            await self.log_error(f"Error extracting keywords: {e}")
            return []
    
    # ========================================================================
    # COMPATIBILITY HELPERS
    # ========================================================================
    
    async def _compat_get_content(self, url: str, task: str = "", timeout: int = 30000):
        """Return page content via browser-use if available, else fallback.

        Args:
            url: Target URL.
            task: Human-readable extraction instruction (ignored by fallback).
            timeout: Timeout **in milliseconds** (same as old API).

        Returns:
            Dict matching the historical `get_content()` schema::
                {"success": bool, "content": {...}}

        This wrapper lets legacy code continue to call `await self._compat_get_content(...)`
        without worrying about library version differences.
        """

        # ------------------------------------------------------------------
        # Case 1 – Old browser-use (<0.3.0): call original helper directly.
        # ------------------------------------------------------------------
        if self.browser and hasattr(self.browser, "get_content"):
            return await self.browser.get_content(url=url, task=task, timeout=timeout)

        # ------------------------------------------------------------------
        # Case 2 – New browser-use: fallback to HTTP GET + Basic parsing.
        # ------------------------------------------------------------------
        try:
            resp = await self.httpx_client.get(url, timeout=timeout / 1000)
            if resp.status_code != 200:
                return {"success": False, "status_code": resp.status_code}

            soup = BeautifulSoup(resp.text, "lxml")

            # Extract plain-text content (rudimentary but good enough).
            text_content = soup.get_text(" ", strip=True)

            # Basic link collection (used by `_get_website_article_urls`).
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                # Skip anchor links / mailto etc.
                if href.startswith("#") or href.startswith("mailto:"):
                    continue
                links.append(href)

            return {
                "success": True,
                "content": {
                    "content": text_content,
                    "title": soup.title.string.strip() if soup.title else "",
                    "article_links": links,
                },
            }
        except Exception as e:
            # Log & return uniform failure structure
            await self.log_error(f"_compat_get_content fallback error: {e}")
            return {"success": False, "error": str(e)} 