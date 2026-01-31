"""
Quality Assessor - Evaluates content quality metrics
"""

import json
import re
from typing import Dict, List, Any
import httpx
import structlog
from .config_loader import get_config_loader

logger = structlog.get_logger(__name__)


class QualityAssessor:
    """Content quality assessment"""
    
    def __init__(self, mac_studio_endpoint: str, model_name: str = "deepseek-r1"):
        self.mac_studio_endpoint = mac_studio_endpoint
        self.model_name = model_name
        self.config_loader = get_config_loader()
    
    async def assess_quality(self, content: str, analysis_depth: str = "standard") -> Dict[str, Any]:
        """Main quality assessment method"""
        
        logger.info("Starting quality assessment", content_length=len(content))
        
        # Basic metrics
        basic_metrics = self._calculate_basic_metrics(content)
        
        # AI-powered quality analysis
        if analysis_depth in ["standard", "deep"]:
            ai_analysis = await self._ai_quality_analysis(content, analysis_depth)
        else:
            ai_analysis = self._quick_quality_analysis(content)
        
        # Calculate component scores
        readability_score = self._calculate_readability_score(content, basic_metrics)
        coherence_score = ai_analysis.get("coherence_score", 0.7)
        completeness_score = ai_analysis.get("completeness_score", 0.7)
        structure_score = self._calculate_structure_score(content, basic_metrics)
        
        # Overall score
        weights = self.config_loader.get_quality_assessment_weights()
        overall_score = (
            readability_score * weights.get("readability", 0.25) +
            coherence_score * weights.get("coherence", 0.25) +
            completeness_score * weights.get("completeness", 0.25) +
            structure_score * weights.get("structure", 0.25)
        )
        
        return {
            "overall_score": overall_score,
            "readability_score": readability_score,
            "coherence_score": coherence_score,
            "completeness_score": completeness_score,
            "structure_score": structure_score,
            "basic_metrics": basic_metrics,
            "ai_analysis": ai_analysis,
            "readability_issues": self._identify_readability_issues(content, basic_metrics),
            "coherence_issues": ai_analysis.get("coherence_issues", []),
            "recommendations": self._generate_quality_recommendations(
                readability_score, coherence_score, completeness_score, structure_score, basic_metrics
            )
        }
    
    def _calculate_basic_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate basic content metrics"""
        
        # Word and sentence counts
        words = re.findall(r'\b\w+\b', content)
        sentences = re.split(r'[.!?]+', content)
        paragraphs = content.split('\n\n')
        
        word_count = len(words)
        sentence_count = len([s for s in sentences if s.strip()])
        paragraph_count = len([p for p in paragraphs if p.strip()])
        
        # Average lengths
        avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else 0
        avg_sentences_per_paragraph = sentence_count / paragraph_count if paragraph_count > 0 else 0
        
        # Character counts
        char_count = len(content)
        char_count_no_spaces = len(content.replace(' ', ''))
        
        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "character_count": char_count,
            "character_count_no_spaces": char_count_no_spaces,
            "avg_words_per_sentence": avg_words_per_sentence,
            "avg_sentences_per_paragraph": avg_sentences_per_paragraph,
            "avg_word_length": sum(len(word) for word in words) / len(words) if words else 0
        }
    
    def _calculate_readability_score(self, content: str, metrics: Dict[str, Any]) -> float:
        """Calculate readability score"""
        
        word_count = metrics["word_count"]
        sentence_count = metrics["sentence_count"]
        avg_words_per_sentence = metrics["avg_words_per_sentence"]
        
        # Simple readability scoring
        if word_count < self.config_loader.get_min_word_count():
            return 0.3  # Too short
        
        max_sentence_length = self.config_loader.get_max_sentence_length()
        if avg_words_per_sentence > max_sentence_length:
            return 0.4  # Sentences too long
        
        # Score based on sentence length
        if avg_words_per_sentence <= 15:
            sentence_score = 1.0
        elif avg_words_per_sentence <= 20:
            sentence_score = 0.8
        elif avg_words_per_sentence <= 25:
            sentence_score = 0.6
        else:
            sentence_score = 0.4
        
        # Score based on word length
        avg_word_length = metrics["avg_word_length"]
        if avg_word_length <= 5:
            word_score = 1.0
        elif avg_word_length <= 6:
            word_score = 0.8
        else:
            word_score = 0.6
        
        return (sentence_score + word_score) / 2
    
    def _calculate_structure_score(self, content: str, metrics: Dict[str, Any]) -> float:
        """Calculate structure quality score"""
        
        structure_score = 0.5  # Base score
        
        # Check for headings/sections
        if re.search(r'^#+ ', content, re.MULTILINE):
            structure_score += 0.2
        
        # Check for lists
        if re.search(r'^\s*[-*•]\s', content, re.MULTILINE):
            structure_score += 0.1
        
        # Check for proper paragraphing
        paragraph_count = metrics["paragraph_count"]
        if paragraph_count > 1:
            structure_score += 0.1
        
        # Check sentence variety
        sentences = re.split(r'[.!?]+', content)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        if sentence_lengths:
            length_variety = len(set(sentence_lengths)) / len(sentence_lengths)
            structure_score += length_variety * 0.1
        
        return min(structure_score, 1.0)
    
    async def _ai_quality_analysis(self, content: str, analysis_depth: str) -> Dict[str, Any]:
        """AI-powered quality analysis"""
        
        prompt = f"""
        Analyze the quality of this content for coherence and completeness:

        CONTENT:
        {content[:2000] if analysis_depth == "standard" else content[:3000]}...

        Evaluate:
        1. Coherence: logical flow, consistency, clear connections
        2. Completeness: thorough coverage, missing information
        3. Clarity: clear explanations, easy to understand
        4. Organization: well-structured, good transitions

        Respond in JSON format:
        {{
            "coherence_score": 0.85,
            "completeness_score": 0.80,
            "clarity_score": 0.90,
            "organization_score": 0.75,
            "coherence_issues": ["list of specific issues"],
            "completeness_gaps": ["missing information"],
            "suggestions": ["improvement suggestions"]
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
                        "max_tokens": 1500
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content_response = result["choices"][0]["message"]["content"]
                    
                    try:
                        return json.loads(content_response)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse AI quality analysis")
                        return self._default_ai_analysis()
                else:
                    logger.error("AI quality analysis failed", status_code=response.status_code)
                    return self._default_ai_analysis()
                    
        except Exception as e:
            logger.error("AI quality analysis error", error=str(e))
            return self._default_ai_analysis()
    
    def _quick_quality_analysis(self, content: str) -> Dict[str, Any]:
        """Quick quality analysis without AI"""
        
        # Simple heuristics
        word_count = len(content.split())
        
        # Coherence based on transition words
        transition_words = ['however', 'therefore', 'furthermore', 'moreover', 'additionally', 'consequently']
        transition_count = sum(1 for word in transition_words if word in content.lower())
        coherence_score = min(0.5 + (transition_count * 0.1), 1.0)
        
        # Completeness based on content length and structure
        if word_count < 100:
            completeness_score = 0.3
        elif word_count < 500:
            completeness_score = 0.6
        else:
            completeness_score = 0.8
        
        return {
            "coherence_score": coherence_score,
            "completeness_score": completeness_score,
            "clarity_score": 0.7,
            "organization_score": 0.7,
            "coherence_issues": [],
            "completeness_gaps": [],
            "suggestions": ["Consider adding more detailed analysis for comprehensive coverage"]
        }
    
    def _default_ai_analysis(self) -> Dict[str, Any]:
        """Default AI analysis when AI call fails"""
        return {
            "coherence_score": 0.7,
            "completeness_score": 0.7,
            "clarity_score": 0.7,
            "organization_score": 0.7,
            "coherence_issues": ["Unable to analyze coherence"],
            "completeness_gaps": ["Unable to analyze completeness"],
            "suggestions": ["Manual review recommended"]
        }
    
    def _identify_readability_issues(self, content: str, metrics: Dict[str, Any]) -> List[str]:
        """Identify specific readability issues"""
        
        issues = []
        
        if metrics["word_count"] < self.config_loader.get_min_word_count():
            issues.append(f"Content too short ({metrics['word_count']} words)")
        
        if metrics["avg_words_per_sentence"] > self.config_loader.get_max_sentence_length():
            issues.append(f"Sentences too long (avg {metrics['avg_words_per_sentence']:.1f} words)")
        
        if metrics["paragraph_count"] <= 1 and metrics["word_count"] > 200:
            issues.append("Needs paragraph breaks for better readability")
        
        if metrics["avg_word_length"] > 7:
            issues.append("Consider using simpler vocabulary")
        
        return issues
    
    def _generate_quality_recommendations(
        self, 
        readability_score: float, 
        coherence_score: float, 
        completeness_score: float, 
        structure_score: float,
        metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate quality improvement recommendations"""
        
        recommendations = []
        
        if readability_score < 0.7:
            recommendations.append("Improve readability with shorter sentences and simpler words")
        
        if coherence_score < 0.7:
            recommendations.append("Enhance logical flow and add transition words")
        
        if completeness_score < 0.7:
            recommendations.append("Add more comprehensive coverage of the topic")
        
        if structure_score < 0.7:
            recommendations.append("Improve structure with headings, lists, and better organization")
        
        if metrics["word_count"] < 200:
            recommendations.append("Expand content with more detailed explanations")
        
        if not recommendations:
            recommendations.append("Content quality is good")
        
        return recommendations 