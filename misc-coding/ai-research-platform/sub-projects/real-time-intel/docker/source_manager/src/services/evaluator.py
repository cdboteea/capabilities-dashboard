"""
Source Evaluator Service

LLM-based source evaluation with comprehensive quality assessment.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse
import re
import json

import httpx
import feedparser
from bs4 import BeautifulSoup
import tldextract
import textstat
import whois

from ..models.source_models import (
    Source, SourceEvaluation, SourceType, SourceQuality, SourceStatus,
    DomainAuthority, ContentAnalysis, BiasAssessment, QualityScore,
    RSSFeedInfo, ContentCategory, BiasDirection
)
from ..utils.database import DatabaseManager


logger = logging.getLogger(__name__)


class SourceEvaluator:
    """
    Comprehensive source evaluation service using LLM analysis and heuristics.
    """
    
    def __init__(self, db_manager: DatabaseManager, llm_endpoint: str, llm_model: str):
        self.db = db_manager
        self.llm_endpoint = llm_endpoint
        self.llm_model = llm_model
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Evaluation cache
        self._evaluation_cache: Dict[str, SourceEvaluation] = {}
        self._cache_ttl = 3600  # 1 hour
        
        # Quality scoring weights (from config)
        self.weights = {
            'domain_authority': 0.25,
            'content_quality': 0.30,
            'bias_assessment': 0.20,
            'reliability_score': 0.15,
            'freshness_factor': 0.10
        }
        
        # Known high-quality domains for baseline scoring
        self.trusted_domains = {
            'reuters.com': 0.95,
            'bbc.com': 0.92,
            'ap.org': 0.94,
            'bloomberg.com': 0.90,
            'wsj.com': 0.91,
            'ft.com': 0.89,
            'economist.com': 0.88,
            'npr.org': 0.87
        }
        
    async def evaluate_source(
        self, 
        url: str, 
        source_type: Optional[SourceType] = None,
        force_reevaluation: bool = False,
        sample_articles: int = 10
    ) -> Tuple[Source, SourceEvaluation]:
        """
        Perform comprehensive source evaluation.
        
        Args:
            url: Source URL to evaluate
            source_type: Hint for source type
            force_reevaluation: Force new evaluation even if cached
            sample_articles: Number of articles to analyze
            
        Returns:
            Tuple of (Source, SourceEvaluation)
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"{url}:{sample_articles}"
            if not force_reevaluation and cache_key in self._evaluation_cache:
                cached_eval = self._evaluation_cache[cache_key]
                if datetime.now(timezone.utc) - cached_eval.created_at < timedelta(seconds=self._cache_ttl):
                    logger.info(f"Using cached evaluation for {url}")
                    source = await self._get_or_create_source(url, source_type)
                    return source, cached_eval
            
            # Perform evaluation
            logger.info(f"Starting evaluation for {url}")
            
            # Step 1: Basic source information
            source = await self._get_or_create_source(url, source_type)
            
            # Step 2: Domain authority analysis
            domain_authority = await self._analyze_domain_authority(source.domain)
            
            # Step 3: Content analysis
            content_analysis = await self._analyze_content_quality(url, sample_articles)
            
            # Step 4: Bias assessment using LLM
            bias_assessment = await self._assess_bias_with_llm(url, sample_articles)
            
            # Step 5: Calculate overall quality score
            quality_score = self._calculate_quality_score(
                domain_authority, content_analysis, bias_assessment
            )
            
            # Create evaluation record
            evaluation = SourceEvaluation(
                source_id=source.id,
                domain_authority=domain_authority,
                content_analysis=content_analysis,
                bias_assessment=bias_assessment,
                quality_score=quality_score,
                evaluation_method="llm_enhanced_heuristic",
                llm_model=self.llm_model,
                sample_articles_analyzed=sample_articles,
                evaluation_duration_seconds=time.time() - start_time,
                recommendations=self._generate_recommendations(quality_score, bias_assessment),
                warnings=self._generate_warnings(quality_score, bias_assessment)
            )
            
            # Cache the evaluation
            self._evaluation_cache[cache_key] = evaluation
            
            # Update source status based on evaluation
            source.status = self._determine_source_status(quality_score)
            source.last_evaluated_at = datetime.now(timezone.utc)
            
            # Save to database
            await self.db.save_source_evaluation(source, evaluation)
            
            logger.info(f"Completed evaluation for {url} in {evaluation.evaluation_duration_seconds:.2f}s")
            return source, evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating source {url}: {str(e)}")
            raise
    
    async def _get_or_create_source(self, url: str, source_type: Optional[SourceType] = None) -> Source:
        """Get existing source or create new one."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Try to get existing source
        existing_source = await self.db.get_source_by_url(url)
        if existing_source:
            return existing_source
        
        # Detect source type if not provided
        if not source_type:
            source_type = await self._detect_source_type(url)
        
        # Detect primary category
        primary_category = await self._detect_primary_category(url)
        
        # Get RSS feed info if applicable
        rss_feed_info = None
        if source_type == SourceType.RSS_FEED:
            rss_feed_info = await self._analyze_rss_feed(url)
        
        # Create new source
        source = Source(
            name=self._extract_site_name(domain),
            url=url,
            domain=domain,
            source_type=source_type,
            primary_category=primary_category,
            rss_feed_info=rss_feed_info,
            status=SourceStatus.PENDING_EVALUATION
        )
        
        return source
    
    async def _analyze_domain_authority(self, domain: str) -> DomainAuthority:
        """Analyze domain authority and reputation metrics."""
        try:
            # Check if it's a known trusted domain
            trust_score = self.trusted_domains.get(domain, 0.5)
            
            # Basic domain analysis
            domain_info = tldextract.extract(domain)
            
            # Estimate authority score based on domain characteristics
            authority_score = 50.0  # Base score
            
            # Adjust based on domain characteristics
            if domain in self.trusted_domains:
                authority_score = self.trusted_domains[domain] * 100
            elif domain_info.suffix in ['.edu', '.gov']:
                authority_score = 85.0
                trust_score = 0.9
            elif domain_info.suffix in ['.org']:
                authority_score = 70.0
                trust_score = 0.75
            elif domain_info.suffix in ['.com', '.net']:
                authority_score = 60.0
                trust_score = 0.6
            
            # Check SSL certificate
            ssl_certificate = await self._check_ssl_certificate(f"https://{domain}")
            if ssl_certificate:
                authority_score += 10
                trust_score += 0.1
            
            # Estimate domain age (simplified)
            domain_age_years = None
            try:
                w = whois.whois(domain)
                if w.creation_date:
                    if isinstance(w.creation_date, list):
                        creation_date = w.creation_date[0]
                    else:
                        creation_date = w.creation_date
                    domain_age_years = (datetime.now() - creation_date).days / 365.25
                    
                    # Older domains get bonus points
                    if domain_age_years > 10:
                        authority_score += 15
                        trust_score += 0.15
                    elif domain_age_years > 5:
                        authority_score += 10
                        trust_score += 0.1
            except:
                pass  # WHOIS lookup failed
            
            # Calculate spam score (inverse of trust)
            spam_score = max(0, 1 - trust_score)
            
            return DomainAuthority(
                domain=domain,
                authority_score=min(100, authority_score),
                trust_score=min(1.0, trust_score),
                spam_score=spam_score,
                ssl_certificate=ssl_certificate,
                domain_age_years=domain_age_years
            )
            
        except Exception as e:
            logger.error(f"Error analyzing domain authority for {domain}: {str(e)}")
            # Return default values
            return DomainAuthority(
                domain=domain,
                authority_score=50.0,
                trust_score=0.5,
                spam_score=0.5,
                ssl_certificate=False
            )
    
    async def _analyze_content_quality(self, url: str, sample_size: int) -> ContentAnalysis:
        """Analyze content quality by sampling articles."""
        try:
            articles = await self._sample_articles(url, sample_size)
            
            if not articles:
                logger.warning(f"No articles found for content analysis: {url}")
                return self._default_content_analysis()
            
            # Analyze article characteristics
            total_length = sum(len(article['content']) for article in articles)
            avg_length = total_length / len(articles)
            
            # Calculate readability scores
            readability_scores = []
            grammar_scores = []
            
            for article in articles:
                content = article['content']
                if len(content) > 100:  # Minimum content for analysis
                    # Flesch Reading Ease
                    readability = textstat.flesch_reading_ease(content)
                    readability_scores.append(max(0, min(100, readability)))
                    
                    # Simple grammar quality (based on sentence structure)
                    grammar_score = self._assess_grammar_quality(content)
                    grammar_scores.append(grammar_score)
            
            avg_readability = sum(readability_scores) / len(readability_scores) if readability_scores else 50
            avg_grammar = sum(grammar_scores) / len(grammar_scores) if grammar_scores else 0.5
            
            # Assess other quality metrics
            citation_frequency = self._assess_citation_frequency(articles)
            content_depth = self._assess_content_depth(articles)
            multimedia_usage = self._assess_multimedia_usage(articles)
            
            # Estimate update frequency (simplified)
            update_frequency = len(articles) / 7  # Assume articles from last week
            
            # Factual accuracy (simplified heuristic)
            factual_accuracy = self._assess_factual_accuracy(articles)
            
            return ContentAnalysis(
                avg_article_length=int(avg_length),
                readability_score=avg_readability,
                grammar_quality=avg_grammar,
                factual_accuracy=factual_accuracy,
                citation_frequency=citation_frequency,
                update_frequency=update_frequency,
                content_depth=content_depth,
                multimedia_usage=multimedia_usage
            )
            
        except Exception as e:
            logger.error(f"Error analyzing content quality for {url}: {str(e)}")
            return self._default_content_analysis()
    
    async def _assess_bias_with_llm(self, url: str, sample_size: int) -> BiasAssessment:
        """Use LLM to assess political bias and reliability."""
        try:
            articles = await self._sample_articles(url, min(sample_size, 5))  # Limit for LLM analysis
            
            if not articles:
                return self._default_bias_assessment()
            
            # Prepare content for LLM analysis
            content_sample = "\n\n".join([
                f"Article {i+1}: {article['title']}\n{article['content'][:1000]}..."
                for i, article in enumerate(articles[:3])  # Use top 3 articles
            ])
            
            # LLM prompt for bias assessment
            prompt = f"""
            Analyze the following news content for political bias and reliability. Provide a JSON response with the following structure:

            {{
                "political_bias": "left|center_left|center|center_right|right|unknown",
                "bias_strength": 0.0-1.0,
                "factual_reporting": 0.0-1.0,
                "sensationalism_score": 0.0-1.0,
                "transparency_score": 0.0-1.0,
                "source_attribution": 0.0-1.0,
                "reasoning": "Brief explanation of assessment"
            }}

            Content to analyze:
            {content_sample}
            
            Consider:
            - Language tone and word choice
            - Presentation of multiple viewpoints
            - Use of loaded language or emotional appeals
            - Quality of source attribution
            - Factual accuracy and verification
            """
            
            # Call LLM
            llm_response = await self._call_llm(prompt)
            
            # Parse LLM response
            try:
                bias_data = json.loads(llm_response)
                
                return BiasAssessment(
                    political_bias=BiasDirection(bias_data.get('political_bias', 'unknown')),
                    bias_strength=float(bias_data.get('bias_strength', 0.5)),
                    factual_reporting=float(bias_data.get('factual_reporting', 0.5)),
                    sensationalism_score=float(bias_data.get('sensationalism_score', 0.5)),
                    transparency_score=float(bias_data.get('transparency_score', 0.5)),
                    correction_policy=self._check_correction_policy(url),
                    source_attribution=float(bias_data.get('source_attribution', 0.5))
                )
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Error parsing LLM bias assessment: {str(e)}")
                return self._default_bias_assessment()
                
        except Exception as e:
            logger.error(f"Error in LLM bias assessment for {url}: {str(e)}")
            return self._default_bias_assessment()
    
    async def _call_llm(self, prompt: str) -> str:
        """Call Mac Studio LLM endpoint."""
        try:
            payload = {
                "model": self.llm_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            }
            
            response = await self.http_client.post(
                f"{self.llm_endpoint}/chat/completions",
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise
    
    def _calculate_quality_score(
        self,
        domain_authority: DomainAuthority,
        content_analysis: ContentAnalysis,
        bias_assessment: BiasAssessment
    ) -> QualityScore:
        """Calculate overall quality score from component assessments."""
        
        # Normalize domain authority (0-100 to 0-1)
        domain_score = domain_authority.authority_score / 100.0
        
        # Content quality composite score
        content_score = (
            (content_analysis.readability_score / 100.0) * 0.2 +
            content_analysis.grammar_quality * 0.25 +
            content_analysis.factual_accuracy * 0.25 +
            content_analysis.citation_frequency * 0.15 +
            content_analysis.content_depth * 0.15
        )
        
        # Bias score (lower bias = higher score)
        bias_score = (
            bias_assessment.factual_reporting * 0.4 +
            (1 - bias_assessment.sensationalism_score) * 0.3 +
            bias_assessment.transparency_score * 0.3
        )
        
        # Reliability score
        reliability_score = (
            domain_authority.trust_score * 0.5 +
            bias_assessment.factual_reporting * 0.3 +
            content_analysis.factual_accuracy * 0.2
        )
        
        # Freshness score (based on update frequency)
        freshness_score = min(1.0, content_analysis.update_frequency / 5.0)  # Normalize to daily updates
        
        # Calculate weighted overall score
        overall_score = (
            domain_score * self.weights['domain_authority'] +
            content_score * self.weights['content_quality'] +
            bias_score * self.weights['bias_assessment'] +
            reliability_score * self.weights['reliability_score'] +
            freshness_score * self.weights['freshness_factor']
        )
        
        # Determine quality rating
        if overall_score >= 0.85:
            quality_rating = SourceQuality.EXCELLENT
        elif overall_score >= 0.70:
            quality_rating = SourceQuality.GOOD
        elif overall_score >= 0.55:
            quality_rating = SourceQuality.ACCEPTABLE
        elif overall_score >= 0.40:
            quality_rating = SourceQuality.POOR
        else:
            quality_rating = SourceQuality.UNRELIABLE
        
        # Calculate confidence based on data availability
        confidence = min(1.0, (
            (1.0 if domain_authority.domain_age_years else 0.7) +
            (1.0 if content_analysis.avg_article_length > 500 else 0.5) +
            (1.0 if bias_assessment.political_bias != BiasDirection.UNKNOWN else 0.3)
        ) / 3.0)
        
        return QualityScore(
            overall_score=overall_score,
            domain_authority_score=domain_score,
            content_quality_score=content_score,
            bias_score=bias_score,
            reliability_score=reliability_score,
            freshness_score=freshness_score,
            confidence=confidence,
            quality_rating=quality_rating
        )
    
    # Helper methods (simplified implementations)
    
    async def _sample_articles(self, url: str, count: int) -> List[Dict[str, Any]]:
        """Sample recent articles from the source."""
        try:
            # Try RSS feed first
            feed = feedparser.parse(url)
            if feed.entries:
                articles = []
                for entry in feed.entries[:count]:
                    content = await self._extract_article_content(entry.link)
                    articles.append({
                        'title': entry.title,
                        'content': content,
                        'url': entry.link
                    })
                return articles
            
            # Fallback to web scraping (simplified)
            response = await self.http_client.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract article links (simplified heuristic)
            links = soup.find_all('a', href=True)
            article_links = [link['href'] for link in links if self._looks_like_article_url(link['href'])]
            
            articles = []
            for link in article_links[:count]:
                if not link.startswith('http'):
                    link = f"{urlparse(url).scheme}://{urlparse(url).netloc}{link}"
                
                content = await self._extract_article_content(link)
                if content:
                    articles.append({
                        'title': soup.find('title').text if soup.find('title') else '',
                        'content': content,
                        'url': link
                    })
            
            return articles
            
        except Exception as e:
            logger.error(f"Error sampling articles from {url}: {str(e)}")
            return []
    
    async def _extract_article_content(self, url: str) -> str:
        """Extract main content from article URL."""
        try:
            response = await self.http_client.get(url, timeout=10.0)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find main content (simplified heuristic)
            content_selectors = [
                'article', '.article-content', '.post-content', 
                '.entry-content', 'main', '.content'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    return content_elem.get_text(strip=True)
            
            # Fallback to body text
            return soup.get_text(strip=True)[:5000]  # Limit content length
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return ""
    
    def _looks_like_article_url(self, url: str) -> bool:
        """Heuristic to identify article URLs."""
        article_patterns = [
            r'/\d{4}/\d{2}/\d{2}/',  # Date-based URLs
            r'/article/',
            r'/news/',
            r'/post/',
            r'/story/',
            r'/blog/'
        ]
        
        return any(re.search(pattern, url) for pattern in article_patterns)
    
    async def _detect_source_type(self, url: str) -> SourceType:
        """Detect source type from URL and content."""
        try:
            # Check if it's an RSS feed
            if url.endswith('.xml') or 'rss' in url.lower() or 'feed' in url.lower():
                return SourceType.RSS_FEED
            
            # Check domain patterns
            domain = urlparse(url).netloc.lower()
            
            if any(keyword in domain for keyword in ['blog', 'blogger', 'wordpress']):
                return SourceType.BLOG
            elif any(keyword in domain for keyword in ['gov', 'government']):
                return SourceType.GOVERNMENT
            elif any(keyword in domain for keyword in ['edu', 'university', 'academic']):
                return SourceType.ACADEMIC
            elif any(keyword in domain for keyword in ['finance', 'financial', 'bloomberg', 'reuters']):
                return SourceType.FINANCIAL_PORTAL
            else:
                return SourceType.NEWS_WEBSITE
                
        except Exception:
            return SourceType.OTHER
    
    async def _detect_primary_category(self, url: str) -> ContentCategory:
        """Detect primary content category."""
        domain = urlparse(url).netloc.lower()
        
        # Simple keyword-based detection
        if any(keyword in domain for keyword in ['business', 'finance', 'economic']):
            return ContentCategory.BUSINESS
        elif any(keyword in domain for keyword in ['tech', 'technology']):
            return ContentCategory.TECHNOLOGY
        elif any(keyword in domain for keyword in ['politics', 'political']):
            return ContentCategory.POLITICS
        elif any(keyword in domain for keyword in ['health', 'medical']):
            return ContentCategory.HEALTH
        elif any(keyword in domain for keyword in ['science']):
            return ContentCategory.SCIENCE
        else:
            return ContentCategory.GENERAL
    
    async def _analyze_rss_feed(self, url: str) -> Optional[RSSFeedInfo]:
        """Analyze RSS feed information."""
        try:
            feed = feedparser.parse(url)
            
            if not feed.entries:
                return None
            
            return RSSFeedInfo(
                feed_url=url,
                title=feed.feed.get('title'),
                description=feed.feed.get('description'),
                language=feed.feed.get('language'),
                last_build_date=datetime.now(timezone.utc),  # Simplified
                item_count=len(feed.entries),
                is_valid=True
            )
            
        except Exception as e:
            return RSSFeedInfo(
                feed_url=url,
                item_count=0,
                is_valid=False,
                error_message=str(e)
            )
    
    async def _check_ssl_certificate(self, url: str) -> bool:
        """Check if site has valid SSL certificate."""
        try:
            response = await self.http_client.get(url, timeout=5.0)
            return response.url.scheme == 'https'
        except:
            return False
    
    def _extract_site_name(self, domain: str) -> str:
        """Extract readable site name from domain."""
        domain_info = tldextract.extract(domain)
        return domain_info.domain.title()
    
    def _assess_grammar_quality(self, text: str) -> float:
        """Simple grammar quality assessment."""
        # Count basic grammar issues (simplified)
        sentences = text.split('.')
        if not sentences:
            return 0.5
        
        issues = 0
        total_checks = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
                
            total_checks += 1
            
            # Check for basic issues
            if not sentence[0].isupper():
                issues += 1
            if sentence.count('  ') > 0:  # Double spaces
                issues += 1
            if len(sentence.split()) < 3:  # Very short sentences
                issues += 1
        
        if total_checks == 0:
            return 0.5
        
        return max(0, 1 - (issues / total_checks))
    
    def _assess_citation_frequency(self, articles: List[Dict[str, Any]]) -> float:
        """Assess how frequently articles cite sources."""
        if not articles:
            return 0.0
        
        citation_indicators = ['according to', 'sources say', 'reported by', 'citing', 'quoted']
        articles_with_citations = 0
        
        for article in articles:
            content = article['content'].lower()
            if any(indicator in content for indicator in citation_indicators):
                articles_with_citations += 1
        
        return articles_with_citations / len(articles)
    
    def _assess_content_depth(self, articles: List[Dict[str, Any]]) -> float:
        """Assess content depth and analysis quality."""
        if not articles:
            return 0.0
        
        depth_indicators = ['analysis', 'background', 'context', 'explanation', 'expert']
        total_score = 0
        
        for article in articles:
            content = article['content'].lower()
            score = sum(1 for indicator in depth_indicators if indicator in content)
            total_score += min(1.0, score / len(depth_indicators))
        
        return total_score / len(articles)
    
    def _assess_multimedia_usage(self, articles: List[Dict[str, Any]]) -> float:
        """Assess multimedia usage in articles."""
        # Simplified - would need actual HTML parsing
        return 0.5  # Default assumption
    
    def _assess_factual_accuracy(self, articles: List[Dict[str, Any]]) -> float:
        """Assess factual accuracy (simplified heuristic)."""
        if not articles:
            return 0.5
        
        # Look for fact-checking indicators
        accuracy_indicators = ['verified', 'confirmed', 'fact-check', 'sources confirm']
        inaccuracy_indicators = ['alleged', 'rumored', 'unconfirmed', 'speculation']
        
        accuracy_score = 0
        for article in articles:
            content = article['content'].lower()
            
            accuracy_count = sum(1 for indicator in accuracy_indicators if indicator in content)
            inaccuracy_count = sum(1 for indicator in inaccuracy_indicators if indicator in content)
            
            if accuracy_count > inaccuracy_count:
                accuracy_score += 0.8
            elif inaccuracy_count > accuracy_count:
                accuracy_score += 0.3
            else:
                accuracy_score += 0.5
        
        return accuracy_score / len(articles)
    
    def _check_correction_policy(self, url: str) -> bool:
        """Check if site has visible correction policy."""
        # Simplified - would need to check for correction/ethics pages
        domain = urlparse(url).netloc.lower()
        return domain in self.trusted_domains
    
    def _determine_source_status(self, quality_score: QualityScore) -> SourceStatus:
        """Determine source status based on quality score."""
        if quality_score.overall_score >= 0.7:
            return SourceStatus.ACTIVE
        elif quality_score.overall_score >= 0.4:
            return SourceStatus.UNDER_REVIEW
        else:
            return SourceStatus.SUSPENDED
    
    def _generate_recommendations(self, quality_score: QualityScore, bias_assessment: BiasAssessment) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        if quality_score.content_quality_score < 0.6:
            recommendations.append("Improve content quality with better research and writing")
        
        if bias_assessment.bias_strength > 0.7:
            recommendations.append("Reduce editorial bias and present multiple viewpoints")
        
        if bias_assessment.source_attribution < 0.5:
            recommendations.append("Improve source attribution and citation practices")
        
        if quality_score.freshness_score < 0.3:
            recommendations.append("Increase update frequency for more timely content")
        
        return recommendations
    
    def _generate_warnings(self, quality_score: QualityScore, bias_assessment: BiasAssessment) -> List[str]:
        """Generate quality warnings."""
        warnings = []
        
        if quality_score.overall_score < 0.4:
            warnings.append("Low overall quality score - use with caution")
        
        if bias_assessment.sensationalism_score > 0.7:
            warnings.append("High sensationalism detected")
        
        if bias_assessment.factual_reporting < 0.5:
            warnings.append("Poor factual reporting quality")
        
        return warnings
    
    def _default_content_analysis(self) -> ContentAnalysis:
        """Return default content analysis for error cases."""
        return ContentAnalysis(
            avg_article_length=1000,
            readability_score=50.0,
            grammar_quality=0.5,
            factual_accuracy=0.5,
            citation_frequency=0.3,
            update_frequency=1.0,
            content_depth=0.5,
            multimedia_usage=0.3
        )
    
    def _default_bias_assessment(self) -> BiasAssessment:
        """Return default bias assessment for error cases."""
        return BiasAssessment(
            political_bias=BiasDirection.UNKNOWN,
            bias_strength=0.5,
            factual_reporting=0.5,
            sensationalism_score=0.5,
            transparency_score=0.5,
            correction_policy=False,
            source_attribution=0.5
        )
    
    async def close(self):
        """Clean up resources."""
        await self.http_client.aclose() 