"""
GapDetector - Identifies gaps in coverage across multiple articles
"""

import json
from typing import Dict, List, Any, Optional
from collections import defaultdict
import httpx
import structlog
from fuzzywuzzy import fuzz
import re
from .config_loader import get_config_loader

logger = structlog.get_logger(__name__)

class GapDetector:
    """
    Analyzes multiple articles to identify:
    - Coverage gaps (important topics not covered by any article)
    - Depth gaps (topics covered superficially)
    - Perspective gaps (missing viewpoints or approaches)
    - Research recommendations for filling gaps
    """
    
    def __init__(self, mac_studio_endpoint: str, model_name: str = "deepseek-r1"):
        self.mac_studio_endpoint = mac_studio_endpoint
        self.model_name = model_name
        self.config_loader = get_config_loader()
        
    async def detect_gaps(
        self, 
        articles: List[Dict[str, Any]], 
        analysis_depth: str = "standard"
    ) -> Dict[str, Any]:
        """
        Main gap detection method
        """
        logger.info("Starting gap detection", 
                   article_count=len(articles),
                   analysis_depth=analysis_depth)
        
        if len(articles) < 2:
            raise ValueError("Need at least 2 articles for gap analysis")
        
        # Extract topics and themes from all articles
        topic_coverage = await self._analyze_topic_coverage(articles)
        
        # Identify gaps based on analysis depth
        if analysis_depth == "quick":
            gaps = await self._quick_gap_analysis(topic_coverage, articles)
        elif analysis_depth == "deep":
            gaps = await self._deep_gap_analysis(topic_coverage, articles)
        else:  # standard
            gaps = await self._standard_gap_analysis(topic_coverage, articles)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(gaps, articles)
        
        # Calculate priority scores
        priorities = self._calculate_priority_scores(gaps, topic_coverage)
        
        result = {
            "gaps": gaps,
            "coverage": topic_coverage,
            "recommendations": recommendations,
            "priorities": priorities,
            "analysis_metadata": {
                "article_count": len(articles),
                "analysis_depth": analysis_depth,
                "models_analyzed": [article.get("model_origin") for article in articles]
            }
        }
        
        logger.info("Gap detection completed", 
                   gaps_found=len(gaps),
                   recommendations_generated=len(recommendations))
        
        return result
    
    async def _analyze_topic_coverage(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze what topics are covered by each article"""
        
        coverage_analysis = {
            "topics_by_article": {},
            "topic_frequency": defaultdict(int),
            "coverage_matrix": {},
            "depth_analysis": {}
        }
        
        for article in articles:
            article_id = article["id"]
            content = article["body_md"]
            
            # Extract topics using AI
            topics = await self._extract_topics_from_content(content, article["model_origin"])
            coverage_analysis["topics_by_article"][article_id] = topics
            
            # Update frequency counts
            for topic in topics:
                coverage_analysis["topic_frequency"][topic["name"]] += 1
            
            # Analyze depth for each topic
            depth_scores = await self._analyze_topic_depth(content, topics)
            coverage_analysis["depth_analysis"][article_id] = depth_scores
        
        # Build coverage matrix
        all_topics = set()
        for topics in coverage_analysis["topics_by_article"].values():
            all_topics.update([topic["name"] for topic in topics])
        
        for topic in all_topics:
            coverage_analysis["coverage_matrix"][topic] = {}
            for article_id in coverage_analysis["topics_by_article"]:
                article_topics = [t["name"] for t in coverage_analysis["topics_by_article"][article_id]]
                coverage_analysis["coverage_matrix"][topic][article_id] = topic in article_topics
        
        return coverage_analysis
    
    async def _extract_topics_from_content(
        self, 
        content: str, 
        model_origin: str
    ) -> List[Dict[str, Any]]:
        """Extract main topics and themes from article content"""
        
        prompt = f"""
        Analyze this research article and extract the main topics and themes covered:

        CONTENT (from {model_origin}):
        {content[:2000]}...

        Identify the main topics discussed. For each topic, provide:
        1. Topic name (concise)
        2. Coverage level (brief, moderate, detailed)
        3. Key points covered
        4. Estimated depth score (1-10)

        Respond in JSON format:
        {{
            "topics": [
                {{
                    "name": "Topic Name",
                    "coverage_level": "moderate",
                    "key_points": ["point1", "point2"],
                    "depth_score": 7
                }}
            ]
        }}
        """
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mac_studio_endpoint}/chat/completions",
                    json={
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                        "max_tokens": 1500
                    },
                    timeout=90.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    try:
                        parsed = json.loads(content)
                        return parsed.get("topics", [])
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse topic extraction JSON")
                        return []
                else:
                    logger.error("Topic extraction failed", status_code=response.status_code)
                    return []
                    
        except Exception as e:
            logger.error("Topic extraction error", error=str(e))
            return []
    
    async def _analyze_topic_depth(
        self, 
        content: str, 
        topics: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Analyze how deeply each topic is covered in the content"""
        
        depth_scores = {}
        
        for topic in topics:
            topic_name = topic["name"]
            
            # Count mentions and analyze context
            mentions = self._count_topic_mentions(content, topic_name)
            
            # Calculate depth based on mentions, key points, and coverage level
            coverage_multiplier = {
                "brief": 0.3,
                "moderate": 0.7,
                "detailed": 1.0
            }.get(topic.get("coverage_level", "moderate"), 0.7)
            
            depth_score = (
                min(mentions / 5, 1.0) * 0.3 +  # Mention frequency (capped at 5)
                len(topic.get("key_points", [])) / 10 * 0.4 +  # Key points coverage
                topic.get("depth_score", 5) / 10 * 0.3  # AI-assessed depth
            ) * coverage_multiplier
            
            depth_scores[topic_name] = min(depth_score, 1.0)
        
        return depth_scores
    
    def _count_topic_mentions(self, content: str, topic_name: str) -> int:
        """Count how many times a topic is mentioned in the content"""
        
        # Create variations of the topic name
        variations = [
            topic_name.lower(),
            topic_name.replace(" ", "-").lower(),
            topic_name.replace(" ", "_").lower()
        ]
        
        content_lower = content.lower()
        total_mentions = 0
        
        for variation in variations:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(variation) + r'\b'
            matches = re.findall(pattern, content_lower)
            total_mentions += len(matches)
        
        return total_mentions
    
    async def _quick_gap_analysis(
        self, 
        topic_coverage: Dict[str, Any], 
        articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Quick gap analysis using coverage matrix and basic heuristics"""
        
        gaps = []
        coverage_matrix = topic_coverage["coverage_matrix"]
        
        # Find topics covered by only one article
        for topic, coverage in coverage_matrix.items():
            covered_count = sum(coverage.values())
            if covered_count == 1:
                gaps.append({
                    "type": "single_coverage_gap",
                    "topic": topic,
                    "description": f"Topic '{topic}' only covered by one article",
                    "severity": "medium",
                    "recommendation": f"Additional perspective needed on {topic}"
                })
        
        # Find topics with shallow coverage across all articles
        for article_id, depth_scores in topic_coverage["depth_analysis"].items():
            for topic, depth in depth_scores.items():
                if depth < 0.3:  # Very shallow coverage
                    gaps.append({
                        "type": "depth_gap",
                        "topic": topic,
                        "article_id": article_id,
                        "description": f"Shallow coverage of '{topic}' in article {article_id}",
                        "severity": "low",
                        "depth_score": depth
                    })
        
        return gaps
    
    async def _standard_gap_analysis(
        self, 
        topic_coverage: Dict[str, Any], 
        articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Standard gap analysis with AI-assisted identification"""
        
        # Start with quick analysis
        gaps = await self._quick_gap_analysis(topic_coverage, articles)
        
        # AI-powered gap identification
        ai_gaps = await self._ai_gap_identification(topic_coverage, articles)
        gaps.extend(ai_gaps)
        
        # Domain-specific gap analysis
        domain_gaps = await self._domain_specific_gaps(articles)
        gaps.extend(domain_gaps)
        
        return gaps
    
    async def _deep_gap_analysis(
        self, 
        topic_coverage: Dict[str, Any], 
        articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Deep gap analysis with comprehensive AI evaluation"""
        
        # Include standard analysis
        gaps = await self._standard_gap_analysis(topic_coverage, articles)
        
        # Deep semantic gap analysis
        semantic_gaps = await self._semantic_gap_analysis(articles)
        gaps.extend(semantic_gaps)
        
        # Research methodology gaps
        methodology_gaps = await self._methodology_gap_analysis(articles)
        gaps.extend(methodology_gaps)
        
        # Citation and evidence gaps
        evidence_gaps = await self._evidence_gap_analysis(articles)
        gaps.extend(evidence_gaps)
        
        return gaps
    
    async def _ai_gap_identification(
        self, 
        topic_coverage: Dict[str, Any], 
        articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Use AI to identify potential gaps in coverage"""
        
        # Prepare summary of current coverage
        coverage_summary = self._prepare_coverage_summary(topic_coverage, articles)
        
        prompt = f"""
        Based on this analysis of research article coverage, identify potential gaps:

        COVERAGE SUMMARY:
        {coverage_summary}

        Identify gaps in:
        1. Topic coverage (important related topics not addressed)
        2. Perspective diversity (missing viewpoints or approaches)
        3. Depth of analysis (topics that need deeper exploration)
        4. Methodological approaches (missing research methods)

        Respond in JSON format:
        {{
            "gaps": [
                {{
                    "type": "topic_gap",
                    "description": "Missing coverage of [topic]",
                    "severity": "high|medium|low",
                    "recommendation": "Specific action to address gap"
                }}
            ]
        }}
        """
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mac_studio_endpoint}/chat/completions",
                    json={
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 2000
                    },
                    timeout=120.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    try:
                        parsed = json.loads(content)
                        return parsed.get("gaps", [])
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse AI gap identification JSON")
                        return []
                else:
                    return []
                    
        except Exception as e:
            logger.error("AI gap identification error", error=str(e))
            return []
    
    async def _semantic_gap_analysis(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze semantic gaps between articles"""
        gaps = []
        return gaps
    
    async def _methodology_gap_analysis(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze gaps in research methodologies"""
        gaps = []
        return gaps
    
    async def _evidence_gap_analysis(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze gaps in evidence and citations"""
        gaps = []
        return gaps
    
    async def _domain_specific_gaps(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify domain-specific gaps based on article content"""
        gaps = []
        return gaps
    
    def _prepare_coverage_summary(
        self, 
        topic_coverage: Dict[str, Any], 
        articles: List[Dict[str, Any]]
    ) -> str:
        """Prepare a summary of current topic coverage for AI analysis"""
        
        summary_parts = []
        
        # Article overview
        summary_parts.append(f"Articles analyzed: {len(articles)}")
        summary_parts.append(f"Models: {[a.get('model_origin') for a in articles]}")
        
        # Topic coverage overview
        total_topics = len(topic_coverage["topic_frequency"])
        summary_parts.append(f"Total topics identified: {total_topics}")
        
        # Most and least covered topics
        topic_freq = topic_coverage["topic_frequency"]
        if topic_freq:
            most_covered = max(topic_freq.items(), key=lambda x: x[1])
            least_covered = min(topic_freq.items(), key=lambda x: x[1])
            summary_parts.append(f"Most covered topic: {most_covered[0]} ({most_covered[1]} articles)")
            summary_parts.append(f"Least covered topic: {least_covered[0]} ({least_covered[1]} articles)")
        
        return "\n".join(summary_parts)
    
    async def _generate_recommendations(
        self, 
        gaps: List[Dict[str, Any]], 
        articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on identified gaps"""
        
        recommendations = []
        
        # Group gaps by type for better recommendations
        gaps_by_type = defaultdict(list)
        for gap in gaps:
            gaps_by_type[gap["type"]].append(gap)
        
        # Generate type-specific recommendations
        for gap_type, type_gaps in gaps_by_type.items():
            if gap_type == "single_coverage_gap":
                recommendations.append({
                    "type": "additional_research",
                    "priority": "high",
                    "description": f"Research additional perspectives on {len(type_gaps)} topics covered by only one model",
                    "specific_topics": [gap["topic"] for gap in type_gaps]
                })
            
            elif gap_type == "depth_gap":
                recommendations.append({
                    "type": "deeper_analysis",
                    "priority": "medium",
                    "description": f"Conduct deeper analysis on {len(type_gaps)} topics with shallow coverage",
                    "affected_articles": list(set(gap["article_id"] for gap in type_gaps if "article_id" in gap))
                })
        
        return recommendations
    
    def _calculate_priority_scores(
        self, 
        gaps: List[Dict[str, Any]], 
        topic_coverage: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate priority scores for addressing gaps using config"""
        
        priorities = {}
        priority_config = self.config_loader.get_priority_scores()
        
        for gap in gaps:
            gap_id = gap.get("topic", gap.get("description", "unknown"))
            
            # Base priority based on severity using config
            severity = gap.get("severity", "medium")
            base_score = priority_config.get(severity, priority_config.get("medium", 0.6))
            
            priorities[gap_id] = base_score
        
        return priorities 