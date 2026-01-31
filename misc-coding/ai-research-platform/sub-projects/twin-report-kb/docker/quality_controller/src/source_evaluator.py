"""
Source Evaluator - Assesses source credibility and authority
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import httpx
import structlog
from urllib.parse import urlparse
from .config_loader import get_config_loader

logger = structlog.get_logger(__name__)


class SourceEvaluator:
    """Source credibility and authority evaluation"""
    
    def __init__(self, mac_studio_endpoint: str, model_name: str = "deepseek-r1"):
        self.mac_studio_endpoint = mac_studio_endpoint
        self.model_name = model_name
        self.config_loader = get_config_loader()
    
    async def evaluate_sources(self, sources: List[Dict[str, Any]], analysis_depth: str = "standard") -> Dict[str, Any]:
        """Main source evaluation method"""
        
        logger.info("Starting source evaluation", source_count=len(sources))
        
        if not sources:
            return {
                "overall_score": 0.5,
                "total_sources": 0,
                "high_credibility_sources": 0,
                "medium_credibility_sources": 0,
                "low_credibility_sources": 0,
                "outdated_sources": 0,
                "source_details": [],
                "recommendations": ["Add authoritative sources to support claims"]
            }
        
        # Evaluate each source
        source_evaluations = []
        for source in sources:
            evaluation = await self._evaluate_single_source(source, analysis_depth)
            source_evaluations.append(evaluation)
        
        # Calculate aggregate scores
        overall_score = self._calculate_overall_source_score(source_evaluations)
        
        # Categorize sources
        high_credibility = sum(1 for eval in source_evaluations if eval["credibility_score"] >= 0.8)
        medium_credibility = sum(1 for eval in source_evaluations if 0.5 <= eval["credibility_score"] < 0.8)
        low_credibility = sum(1 for eval in source_evaluations if eval["credibility_score"] < 0.5)
        outdated = sum(1 for eval in source_evaluations if eval.get("is_outdated", False))
        
        return {
            "overall_score": overall_score,
            "total_sources": len(sources),
            "high_credibility_sources": high_credibility,
            "medium_credibility_sources": medium_credibility,
            "low_credibility_sources": low_credibility,
            "outdated_sources": outdated,
            "source_details": source_evaluations,
            "recommendations": self._generate_source_recommendations(source_evaluations)
        }
    
    async def _evaluate_single_source(self, source: Dict[str, Any], analysis_depth: str) -> Dict[str, Any]:
        """Evaluate a single source"""
        
        url = source.get("url", "")
        title = source.get("title", "")
        author = source.get("author", "")
        year = source.get("year", "")
        source_type = source.get("type", "unknown")
        
        # Authority assessment
        authority_score = self._assess_authority(url, source_type, author)
        
        # Recency assessment
        recency_score, is_outdated = self._assess_recency(year, source_type)
        
        # Relevance assessment
        if analysis_depth in ["standard", "deep"]:
            relevance_score = await self._assess_relevance_ai(source)
        else:
            relevance_score = self._assess_relevance_simple(source)
        
        # Calculate weighted score
        weights = self.config_loader.get_source_evaluation_weights()
        weighted_score = (
            authority_score * weights.get("authority", 0.4) +
            recency_score * weights.get("recency", 0.3) +
            relevance_score * weights.get("relevance", 0.3)
        )
        
        # Determine credibility level
        if weighted_score >= 0.8:
            credibility_level = "high"
        elif weighted_score >= 0.5:
            credibility_level = "medium"
        else:
            credibility_level = "low"
        
        return {
            "source": source,
            "credibility_score": weighted_score,
            "credibility_level": credibility_level,
            "authority_score": authority_score,
            "recency_score": recency_score,
            "relevance_score": relevance_score,
            "is_outdated": is_outdated,
            "issues": self._identify_source_issues(source, authority_score, recency_score, is_outdated)
        }
    
    def _assess_authority(self, url: str, source_type: str, author: str) -> float:
        """Assess source authority"""
        
        authority_score = 0.5  # Base score
        
        if url:
            try:
                domain = urlparse(url).netloc.lower()
                
                # Check trusted domains
                trusted_domains = self.config_loader.get_trusted_domains()
                for trusted in trusted_domains:
                    if trusted in domain:
                        return 0.95
                
                # Check blacklisted domains
                blacklisted_domains = self.config_loader.get_blacklisted_domains()
                for blacklisted in blacklisted_domains:
                    if blacklisted in domain:
                        return 0.1
                
                # Domain type scoring
                if domain.endswith('.edu'):
                    authority_score = 0.9
                elif domain.endswith('.gov'):
                    authority_score = 0.95
                elif domain.endswith('.org'):
                    authority_score = 0.75
                elif any(academic in domain for academic in ['pubmed', 'scholar', 'arxiv', 'ieee', 'acm']):
                    authority_score = 0.9
                elif 'wikipedia' in domain:
                    authority_score = 0.6
                elif domain.endswith('.com'):
                    authority_score = 0.4
                
            except:
                authority_score = 0.3
        
        # Boost for academic sources
        if source_type in ['journal', 'academic', 'research']:
            authority_score = min(authority_score + 0.2, 1.0)
        
        # Boost for known authors (simplified check)
        if author and len(author.split()) >= 2:  # Full name provided
            authority_score = min(authority_score + 0.1, 1.0)
        
        return authority_score
    
    def _assess_recency(self, year: str, source_type: str) -> tuple[float, bool]:
        """Assess source recency"""
        
        current_year = datetime.now().year
        max_age_days = self.config_loader.get_max_source_age_days()
        
        if not year:
            # No year provided - assume medium recency
            return 0.5, False
        
        try:
            source_year = int(year)
            age_years = current_year - source_year
            
            # Different standards for different source types
            if source_type in ['news', 'blog']:
                # News should be recent
                if age_years <= 1:
                    recency_score = 1.0
                elif age_years <= 3:
                    recency_score = 0.6
                else:
                    recency_score = 0.2
                is_outdated = age_years > 2
            
            elif source_type in ['journal', 'academic', 'research']:
                # Academic sources can be older
                if age_years <= 5:
                    recency_score = 1.0
                elif age_years <= 10:
                    recency_score = 0.8
                elif age_years <= 15:
                    recency_score = 0.6
                else:
                    recency_score = 0.4
                is_outdated = age_years > 10
            
            else:
                # General sources
                if age_years <= 2:
                    recency_score = 1.0
                elif age_years <= 5:
                    recency_score = 0.7
                elif age_years <= 10:
                    recency_score = 0.5
                else:
                    recency_score = 0.3
                is_outdated = age_years > 5
            
            return recency_score, is_outdated
            
        except ValueError:
            return 0.5, False
    
    async def _assess_relevance_ai(self, source: Dict[str, Any]) -> float:
        """AI-powered relevance assessment"""
        
        source_text = f"Title: {source.get('title', '')}\nAuthor: {source.get('author', '')}\nType: {source.get('type', '')}"
        
        prompt = f"""
        Assess the relevance and quality of this source for research purposes:

        SOURCE:
        {source_text}

        Consider:
        1. How relevant is this source for factual research?
        2. Does it appear to be a primary or secondary source?
        3. Is the title descriptive and specific?
        4. Does it seem authoritative?

        Respond with a JSON object:
        {{
            "relevance_score": 0.85,
            "source_quality": "high|medium|low",
            "reasoning": "brief explanation"
        }}
        """
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mac_studio_endpoint}/chat/completions",
                    json={
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 500
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    try:
                        parsed = json.loads(content)
                        return parsed.get("relevance_score", 0.7)
                    except json.JSONDecodeError:
                        return 0.7
                else:
                    return 0.7
                    
        except Exception as e:
            logger.error("AI relevance assessment error", error=str(e))
            return 0.7
    
    def _assess_relevance_simple(self, source: Dict[str, Any]) -> float:
        """Simple relevance assessment"""
        
        relevance_score = 0.5  # Base score
        
        title = source.get("title", "").lower()
        source_type = source.get("type", "")
        
        # Check for descriptive title
        if len(title.split()) >= 3:
            relevance_score += 0.2
        
        # Check for specific keywords that indicate quality
        quality_keywords = ['study', 'research', 'analysis', 'report', 'investigation', 'survey']
        if any(keyword in title for keyword in quality_keywords):
            relevance_score += 0.2
        
        # Type-based scoring
        if source_type in ['journal', 'academic', 'research']:
            relevance_score += 0.2
        elif source_type in ['news', 'report']:
            relevance_score += 0.1
        
        return min(relevance_score, 1.0)
    
    def _calculate_overall_source_score(self, evaluations: List[Dict[str, Any]]) -> float:
        """Calculate overall source quality score"""
        
        if not evaluations:
            return 0.5
        
        # Average credibility scores
        total_score = sum(eval["credibility_score"] for eval in evaluations)
        avg_score = total_score / len(evaluations)
        
        # Penalty for having too many low-quality sources
        low_quality_count = sum(1 for eval in evaluations if eval["credibility_score"] < 0.5)
        low_quality_ratio = low_quality_count / len(evaluations)
        
        # Apply penalty
        penalty = low_quality_ratio * 0.3
        final_score = max(0.0, avg_score - penalty)
        
        return min(final_score, 1.0)
    
    def _identify_source_issues(self, source: Dict[str, Any], authority_score: float, recency_score: float, is_outdated: bool) -> List[str]:
        """Identify specific issues with a source"""
        
        issues = []
        
        if authority_score < 0.5:
            issues.append("Low authority/credibility")
        
        if recency_score < 0.5:
            issues.append("Outdated information")
        
        if is_outdated:
            issues.append("Source is too old for current research")
        
        if not source.get("author"):
            issues.append("Missing author information")
        
        if not source.get("title"):
            issues.append("Missing or unclear title")
        
        if not source.get("url"):
            issues.append("No URL provided for verification")
        
        return issues
    
    def _generate_source_recommendations(self, evaluations: List[Dict[str, Any]]) -> List[str]:
        """Generate source improvement recommendations"""
        
        recommendations = []
        
        if not evaluations:
            return ["Add authoritative sources to support claims"]
        
        low_credibility_count = sum(1 for eval in evaluations if eval["credibility_score"] < 0.5)
        outdated_count = sum(1 for eval in evaluations if eval.get("is_outdated", False))
        missing_info_count = sum(1 for eval in evaluations if len(eval.get("issues", [])) > 0)
        
        if low_credibility_count > 0:
            recommendations.append(f"Replace {low_credibility_count} low-credibility sources with authoritative ones")
        
        if outdated_count > 0:
            recommendations.append(f"Update {outdated_count} outdated sources with recent information")
        
        if missing_info_count > 0:
            recommendations.append(f"Complete missing information for {missing_info_count} sources")
        
        # Check for source diversity
        source_types = [eval["source"].get("type", "unknown") for eval in evaluations]
        unique_types = len(set(source_types))
        
        if unique_types <= 1 and len(evaluations) > 1:
            recommendations.append("Add diverse source types for comprehensive coverage")
        
        # Check for academic sources
        academic_count = sum(1 for eval in evaluations if eval["source"].get("type") in ["journal", "academic", "research"])
        if academic_count == 0 and len(evaluations) > 2:
            recommendations.append("Consider adding academic or peer-reviewed sources")
        
        if not recommendations:
            recommendations.append("Source quality is good")
        
        return recommendations 