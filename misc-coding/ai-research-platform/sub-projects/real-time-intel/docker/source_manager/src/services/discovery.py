"""
Source Discovery Service

Intelligent source discovery and recommendation system.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple, Any
from urllib.parse import urljoin, urlparse
import re

import httpx
import feedparser
from bs4 import BeautifulSoup
import tldextract

from ..models.source_models import (
    Source, SourceDiscovery, DiscoveryResult, SourceType, ContentCategory,
    RSSFeedInfo, SourceQuality
)
from ..utils.database import DatabaseManager
from .evaluator import SourceEvaluator


logger = logging.getLogger(__name__)


class SourceDiscoveryService:
    """
    Intelligent source discovery service for finding and evaluating new sources.
    """
    
    def __init__(self, db_manager: DatabaseManager, evaluator: SourceEvaluator):
        self.db = db_manager
        self.evaluator = evaluator
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Discovery cache
        self._discovery_cache: Dict[str, List[DiscoveryResult]] = {}
        self._cache_ttl = 86400  # 24 hours
        
        # Known source directories and aggregators
        self.source_directories = [
            "https://www.feedspot.com",
            "https://alltop.com",
            "https://feedly.com",
            "https://www.journalism.org"
        ]
        
        # RSS discovery patterns
        self.rss_patterns = [
            r'<link[^>]*type=["\']application/rss\+xml["\'][^>]*>',
            r'<link[^>]*type=["\']application/atom\+xml["\'][^>]*>',
            r'href=["\']([^"\']*(?:rss|feed|atom)[^"\']*)["\']'
        ]
        
        # Common RSS feed paths
        self.common_feed_paths = [
            '/rss', '/rss.xml', '/feed', '/feed.xml', '/feeds/all.atom.xml',
            '/atom.xml', '/index.xml', '/rss/news', '/feeds/news.xml',
            '/api/rss', '/blog/feed', '/news/rss'
        ]
        
        # Quality source domains for similarity matching
        self.quality_domains = {
            'reuters.com', 'bloomberg.com', 'wsj.com', 'ft.com',
            'economist.com', 'bbc.com', 'ap.org', 'npr.org',
            'cnn.com', 'nytimes.com', 'washingtonpost.com'
        }
    
    async def discover_sources(
        self,
        query: str,
        categories: List[ContentCategory] = None,
        source_types: List[SourceType] = None,
        max_results: int = 20,
        quality_threshold: float = 0.5,
        include_evaluations: bool = True
    ) -> Tuple[SourceDiscovery, List[DiscoveryResult]]:
        """
        Discover new sources based on query and criteria.
        
        Args:
            query: Search query for source discovery
            categories: Target content categories
            source_types: Target source types
            max_results: Maximum results to return
            quality_threshold: Minimum quality threshold
            include_evaluations: Whether to include full evaluations
            
        Returns:
            Tuple of (SourceDiscovery, List[DiscoveryResult])
        """
        start_time = time.time()
        
        # Check cache
        cache_key = f"{query}:{categories}:{source_types}:{max_results}"
        if cache_key in self._discovery_cache:
            cached_results = self._discovery_cache[cache_key]
            logger.info(f"Using cached discovery results for query: {query}")
            
            # Create discovery record
            discovery = SourceDiscovery(
                query=query,
                discovery_method="cached",
                target_categories=categories or [],
                max_results=max_results,
                sources_found=len(cached_results),
                sources_evaluated=len([r for r in cached_results if r.evaluation]),
                high_quality_sources=len([r for r in cached_results if r.evaluation and r.evaluation.quality_score.overall_score >= 0.7]),
                completed_at=datetime.now(timezone.utc),
                duration_seconds=time.time() - start_time,
                status="completed"
            )
            
            return discovery, cached_results[:max_results]
        
        logger.info(f"Starting source discovery for query: {query}")
        
        # Create discovery record
        discovery = SourceDiscovery(
            query=query,
            discovery_method="multi_method",
            target_categories=categories or [],
            max_results=max_results
        )
        
        try:
            # Multiple discovery methods
            all_results = []
            
            # Method 1: RSS directory search
            rss_results = await self._discover_via_rss_directories(query, categories)
            all_results.extend(rss_results)
            
            # Method 2: Search engine discovery
            search_results = await self._discover_via_search_engines(query, categories)
            all_results.extend(search_results)
            
            # Method 3: Similar source discovery
            similar_results = await self._discover_similar_sources(query, categories)
            all_results.extend(similar_results)
            
            # Method 4: RSS feed discovery from known sites
            feed_results = await self._discover_rss_feeds(query)
            all_results.extend(feed_results)
            
            # Remove duplicates and filter existing sources
            unique_results = await self._deduplicate_and_filter(all_results)
            
            # Evaluate sources if requested
            if include_evaluations:
                evaluated_results = await self._evaluate_discovered_sources(unique_results)
            else:
                evaluated_results = unique_results
            
            # Filter by quality threshold
            quality_filtered = [
                result for result in evaluated_results
                if not result.evaluation or result.evaluation.quality_score.overall_score >= quality_threshold
            ]
            
            # Sort by discovery score and quality
            quality_filtered.sort(
                key=lambda x: (
                    x.evaluation.quality_score.overall_score if x.evaluation else 0.5,
                    x.discovery_score
                ),
                reverse=True
            )
            
            # Limit results
            final_results = quality_filtered[:max_results]
            
            # Update discovery record
            discovery.sources_found = len(unique_results)
            discovery.sources_evaluated = len([r for r in final_results if r.evaluation])
            discovery.high_quality_sources = len([
                r for r in final_results 
                if r.evaluation and r.evaluation.quality_score.overall_score >= 0.7
            ])
            discovery.completed_at = datetime.now(timezone.utc)
            discovery.duration_seconds = time.time() - start_time
            discovery.status = "completed"
            
            # Cache results
            self._discovery_cache[cache_key] = final_results
            
            # Save discovery to database
            await self.db.save_source_discovery(discovery, final_results)
            
            logger.info(f"Completed source discovery: found {len(final_results)} sources in {discovery.duration_seconds:.2f}s")
            
            return discovery, final_results
            
        except Exception as e:
            logger.error(f"Error in source discovery: {str(e)}")
            discovery.status = "failed"
            discovery.completed_at = datetime.now(timezone.utc)
            discovery.duration_seconds = time.time() - start_time
            raise
    
    async def _discover_via_rss_directories(
        self, 
        query: str, 
        categories: List[ContentCategory] = None
    ) -> List[DiscoveryResult]:
        """Discover sources via RSS directories and aggregators."""
        results = []
        
        try:
            # Search Feedspot (simplified)
            feedspot_results = await self._search_feedspot(query, categories)
            results.extend(feedspot_results)
            
            # Search AllTop (simplified)
            alltop_results = await self._search_alltop(query, categories)
            results.extend(alltop_results)
            
        except Exception as e:
            logger.error(f"Error in RSS directory discovery: {str(e)}")
        
        return results
    
    async def _discover_via_search_engines(
        self, 
        query: str, 
        categories: List[ContentCategory] = None
    ) -> List[DiscoveryResult]:
        """Discover sources via search engine queries."""
        results = []
        
        try:
            # Construct search queries
            search_queries = self._build_search_queries(query, categories)
            
            for search_query in search_queries:
                # Simulate search engine results (in real implementation, would use search APIs)
                search_results = await self._perform_web_search(search_query)
                
                for url in search_results:
                    try:
                        source = await self._create_source_from_url(url)
                        if source:
                            result = DiscoveryResult(
                                source=source,
                                discovery_score=0.7,  # Base score for search results
                                discovery_method="search_engine",
                                confidence=0.6
                            )
                            results.append(result)
                    except Exception as e:
                        logger.error(f"Error creating source from {url}: {str(e)}")
                        continue
                
        except Exception as e:
            logger.error(f"Error in search engine discovery: {str(e)}")
        
        return results
    
    async def _discover_similar_sources(
        self, 
        query: str, 
        categories: List[ContentCategory] = None
    ) -> List[DiscoveryResult]:
        """Discover sources similar to existing high-quality sources."""
        results = []
        
        try:
            # Get existing high-quality sources in relevant categories
            existing_sources = await self.db.get_sources_by_categories(categories or [])
            high_quality_sources = [
                s for s in existing_sources 
                if hasattr(s, 'quality_score') and s.quality_score >= 0.7
            ]
            
            # Find similar domains and sources
            for source in high_quality_sources[:5]:  # Limit to top 5
                similar_urls = await self._find_similar_sources(source.domain, query)
                
                for url in similar_urls:
                    try:
                        new_source = await self._create_source_from_url(url)
                        if new_source:
                            result = DiscoveryResult(
                                source=new_source,
                                discovery_score=0.8,  # Higher score for similarity-based discovery
                                discovery_method="similarity_based",
                                confidence=0.7
                            )
                            results.append(result)
                    except Exception as e:
                        logger.error(f"Error creating similar source from {url}: {str(e)}")
                        continue
                
        except Exception as e:
            logger.error(f"Error in similarity-based discovery: {str(e)}")
        
        return results
    
    async def _discover_rss_feeds(self, query: str) -> List[DiscoveryResult]:
        """Discover RSS feeds from known websites."""
        results = []
        
        try:
            # Start with quality domains
            target_domains = list(self.quality_domains)
            
            # Add domains from query if it contains URLs
            query_domains = self._extract_domains_from_query(query)
            target_domains.extend(query_domains)
            
            for domain in target_domains[:10]:  # Limit to prevent overload
                try:
                    feeds = await self._discover_feeds_for_domain(domain)
                    
                    for feed_url in feeds:
                        source = await self._create_source_from_url(feed_url, SourceType.RSS_FEED)
                        if source:
                            result = DiscoveryResult(
                                source=source,
                                discovery_score=0.9,  # High score for RSS feeds
                                discovery_method="rss_discovery",
                                confidence=0.8
                            )
                            results.append(result)
                            
                except Exception as e:
                    logger.error(f"Error discovering feeds for {domain}: {str(e)}")
                    continue
                
        except Exception as e:
            logger.error(f"Error in RSS feed discovery: {str(e)}")
        
        return results
    
    async def _discover_feeds_for_domain(self, domain: str) -> List[str]:
        """Discover RSS feeds for a specific domain."""
        feeds = []
        base_url = f"https://{domain}"
        
        try:
            # Method 1: Check common feed paths
            for path in self.common_feed_paths:
                feed_url = urljoin(base_url, path)
                if await self._is_valid_feed(feed_url):
                    feeds.append(feed_url)
            
            # Method 2: Parse homepage for feed links
            try:
                response = await self.http_client.get(base_url, timeout=10.0)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for RSS/Atom link tags
                feed_links = soup.find_all('link', type=re.compile(r'application/(rss|atom)\+xml'))
                for link in feed_links:
                    href = link.get('href')
                    if href:
                        feed_url = urljoin(base_url, href)
                        if await self._is_valid_feed(feed_url):
                            feeds.append(feed_url)
                
                # Look for feed links in content
                for pattern in self.rss_patterns:
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0]
                        feed_url = urljoin(base_url, match)
                        if await self._is_valid_feed(feed_url):
                            feeds.append(feed_url)
                            
            except Exception as e:
                logger.error(f"Error parsing homepage for {domain}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error discovering feeds for {domain}: {str(e)}")
        
        return list(set(feeds))  # Remove duplicates
    
    async def _is_valid_feed(self, url: str) -> bool:
        """Check if URL is a valid RSS/Atom feed."""
        try:
            response = await self.http_client.get(url, timeout=5.0)
            if response.status_code != 200:
                return False
            
            # Parse with feedparser
            feed = feedparser.parse(response.content)
            return len(feed.entries) > 0 and not feed.bozo
            
        except Exception:
            return False
    
    async def _create_source_from_url(
        self, 
        url: str, 
        source_type: SourceType = None
    ) -> Optional[Source]:
        """Create Source object from URL."""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Skip if we already have this source
            existing = await self.db.get_source_by_url(url)
            if existing:
                return None
            
            # Detect source type if not provided
            if not source_type:
                source_type = await self._detect_source_type(url)
            
            # Get basic site information
            site_info = await self._get_site_info(url)
            
            source = Source(
                name=site_info.get('title', self._extract_site_name(domain)),
                url=url,
                domain=domain,
                source_type=source_type,
                primary_category=site_info.get('category', ContentCategory.GENERAL),
                description=site_info.get('description'),
                language=site_info.get('language', 'en')
            )
            
            return source
            
        except Exception as e:
            logger.error(f"Error creating source from URL {url}: {str(e)}")
            return None
    
    async def _get_site_info(self, url: str) -> Dict[str, Any]:
        """Get basic site information."""
        info = {}
        
        try:
            response = await self.http_client.get(url, timeout=10.0)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                info['title'] = title_tag.text.strip()
            
            # Extract description
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                info['description'] = desc_tag.get('content', '').strip()
            
            # Extract language
            html_tag = soup.find('html')
            if html_tag and html_tag.get('lang'):
                info['language'] = html_tag.get('lang')[:2]  # Get language code
            
            # Detect category from content
            info['category'] = self._detect_category_from_content(soup.get_text())
            
        except Exception as e:
            logger.error(f"Error getting site info for {url}: {str(e)}")
        
        return info
    
    async def _deduplicate_and_filter(self, results: List[DiscoveryResult]) -> List[DiscoveryResult]:
        """Remove duplicates and filter out existing sources."""
        seen_urls = set()
        seen_domains = set()
        unique_results = []
        
        # Get existing source URLs
        existing_urls = await self.db.get_all_source_urls()
        existing_url_set = set(existing_urls)
        
        for result in results:
            url = str(result.source.url)
            domain = result.source.domain
            
            # Skip if URL already exists
            if url in existing_url_set:
                continue
            
            # Skip if we've already seen this URL in results
            if url in seen_urls:
                continue
            
            # Limit sources per domain to avoid over-representation
            domain_count = sum(1 for existing_domain in seen_domains if existing_domain == domain)
            if domain_count >= 3:  # Max 3 sources per domain
                continue
            
            seen_urls.add(url)
            seen_domains.add(domain)
            unique_results.append(result)
        
        return unique_results
    
    async def _evaluate_discovered_sources(self, results: List[DiscoveryResult]) -> List[DiscoveryResult]:
        """Evaluate discovered sources for quality."""
        evaluated_results = []
        
        # Limit concurrent evaluations
        semaphore = asyncio.Semaphore(5)
        
        async def evaluate_single(result: DiscoveryResult) -> DiscoveryResult:
            async with semaphore:
                try:
                    source, evaluation = await self.evaluator.evaluate_source(
                        str(result.source.url),
                        result.source.source_type,
                        sample_articles=5  # Smaller sample for discovery
                    )
                    result.source = source
                    result.evaluation = evaluation
                    return result
                except Exception as e:
                    logger.error(f"Error evaluating discovered source {result.source.url}: {str(e)}")
                    return result
        
        # Evaluate sources concurrently
        tasks = [evaluate_single(result) for result in results]
        evaluated_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        return [result for result in evaluated_results if isinstance(result, DiscoveryResult)]
    
    # Helper methods (simplified implementations)
    
    async def _search_feedspot(self, query: str, categories: List[ContentCategory]) -> List[DiscoveryResult]:
        """Search Feedspot for relevant feeds."""
        # Simplified implementation - would use actual Feedspot API/scraping
        return []
    
    async def _search_alltop(self, query: str, categories: List[ContentCategory]) -> List[DiscoveryResult]:
        """Search AllTop for relevant sources."""
        # Simplified implementation - would use actual AllTop scraping
        return []
    
    def _build_search_queries(self, query: str, categories: List[ContentCategory]) -> List[str]:
        """Build search engine queries for source discovery."""
        queries = []
        
        # Base query
        queries.append(f'"{query}" RSS feed')
        queries.append(f'"{query}" news source')
        
        # Category-specific queries
        if categories:
            for category in categories:
                queries.append(f'"{query}" {category.value} RSS')
                queries.append(f'{category.value} "{query}" news')
        
        return queries
    
    async def _perform_web_search(self, query: str) -> List[str]:
        """Perform web search and extract URLs."""
        # Simplified implementation - would use actual search API
        # For now, return empty list
        return []
    
    async def _find_similar_sources(self, domain: str, query: str) -> List[str]:
        """Find sources similar to given domain."""
        # Simplified implementation - would use similarity algorithms
        return []
    
    def _extract_domains_from_query(self, query: str) -> List[str]:
        """Extract domain names from query string."""
        domains = []
        
        # Simple regex to find domain-like patterns
        domain_pattern = r'\b([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b'
        matches = re.findall(domain_pattern, query)
        
        for match in matches:
            if isinstance(match, tuple):
                domains.append(match[0] + match[1])
            else:
                domains.append(match)
        
        return domains
    
    async def _detect_source_type(self, url: str) -> SourceType:
        """Detect source type from URL."""
        if any(pattern in url.lower() for pattern in ['rss', 'feed', 'atom', '.xml']):
            return SourceType.RSS_FEED
        elif 'blog' in url.lower():
            return SourceType.BLOG
        else:
            return SourceType.NEWS_WEBSITE
    
    def _detect_category_from_content(self, content: str) -> ContentCategory:
        """Detect content category from text content."""
        content_lower = content.lower()
        
        # Simple keyword-based detection
        if any(keyword in content_lower for keyword in ['business', 'finance', 'economy', 'market']):
            return ContentCategory.BUSINESS
        elif any(keyword in content_lower for keyword in ['technology', 'tech', 'software', 'ai']):
            return ContentCategory.TECHNOLOGY
        elif any(keyword in content_lower for keyword in ['politics', 'government', 'election']):
            return ContentCategory.POLITICS
        elif any(keyword in content_lower for keyword in ['health', 'medical', 'medicine']):
            return ContentCategory.HEALTH
        elif any(keyword in content_lower for keyword in ['science', 'research', 'study']):
            return ContentCategory.SCIENCE
        else:
            return ContentCategory.GENERAL
    
    def _extract_site_name(self, domain: str) -> str:
        """Extract readable site name from domain."""
        domain_info = tldextract.extract(domain)
        return domain_info.domain.title()
    
    async def close(self):
        """Clean up resources."""
        await self.http_client.aclose() 