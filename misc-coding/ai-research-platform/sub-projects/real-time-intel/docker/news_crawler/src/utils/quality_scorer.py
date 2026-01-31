"""
Quality Scorer for News Articles

Evaluates the quality of news articles based on multiple factors.
"""

from typing import Dict, Any, Optional
import re
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class QualityScorer:
    """Score news article quality based on various factors."""
    
    def __init__(self):
        # Quality scoring weights
        self.weights = {
            'content_length': 0.15,
            'source_reputation': 0.25,
            'recency': 0.15,
            'readability': 0.10,
            'metadata_completeness': 0.10,
            'url_quality': 0.10,
            'content_structure': 0.15
        }
    
    def score_article(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score an article based on multiple quality factors.
        
        Args:
            article_data: Dictionary containing article information
            
        Returns:
            Dictionary with quality score and breakdown
        """
        try:
            scores = {}
            
            # Content length scoring
            scores['content_length'] = self._score_content_length(
                article_data.get('content', ''),
                article_data.get('title', '')
            )
            
            # Source reputation scoring
            scores['source_reputation'] = self._score_source_reputation(
                article_data.get('source_url', ''),
                article_data.get('source_name', '')
            )
            
            # Recency scoring
            scores['recency'] = self._score_recency(
                article_data.get('published_date')
            )
            
            # Readability scoring
            scores['readability'] = self._score_readability(
                article_data.get('content', '')
            )
            
            # Metadata completeness
            scores['metadata_completeness'] = self._score_metadata_completeness(
                article_data
            )
            
            # URL quality
            scores['url_quality'] = self._score_url_quality(
                article_data.get('url', '')
            )
            
            # Content structure
            scores['content_structure'] = self._score_content_structure(
                article_data.get('content', ''),
                article_data.get('title', '')
            )
            
            # Calculate weighted overall score
            overall_score = sum(
                scores[factor] * self.weights[factor]
                for factor in self.weights.keys()
            )
            
            return {
                'overall_score': round(overall_score, 3),
                'factor_scores': scores,
                'quality_tier': self._get_quality_tier(overall_score),
                'recommendations': self._get_recommendations(scores)
            }
            
        except Exception as e:
            logger.error(f"Quality scoring failed: {e}")
            return {
                'overall_score': 0.5,
                'factor_scores': {},
                'quality_tier': 'medium',
                'recommendations': ['Error in quality assessment']
            }
    
    def _score_content_length(self, content: str, title: str) -> float:
        """Score based on content length appropriateness."""
        word_count = len(content.split()) + len(title.split())
        
        if word_count < 50:
            return 0.2  # Too short
        elif word_count < 200:
            return 0.6  # Short but acceptable
        elif word_count < 2000:
            return 1.0  # Good length
        elif word_count < 5000:
            return 0.8  # Long but manageable
        else:
            return 0.4  # Too long
    
    def _score_source_reputation(self, source_url: str, source_name: str) -> float:
        """Score based on source reputation indicators."""
        score = 0.5  # Default score
        
        # Check for reputable domains
        reputable_domains = [
            'reuters.com', 'bloomberg.com', 'wsj.com', 'ft.com',
            'cnbc.com', 'marketwatch.com', 'yahoo.com/finance',
            'investing.com', 'sec.gov', 'nasdaq.com'
        ]
        
        for domain in reputable_domains:
            if domain in source_url.lower():
                score = 0.9
                break
        
        # Check for HTTPS
        if source_url.startswith('https://'):
            score += 0.1
        
        # Check for proper domain structure
        if re.match(r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', source_url):
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_recency(self, published_date: Optional[str]) -> float:
        """Score based on article recency."""
        if not published_date:
            return 0.3
        
        try:
            # Parse published date
            if isinstance(published_date, str):
                # Try common formats
                for fmt in ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                    try:
                        pub_date = datetime.strptime(published_date, fmt)
                        if pub_date.tzinfo is None:
                            pub_date = pub_date.replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        continue
                else:
                    return 0.3
            else:
                pub_date = published_date
            
            # Calculate age in hours
            now = datetime.now(timezone.utc)
            age_hours = (now - pub_date).total_seconds() / 3600
            
            if age_hours < 1:
                return 1.0  # Very recent
            elif age_hours < 24:
                return 0.9  # Within a day
            elif age_hours < 168:  # 1 week
                return 0.7  # Within a week
            elif age_hours < 720:  # 1 month
                return 0.5  # Within a month
            else:
                return 0.2  # Old
                
        except Exception:
            return 0.3
    
    def _score_readability(self, content: str) -> float:
        """Score based on content readability."""
        if not content:
            return 0.0
        
        # Simple readability metrics
        sentences = len(re.split(r'[.!?]+', content))
        words = len(content.split())
        
        if sentences == 0:
            return 0.3
        
        avg_sentence_length = words / sentences
        
        # Optimal sentence length is 15-20 words
        if 10 <= avg_sentence_length <= 25:
            readability_score = 0.9
        elif 5 <= avg_sentence_length <= 35:
            readability_score = 0.7
        else:
            readability_score = 0.4
        
        # Check for proper capitalization
        if content and content[0].isupper():
            readability_score += 0.1
        
        return min(readability_score, 1.0)
    
    def _score_metadata_completeness(self, article_data: Dict[str, Any]) -> float:
        """Score based on metadata completeness."""
        required_fields = ['title', 'content', 'url', 'published_date']
        optional_fields = ['author', 'source_name', 'summary', 'tags']
        
        required_score = sum(
            1 for field in required_fields 
            if article_data.get(field) and str(article_data[field]).strip()
        ) / len(required_fields)
        
        optional_score = sum(
            1 for field in optional_fields
            if article_data.get(field) and str(article_data[field]).strip()
        ) / len(optional_fields)
        
        # Weight required fields more heavily
        return (required_score * 0.8) + (optional_score * 0.2)
    
    def _score_url_quality(self, url: str) -> float:
        """Score based on URL quality indicators."""
        if not url:
            return 0.0
        
        score = 0.0
        
        # HTTPS check
        if url.startswith('https://'):
            score += 0.3
        elif url.startswith('http://'):
            score += 0.1
        
        # Domain structure check
        if re.match(r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', url):
            score += 0.3
        
        # No suspicious patterns
        suspicious_patterns = ['bit.ly', 'tinyurl', 'redirect', 'proxy']
        if not any(pattern in url.lower() for pattern in suspicious_patterns):
            score += 0.2
        
        # Reasonable length
        if 20 <= len(url) <= 200:
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_content_structure(self, content: str, title: str) -> float:
        """Score based on content structure quality."""
        if not content:
            return 0.0
        
        score = 0.0
        
        # Title exists and reasonable length
        if title and 10 <= len(title) <= 200:
            score += 0.3
        
        # Paragraph structure
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) >= 2:
            score += 0.3
        
        # Sentence variety
        sentences = re.split(r'[.!?]+', content)
        if len(sentences) >= 3:
            sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
            if sentence_lengths:
                # Check for sentence length variety
                avg_length = sum(sentence_lengths) / len(sentence_lengths)
                if 5 <= avg_length <= 30:
                    score += 0.2
        
        # No excessive repetition
        words = content.lower().split()
        if len(words) > 10:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio > 0.4:  # At least 40% unique words
                score += 0.2
        
        return min(score, 1.0)
    
    def _get_quality_tier(self, overall_score: float) -> str:
        """Convert numerical score to quality tier."""
        if overall_score >= 0.8:
            return 'high'
        elif overall_score >= 0.6:
            return 'medium'
        elif overall_score >= 0.4:
            return 'low'
        else:
            return 'poor'
    
    def _get_recommendations(self, scores: Dict[str, float]) -> list:
        """Generate recommendations based on factor scores."""
        recommendations = []
        
        for factor, score in scores.items():
            if score < 0.5:
                if factor == 'content_length':
                    recommendations.append('Content length should be between 200-2000 words')
                elif factor == 'source_reputation':
                    recommendations.append('Source may not be well-established')
                elif factor == 'recency':
                    recommendations.append('Article is not recent')
                elif factor == 'readability':
                    recommendations.append('Content readability could be improved')
                elif factor == 'metadata_completeness':
                    recommendations.append('Missing important metadata fields')
                elif factor == 'url_quality':
                    recommendations.append('URL structure could be improved')
                elif factor == 'content_structure':
                    recommendations.append('Content structure and formatting need improvement')
        
        if not recommendations:
            recommendations.append('Article meets quality standards')
        
        return recommendations 