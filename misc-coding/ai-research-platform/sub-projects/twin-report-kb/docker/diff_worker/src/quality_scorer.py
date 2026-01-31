"""
QualityScorer - Evaluates the quality of diff analyses and reports
"""

import json
from typing import Dict, List, Any, Optional
import httpx
import structlog
import re
from .config_loader import get_config_loader

logger = structlog.get_logger(__name__)

class QualityScorer:
    """
    Evaluates the quality of diff analyses and research reports based on:
    - Completeness of analysis
    - Accuracy of gap identification
    - Usefulness of recommendations
    - Overall analytical rigor
    """
    
    def __init__(self, mac_studio_endpoint: str, model_name: str = "deepseek-r1"):
        self.mac_studio_endpoint = mac_studio_endpoint
        self.model_name = model_name
        self.config_loader = get_config_loader()
        
    async def score_diff_quality(self, diff_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score the quality of a diff analysis result
        """
        logger.info("Starting diff quality scoring")
        
        # Component scoring
        completeness_score = self._score_completeness(diff_result)
        accuracy_score = await self._score_accuracy(diff_result)
        usefulness_score = self._score_usefulness(diff_result)
        coherence_score = self._score_coherence(diff_result)
        
        # Overall quality score (weighted average using config)
        weights = self.config_loader.get_quality_weights()
        overall_score = (
            completeness_score * weights.get("completeness", 0.3) +
            accuracy_score * weights.get("accuracy", 0.25) +
            usefulness_score * weights.get("usefulness", 0.25) +
            coherence_score * weights.get("coherence", 0.2)
        )
        
        quality_assessment = {
            "overall_score": round(overall_score, 3),
            "component_scores": {
                "completeness": round(completeness_score, 3),
                "accuracy": round(accuracy_score, 3),
                "usefulness": round(usefulness_score, 3),
                "coherence": round(coherence_score, 3)
            },
            "quality_level": self._get_quality_level(overall_score),
            "improvement_suggestions": self._generate_improvement_suggestions(
                completeness_score, accuracy_score, usefulness_score, coherence_score
            ),
            "scoring_metadata": {
                "gaps_analyzed": len(diff_result.get("gaps", [])),
                "overlaps_found": len(diff_result.get("overlaps", [])),
                "contradictions_found": len(diff_result.get("contradictions", []))
            }
        }
        
        logger.info("Diff quality scoring completed", overall_score=overall_score)
        return quality_assessment
    
    def _score_completeness(self, diff_result: Dict[str, Any]) -> float:
        """
        Score the completeness of the diff analysis using config
        """
        score = 0.0
        completeness_config = self.config_loader.get_completeness_config()
        
        # Component weights from config
        required_weight = completeness_config.get("required_components_weight", 0.4)
        summary_weight = completeness_config.get("summary_quality_weight", 0.3)
        gap_weight = completeness_config.get("gap_analysis_depth_weight", 0.3)
        
        # Check for required components
        required_components = ["summary", "gaps", "overlaps", "contradictions", "confidence_score"]
        present_components = sum(1 for comp in required_components if comp in diff_result)
        score += (present_components / len(required_components)) * required_weight
        
        # Check summary quality using config thresholds
        summary = diff_result.get("summary", "")
        summary_thresholds = completeness_config.get("summary_thresholds", {})
        basic_length = summary_thresholds.get("basic_length", 50)
        detailed_length = summary_thresholds.get("detailed_length", 150)
        
        if len(summary) > basic_length:
            score += summary_weight * 0.67  # 2/3 of summary weight
        if len(summary) > detailed_length:
            score += summary_weight * 0.33  # 1/3 of summary weight
        
        # Check gap analysis depth using config
        gaps = diff_result.get("gaps", [])
        gap_thresholds = completeness_config.get("gap_thresholds", {})
        multiple_gaps = gap_thresholds.get("multiple_gaps", 2)
        
        if gaps:
            score += gap_weight * 0.67  # 2/3 of gap weight
            if len(gaps) > multiple_gaps:
                score += gap_weight * 0.33  # 1/3 of gap weight
        
        return min(score, 1.0)
    
    async def _score_accuracy(self, diff_result: Dict[str, Any]) -> float:
        """
        Score the accuracy of the diff analysis using AI validation and config
        """
        accuracy_config = self.config_loader.get_accuracy_config()
        confidence_weight = accuracy_config.get("confidence_weight", 0.6)
        ai_weight = accuracy_config.get("ai_validation_weight", 0.4)
        
        # Use confidence score as a proxy for accuracy
        confidence = diff_result.get("confidence_score", 0.5)
        
        # Additional validation using AI with config model
        accuracy_score = await self._ai_accuracy_validation(diff_result)
        
        # Combine confidence and AI validation using config weights
        final_accuracy = (confidence * confidence_weight + accuracy_score * ai_weight)
        
        return min(final_accuracy, 1.0)
    
    def _score_usefulness(self, diff_result: Dict[str, Any]) -> float:
        """
        Score the usefulness of the analysis results using config
        """
        score = 0.0
        usefulness_config = self.config_loader.get_usefulness_config()
        
        # Component weights from config
        gaps_weight = usefulness_config.get("actionable_gaps_weight", 0.3)
        overlaps_weight = usefulness_config.get("quality_overlaps_weight", 0.2)
        contradictions_weight = usefulness_config.get("detailed_contradictions_weight", 0.2)
        insights_weight = usefulness_config.get("summary_insights_weight", 0.3)
        
        # Thresholds from config
        thresholds = usefulness_config.get("thresholds", {})
        gap_min_length = thresholds.get("actionable_gap_min_length", 20)
        contradiction_min_length = thresholds.get("detailed_contradiction_min_length", 50)
        
        # Actionable gaps using config threshold
        gaps = diff_result.get("gaps", [])
        actionable_gaps = sum(1 for gap in gaps if isinstance(gap, str) and len(gap) > gap_min_length)
        if gaps:
            score += min(actionable_gaps / len(gaps), 1.0) * gaps_weight
        
        # Quality of overlaps identification
        overlaps = diff_result.get("overlaps", [])
        if overlaps:
            detailed_overlaps = sum(1 for overlap in overlaps if "similarity" in str(overlap))
            score += min(detailed_overlaps / len(overlaps), 1.0) * overlaps_weight
        
        # Contradiction usefulness using config threshold
        contradictions = diff_result.get("contradictions", [])
        if contradictions:
            detailed_contradictions = sum(1 for contra in contradictions 
                                        if isinstance(contra, str) and len(contra) > contradiction_min_length)
            score += min(detailed_contradictions / len(contradictions), 1.0) * contradictions_weight
        
        # Summary informativeness using config keywords
        summary = diff_result.get("summary", "")
        if summary:
            insight_keywords = self.config_loader.get_insight_keywords()
            insights = sum(1 for keyword in insight_keywords if keyword in summary.lower())
            score += min(insights / len(insight_keywords), 1.0) * insights_weight
        
        return min(score, 1.0)
    
    def _score_coherence(self, diff_result: Dict[str, Any]) -> float:
        """
        Score the coherence and logical consistency of the analysis
        """
        score = 0.0
        
        # Summary coherence with findings
        summary = diff_result.get("summary", "")
        gaps = diff_result.get("gaps", [])
        overlaps = diff_result.get("overlaps", [])
        contradictions = diff_result.get("contradictions", [])
        
        # Check if summary mentions findings
        if gaps and any("gap" in summary.lower() for _ in [1]):
            score += 0.3
        if overlaps and any("overlap" in summary.lower() for _ in [1]):
            score += 0.2
        if contradictions and any("contradiction" in summary.lower() for _ in [1]):
            score += 0.2
        
        # Logical consistency check
        confidence = diff_result.get("confidence_score", 0.5)
        findings_count = len(gaps) + len(overlaps) + len(contradictions)
        
        # High confidence should correlate with substantial findings
        if confidence > 0.8 and findings_count > 2:
            score += 0.2
        elif confidence < 0.4 and findings_count < 2:
            score += 0.1
        
        # Metadata consistency
        metadata = diff_result.get("metadata", {})
        if metadata:
            score += 0.1
        
        return min(score, 1.0)
    
    async def _ai_accuracy_validation(self, diff_result: Dict[str, Any]) -> float:
        """
        Use AI to validate the accuracy of the diff analysis
        """
        prompt = f"""
        Evaluate the accuracy and quality of this diff analysis:

        SUMMARY: {diff_result.get('summary', 'N/A')}
        
        GAPS IDENTIFIED: {len(diff_result.get('gaps', []))} gaps
        Sample gaps: {diff_result.get('gaps', [])[:3]}
        
        OVERLAPS IDENTIFIED: {len(diff_result.get('overlaps', []))} overlaps
        Sample overlaps: {diff_result.get('overlaps', [])[:3]}
        
        CONTRADICTIONS: {len(diff_result.get('contradictions', []))} contradictions
        
        CONFIDENCE SCORE: {diff_result.get('confidence_score', 'N/A')}

        Rate the accuracy of this analysis on a scale of 0-1 based on:
        1. Logical consistency of findings
        2. Appropriateness of confidence level
        3. Quality of gap/overlap identification
        4. Overall analytical rigor

        Respond with just a number between 0 and 1 (e.g., 0.85).
        """
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mac_studio_endpoint}/chat/completions",
                    json={
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 100
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"].strip()
                    
                    # Extract number from response
                    try:
                        score = float(content)
                        return max(0.0, min(1.0, score))  # Clamp to 0-1
                    except ValueError:
                        # Try to extract first number found
                        numbers = re.findall(r'0?\.\d+|[01]', content)
                        if numbers:
                            return max(0.0, min(1.0, float(numbers[0])))
                        
                logger.warning("Could not parse AI accuracy score")
                return 0.5  # Default neutral score
                
        except Exception as e:
            logger.error("AI accuracy validation error", error=str(e))
            return 0.5  # Default neutral score
    
    def _get_quality_level(self, overall_score: float) -> str:
        """
        Convert numerical score to quality level using config thresholds
        """
        thresholds = self.config_loader.get_quality_thresholds()
        
        if overall_score >= thresholds.get("excellent", 0.9):
            return "excellent"
        elif overall_score >= thresholds.get("very_good", 0.8):
            return "very_good"
        elif overall_score >= thresholds.get("good", 0.7):
            return "good"
        elif overall_score >= thresholds.get("satisfactory", 0.6):
            return "satisfactory"
        elif overall_score >= thresholds.get("needs_improvement", 0.5):
            return "needs_improvement"
        else:
            return "poor"
    
    def _generate_improvement_suggestions(
        self, 
        completeness: float, 
        accuracy: float, 
        usefulness: float, 
        coherence: float
    ) -> List[str]:
        """
        Generate specific improvement suggestions based on component scores
        """
        suggestions = []
        
        if completeness < 0.7:
            suggestions.append("Improve analysis completeness by ensuring all required components are present and detailed")
        
        if accuracy < 0.7:
            suggestions.append("Enhance accuracy by using more rigorous comparison methods and validation")
        
        if usefulness < 0.7:
            suggestions.append("Increase usefulness by providing more actionable insights and specific recommendations")
        
        if coherence < 0.7:
            suggestions.append("Improve coherence by ensuring summary aligns with findings and maintaining logical consistency")
        
        # Overall suggestions
        if all(score < 0.8 for score in [completeness, accuracy, usefulness, coherence]):
            suggestions.append("Consider using deeper analysis methods and more comprehensive comparison techniques")
        
        return suggestions
    
    async def score_article_quality(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score the quality of an individual research article
        """
        logger.info("Starting article quality scoring", article_id=article.get("id"))
        
        # Component scoring
        content_score = self._score_content_quality(article)
        structure_score = self._score_structure_quality(article)
        citation_score = self._score_citation_quality(article)
        depth_score = self._score_depth_quality(article)
        
        # Overall quality score
        overall_score = (
            content_score * 0.3 +
            structure_score * 0.2 +
            citation_score * 0.25 +
            depth_score * 0.25
        )
        
        quality_assessment = {
            "overall_score": round(overall_score, 3),
            "component_scores": {
                "content": round(content_score, 3),
                "structure": round(structure_score, 3),
                "citations": round(citation_score, 3),
                "depth": round(depth_score, 3)
            },
            "quality_level": self._get_quality_level(overall_score),
            "article_metadata": {
                "word_count": article.get("word_count", 0),
                "model_origin": article.get("model_origin", "unknown"),
                "estimated_reading_time": self._estimate_reading_time(article)
            }
        }
        
        logger.info("Article quality scoring completed", 
                   article_id=article.get("id"),
                   overall_score=overall_score)
        
        return quality_assessment
    
    def _score_content_quality(self, article: Dict[str, Any]) -> float:
        """Score the quality of article content"""
        content = article.get("body_md", "")
        score = 0.0
        
        # Length appropriateness
        word_count = article.get("word_count", len(content.split()))
        if 1000 <= word_count <= 10000:  # Reasonable length
            score += 0.3
        elif word_count > 500:  # At least substantial
            score += 0.2
        
        # Content richness indicators
        if content:
            # Variety of sentence structures
            sentences = content.split('.')
            avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
            if 10 <= avg_sentence_length <= 25:  # Good sentence variety
                score += 0.2
            
            # Presence of examples or specifics
            examples_indicators = ['example', 'instance', 'case', 'specifically', 'such as']
            example_count = sum(content.lower().count(indicator) for indicator in examples_indicators)
            score += min(example_count / 10, 0.2)  # Up to 0.2 for examples
            
            # Technical depth indicators
            technical_indicators = ['analysis', 'research', 'study', 'data', 'evidence']
            technical_count = sum(content.lower().count(indicator) for indicator in technical_indicators)
            score += min(technical_count / 20, 0.3)  # Up to 0.3 for technical depth
        
        return min(score, 1.0)
    
    def _score_structure_quality(self, article: Dict[str, Any]) -> float:
        """Score the structural quality of the article"""
        content = article.get("body_md", "")
        score = 0.0
        
        # Header structure
        headers = re.findall(r'^#+\s+.+$', content, re.MULTILINE)
        if len(headers) >= 3:  # Good section organization
            score += 0.4
        elif len(headers) >= 1:  # Some organization
            score += 0.2
        
        # Paragraph structure
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) >= 5:  # Well-paragraphed
            score += 0.3
        elif len(paragraphs) >= 3:  # Adequate paragraphing
            score += 0.2
        
        # Logical flow indicators
        transition_words = ['however', 'therefore', 'furthermore', 'moreover', 'consequently']
        transition_count = sum(content.lower().count(word) for word in transition_words)
        score += min(transition_count / 10, 0.3)  # Up to 0.3 for transitions
        
        return min(score, 1.0)
    
    def _score_citation_quality(self, article: Dict[str, Any]) -> float:
        """Score the quality of citations and references"""
        content = article.get("body_md", "")
        score = 0.0
        
        # Citation count
        citations = re.findall(r'\[.*?\]|\(.*?20\d{2}.*?\)', content)
        citation_count = len(citations)
        
        if citation_count >= 10:  # Well-referenced
            score += 0.4
        elif citation_count >= 5:  # Adequately referenced
            score += 0.3
        elif citation_count >= 2:  # Some references
            score += 0.2
        
        # Citation diversity (different types)
        url_citations = len(re.findall(r'https?://', content))
        academic_indicators = content.lower().count('journal') + content.lower().count('study')
        
        if url_citations > 0 and academic_indicators > 0:  # Diverse sources
            score += 0.3
        elif url_citations > 0 or academic_indicators > 0:  # Some source diversity
            score += 0.2
        
        # In-text citation integration
        inline_citations = len(re.findall(r'\w+\s+\[.*?\]|\w+\s+\(.*?20\d{2}.*?\)', content))
        if inline_citations > 0:
            score += 0.3
        
        return min(score, 1.0)
    
    def _score_depth_quality(self, article: Dict[str, Any]) -> float:
        """Score the depth and analytical quality"""
        content = article.get("body_md", "")
        score = 0.0
        
        # Analytical depth indicators
        analysis_words = ['analyze', 'examine', 'investigate', 'explore', 'evaluate', 'assess']
        analysis_count = sum(content.lower().count(word) for word in analysis_words)
        score += min(analysis_count / 15, 0.3)  # Up to 0.3 for analytical language
        
        # Evidence and reasoning
        evidence_words = ['evidence', 'data', 'research', 'findings', 'results', 'shows']
        evidence_count = sum(content.lower().count(word) for word in evidence_words)
        score += min(evidence_count / 20, 0.3)  # Up to 0.3 for evidence
        
        # Critical thinking indicators
        critical_words = ['however', 'although', 'despite', 'nevertheless', 'on the other hand']
        critical_count = sum(content.lower().count(word) for word in critical_words)
        score += min(critical_count / 10, 0.2)  # Up to 0.2 for critical thinking
        
        # Detailed explanations
        explanation_words = ['because', 'since', 'due to', 'as a result', 'therefore']
        explanation_count = sum(content.lower().count(word) for word in explanation_words)
        score += min(explanation_count / 15, 0.2)  # Up to 0.2 for explanations
        
        return min(score, 1.0)
    
    def _estimate_reading_time(self, article: Dict[str, Any]) -> int:
        """Estimate reading time in minutes"""
        word_count = article.get("word_count", 0)
        # Average reading speed: 200-300 words per minute
        reading_time = max(1, word_count // 250)  # Conservative estimate
        return reading_time 