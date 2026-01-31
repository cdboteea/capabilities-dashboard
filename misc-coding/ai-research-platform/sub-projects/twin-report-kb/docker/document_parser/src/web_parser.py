#!/usr/bin/env python3
"""
Web Parser for Document Parser
Extracts content from web pages and URLs
"""

import asyncio
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
import re

import httpx
from bs4 import BeautifulSoup
# import newspaper  # Disabled due to lxml compatibility
# from readability import Document  # Disabled due to lxml issues
import html2text
import structlog

logger = structlog.get_logger(__name__)

class WebParser:
    """Parses web content from URLs"""
    
    def __init__(self):
        self.supported_formats = ['url', 'web', 'html']
        self.timeout = 30
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    async def parse(self, url: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Parse web content from URL"""
        
        if options is None:
            options = {}
        
        logger.info("Starting web parsing", url=url, options=options)
        
        try:
            # Fetch the web page
            html_content = await self._fetch_url(url, options)
            
            if not html_content:
                raise Exception("Failed to fetch content from URL")
            
            # Use multiple extraction methods
            newspaper_result = {"title": "", "content": "", "metadata": {}}  # Placeholder(url, html_content, options)
            readability_result = {"title": "", "content": "", "metadata": {}}  # await self._parse_with_readability(html_content, options)
            beautifulsoup_result = await self._parse_with_beautifulsoup(html_content, url, options)
            
            # Combine results for best extraction
            combined_result = {
                "title": (
                    newspaper_result.get("title") or 
                    readability_result.get("title") or 
                    beautifulsoup_result.get("title", "Web Document")
                ),
                "content": self._select_best_content([
                    newspaper_result.get("content", ""),
                    readability_result.get("content", ""),
                    beautifulsoup_result.get("content", "")
                ]),
                "metadata": {
                    **newspaper_result.get("metadata", {}),
                    **readability_result.get("metadata", {}),
                    **beautifulsoup_result.get("metadata", {}),
                    "url": url,
                    "extraction_methods": {
                        "newspaper": bool(newspaper_result.get("content")),
                        "readability": bool(readability_result.get("content")),
                        "beautifulsoup": bool(beautifulsoup_result.get("content"))
                    }
                },
                "structure": {
                    "links": beautifulsoup_result.get("structure", {}).get("links", []),
                    "images": beautifulsoup_result.get("structure", {}).get("images", []),
                    "headings": beautifulsoup_result.get("structure", {}).get("headings", []),
                    "tables": beautifulsoup_result.get("structure", {}).get("tables", [])
                },
                "stats": {
                    "word_count": 0,
                    "character_count": 0,
                    "link_count": len(beautifulsoup_result.get("structure", {}).get("links", [])),
                    "image_count": len(beautifulsoup_result.get("structure", {}).get("images", [])),
                    "heading_count": len(beautifulsoup_result.get("structure", {}).get("headings", []))
                }
            }
            
            # Calculate content stats
            content = combined_result["content"]
            combined_result["stats"]["word_count"] = len(content.split())
            combined_result["stats"]["character_count"] = len(content)
            
            logger.info("Web parsing completed successfully",
                       url=url,
                       word_count=combined_result["stats"]["word_count"],
                       title=combined_result["title"][:50])
            
            return combined_result
            
        except Exception as e:
            logger.error("Web parsing failed", url=url, error=str(e))
            return {
                "title": "Web Parsing Failed",
                "content": f"Error parsing URL {url}: {str(e)}",
                "metadata": {"url": url, "error": str(e)},
                "structure": {},
                "stats": {"error": True}
            }
    
    async def _fetch_url(self, url: str, options: Dict[str, Any]) -> str:
        """Fetch HTML content from URL"""
        
        headers = {
            "User-Agent": options.get("user_agent", self.user_agent),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        timeout = options.get("timeout", self.timeout)
        
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    logger.warning("Non-HTML content type detected", 
                                 url=url, 
                                 content_type=content_type)
                
                return response.text
                
            except httpx.TimeoutException:
                logger.error("Request timeout", url=url, timeout=timeout)
                raise Exception(f"Request timeout after {timeout} seconds")
            except httpx.HTTPStatusError as e:
                logger.error("HTTP error", url=url, status_code=e.response.status_code)
                raise Exception(f"HTTP {e.response.status_code}: {e.response.reason_phrase}")
            except Exception as e:
                logger.error("Failed to fetch URL", url=url, error=str(e))
                raise
    
    async def _parse_with_newspaper(self, url: str, html_content: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Parse using newspaper3k library"""
        
        try:
            article = newspaper.Article(url)
            article.set_html(html_content)
            article.parse()
            
            # Extract additional metadata
            metadata = {
                "authors": article.authors,
                "publish_date": article.publish_date.isoformat() if article.publish_date else None,
                "top_image": article.top_image,
                "movies": article.movies,
                "keywords": article.keywords if hasattr(article, 'keywords') else [],
                "summary": article.summary if hasattr(article, 'summary') else "",
                "parser": "newspaper3k"
            }
            
            # Try to extract keywords and summary if not already done
            try:
                if not metadata["keywords"]:
                    article.nlp()
                    metadata["keywords"] = article.keywords
                    metadata["summary"] = article.summary
            except Exception:
                pass  # NLP processing is optional
            
            return {
                "title": article.title,
                "content": article.text,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.warning("Newspaper parsing failed", url=url, error=str(e))
            return {"error": str(e)}
    
    async def _parse_with_readability(self, html_content: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Parse using readability-lxml library"""
        
        try:
            doc = Document(html_content)
            
            # Convert to markdown for cleaner text
            h = html2text.HTML2Text()
            h.ignore_links = options.get("ignore_links", False)
            h.ignore_images = options.get("ignore_images", False)
            h.body_width = 0  # Don't wrap lines
            
            content = h.handle(doc.content())
            
            return {
                "title": doc.title(),
                "content": content.strip(),
                "metadata": {
                    "parser": "readability",
                    "content_score": getattr(doc, 'content_score', 0)
                }
            }
            
        except Exception as e:
            logger.warning("Readability parsing failed", error=str(e))
            return {"error": str(e)}
    
    async def _parse_with_beautifulsoup(self, html_content: str, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Parse using BeautifulSoup for structure extraction"""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = ""
            if soup.title:
                title = soup.title.get_text().strip()
            elif soup.find('h1'):
                title = soup.find('h1').get_text().strip()
            
            # Extract main content
            content_text = self._extract_main_content(soup)
            
            # Extract structure elements
            links = self._extract_links(soup, url)
            images = self._extract_images(soup, url)
            headings = self._extract_headings(soup)
            tables = self._extract_tables(soup)
            
            # Extract metadata
            metadata = self._extract_meta_tags(soup)
            metadata["parser"] = "beautifulsoup"
            
            return {
                "title": title,
                "content": content_text,
                "metadata": metadata,
                "structure": {
                    "links": links,
                    "images": images,
                    "headings": headings,
                    "tables": tables
                }
            }
            
        except Exception as e:
            logger.warning("BeautifulSoup parsing failed", error=str(e))
            return {"error": str(e)}
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content text from soup"""
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Try to find main content areas
        main_content = None
        for selector in ["main", "article", ".content", "#content", ".post", ".entry"]:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # Fall back to body if no main content found
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Extract text
        text = main_content.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract links from soup"""
        
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            links.append({
                "text": link.get_text().strip(),
                "url": absolute_url,
                "title": link.get('title', ''),
                "is_external": urlparse(absolute_url).netloc != urlparse(base_url).netloc
            })
        
        return links
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract images from soup"""
        
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, src)
            
            images.append({
                "url": absolute_url,
                "alt": img.get('alt', ''),
                "title": img.get('title', ''),
                "width": img.get('width'),
                "height": img.get('height')
            })
        
        return images
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract headings from soup"""
        
        headings = []
        for level in range(1, 7):  # h1 to h6
            for heading in soup.find_all(f'h{level}'):
                headings.append({
                    "level": level,
                    "text": heading.get_text().strip(),
                    "id": heading.get('id', '')
                })
        
        return headings
    
    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract tables from soup"""
        
        tables = []
        for table_idx, table in enumerate(soup.find_all('table')):
            rows = []
            for row in table.find_all('tr'):
                cells = [cell.get_text().strip() for cell in row.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            
            if rows:
                tables.append({
                    "index": table_idx,
                    "rows": len(rows),
                    "columns": len(rows[0]) if rows else 0,
                    "data": rows if len(rows) <= 100 else rows[:100]  # Limit large tables
                })
        
        return tables
    
    def _extract_meta_tags(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata from meta tags"""
        
        metadata = {}
        
        # Standard meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property') or meta.get('http-equiv')
            content = meta.get('content')
            
            if name and content:
                metadata[name.lower()] = content
        
        # Open Graph tags
        og_tags = {}
        for meta in soup.find_all('meta', property=lambda x: x and x.startswith('og:')):
            property_name = meta.get('property')[3:]  # Remove 'og:' prefix
            og_tags[property_name] = meta.get('content')
        
        if og_tags:
            metadata['open_graph'] = og_tags
        
        # Twitter Card tags
        twitter_tags = {}
        for meta in soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')}):
            name = meta.get('name')[8:]  # Remove 'twitter:' prefix
            twitter_tags[name] = meta.get('content')
        
        if twitter_tags:
            metadata['twitter_card'] = twitter_tags
        
        return metadata
    
    def _select_best_content(self, content_options: List[str]) -> str:
        """Select the best content from multiple extraction methods"""
        
        # Filter out empty content
        valid_content = [content for content in content_options if content and content.strip()]
        
        if not valid_content:
            return ""
        
        # Select the longest content as it's likely the most complete
        return max(valid_content, key=len)
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported formats"""
        return self.supported_formats 