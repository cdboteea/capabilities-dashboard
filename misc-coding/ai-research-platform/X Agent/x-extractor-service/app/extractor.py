"""Core content extraction logic for X (Twitter) posts."""

import re
import asyncio
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
from bs4 import BeautifulSoup
import structlog

from .models import PostContent, Author, Engagement, UrlInfo, MediaItem, ReferencedDocument
from .config import settings

logger = structlog.get_logger()


class XPostExtractor:
    """Extractor for X (Twitter) post content."""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': settings.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(
            headers=self.headers,
            timeout=httpx.Timeout(settings.request_timeout),
            follow_redirects=True
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    def normalize_url(self, url: str) -> str:
        """Normalize X/Twitter URL to standard format."""
        # Handle both x.com and twitter.com domains
        url = url.replace('twitter.com', 'x.com')
        
        # Extract post ID from URL
        match = re.search(r'/status/(\d+)', url)
        if match:
            post_id = match.group(1)
            # Remove query parameters and fragments
            base_url = url.split('?')[0].split('#')[0]
            return base_url
        
        return url
    
    def extract_post_id(self, url: str) -> Optional[str]:
        """Extract post ID from X URL."""
        match = re.search(r'/status/(\d+)', url)
        return match.group(1) if match else None
    
    async def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch page content from URL."""
        try:
            response = await self.session.get(url)
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            logger.error("Request error", url=url, error=str(e))
            return None
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error", url=url, status_code=e.response.status_code)
            return None
    
    def parse_engagement_metrics(self, soup: BeautifulSoup) -> Engagement:
        """Parse engagement metrics from page content."""
        engagement = Engagement()
        
        try:
            # Look for engagement metrics in various possible locations
            # This is a simplified approach - real implementation would need more robust parsing
            
            # Try to find metrics in data attributes or aria-labels
            like_elements = soup.find_all(attrs={'data-testid': re.compile(r'like|favorite')})
            retweet_elements = soup.find_all(attrs={'data-testid': re.compile(r'retweet')})
            reply_elements = soup.find_all(attrs={'data-testid': re.compile(r'reply')})
            
            # Extract numbers from text content
            for element in like_elements:
                text = element.get_text(strip=True)
                numbers = re.findall(r'(\d+(?:,\d+)*)', text)
                if numbers:
                    engagement.likes = int(numbers[0].replace(',', ''))
                    break
            
            for element in retweet_elements:
                text = element.get_text(strip=True)
                numbers = re.findall(r'(\d+(?:,\d+)*)', text)
                if numbers:
                    engagement.retweets = int(numbers[0].replace(',', ''))
                    break
            
            for element in reply_elements:
                text = element.get_text(strip=True)
                numbers = re.findall(r'(\d+(?:,\d+)*)', text)
                if numbers:
                    engagement.replies = int(numbers[0].replace(',', ''))
                    break
                    
        except Exception as e:
            logger.warning("Error parsing engagement metrics", error=str(e))
        
        return engagement
    
    def extract_urls_from_text(self, text: str) -> List[UrlInfo]:
        """Extract URLs from post text."""
        urls = []
        
        # Find URLs in text
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        found_urls = re.findall(url_pattern, text)
        
        for url in found_urls:
            urls.append(UrlInfo(
                display_url=url,
                expanded_url=url,  # Would need to expand t.co links in real implementation
                title=None,
                description=None
            ))
        
        return urls
    
    def extract_hashtags_and_mentions(self, text: str) -> tuple[List[str], List[str]]:
        """Extract hashtags and mentions from post text."""
        hashtags = re.findall(r'#(\w+)', text)
        mentions = re.findall(r'@(\w+)', text)
        return hashtags, mentions
    
    def parse_media_items(self, soup: BeautifulSoup) -> List[MediaItem]:
        """Parse media items from page content."""
        media_items = []
        
        try:
            # Look for images
            img_elements = soup.find_all('img', src=True)
            for img in img_elements:
                src = img.get('src', '')
                if 'pbs.twimg.com' in src or 'media' in src:
                    media_items.append(MediaItem(
                        type='image',
                        url=src,
                        alt_text=img.get('alt', ''),
                        width=None,
                        height=None
                    ))
            
            # Look for videos
            video_elements = soup.find_all('video', src=True)
            for video in video_elements:
                src = video.get('src', '')
                media_items.append(MediaItem(
                    type='video',
                    url=src,
                    alt_text=None,
                    width=None,
                    height=None
                ))
                
        except Exception as e:
            logger.warning("Error parsing media items", error=str(e))
        
        return media_items
    
    def extract_referenced_documents(self, urls: List[UrlInfo]) -> List[ReferencedDocument]:
        """Extract referenced documents from URLs."""
        documents = []
        
        for url_info in urls:
            url = url_info.expanded_url
            
            # Check for common document types
            if any(ext in url.lower() for ext in ['.pdf', '.doc', '.docx', '.ppt', '.pptx']):
                doc_type = 'PDF' if '.pdf' in url.lower() else 'Document'
                documents.append(ReferencedDocument(
                    url=url,
                    type=doc_type,
                    title=url_info.title,
                    description=url_info.description
                ))
            elif 'docs.google.com' in url:
                documents.append(ReferencedDocument(
                    url=url,
                    type='Google Doc',
                    title=url_info.title,
                    description=url_info.description
                ))
        
        return documents
    
    async def extract_post_content(self, url: str) -> Optional[PostContent]:
        """Extract content from a single X post URL."""
        try:
            normalized_url = self.normalize_url(url)
            post_id = self.extract_post_id(normalized_url)
            
            if not post_id:
                logger.error("Could not extract post ID from URL", url=url)
                return None
            
            # Fetch page content
            html_content = await self.fetch_page_content(normalized_url)
            if not html_content:
                return None
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract basic post information
            # This is a simplified extraction - real implementation would need more robust parsing
            
            # Try to find the main tweet content
            tweet_text = ""
            content_elements = soup.find_all(attrs={'data-testid': 'tweetText'})
            if content_elements:
                tweet_text = content_elements[0].get_text(strip=True)
            else:
                # Fallback: look for text in meta tags
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    tweet_text = meta_desc.get('content', '')
            
            # Extract author information
            author_name = "Unknown"
            author_username = "unknown"
            
            # Look for author info in meta tags or page title
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text()
                # Extract username from title like "Username (@username) / X"
                match = re.search(r'(.+?) \\(@(.+?)\\)', title_text)
                if match:
                    author_name = match.group(1).strip()
                    author_username = match.group(2).strip()
            
            author = Author(
                username=author_username,
                display_name=author_name,
                verified=False  # Would need to check for verification badge
            )
            
            # Parse engagement metrics
            engagement = self.parse_engagement_metrics(soup)
            
            # Extract URLs from text
            urls = self.extract_urls_from_text(tweet_text)
            
            # Extract hashtags and mentions
            hashtags, mentions = self.extract_hashtags_and_mentions(tweet_text)
            
            # Parse media items
            media = self.parse_media_items(soup)
            
            # Extract referenced documents
            referenced_docs = self.extract_referenced_documents(urls)
            
            # Create timestamp (simplified - would need better parsing)
            timestamp = datetime.now()
            
            return PostContent(
                post_url=normalized_url,
                post_id=post_id,
                author=author,
                content=tweet_text,
                timestamp=timestamp,
                engagement=engagement,
                urls=urls,
                media=media,
                referenced_documents=referenced_docs,
                hashtags=hashtags,
                mentions=mentions,
                is_reply=False,  # Would need to detect reply status
                is_retweet=False  # Would need to detect retweet status
            )
            
        except Exception as e:
            logger.error("Error extracting post content", url=url, error=str(e))
            return None
    
    async def extract_multiple_posts(self, urls: List[str]) -> List[PostContent]:
        """Extract content from multiple X post URLs concurrently."""
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        
        async def extract_with_semaphore(url: str) -> Optional[PostContent]:
            async with semaphore:
                return await self.extract_post_content(url)
        
        tasks = [extract_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        posts = []
        for result in results:
            if isinstance(result, PostContent):
                posts.append(result)
            elif isinstance(result, Exception):
                logger.error("Exception during extraction", error=str(result))
        
        return posts


async def expand_shortened_url(url: str) -> str:
    """Expand shortened URLs (like t.co links)."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            response = await client.head(url)
            return str(response.url)
    except Exception:
        return url  # Return original URL if expansion fails

