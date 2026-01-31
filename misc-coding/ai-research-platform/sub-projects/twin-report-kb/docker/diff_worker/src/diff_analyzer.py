"""
DiffAnalyzer - Core module for analyzing differences between twin reports
"""

import asyncio
import json
import difflib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import httpx
import structlog
from fuzzywuzzy import fuzz, process
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

logger = structlog.get_logger(__name__)

@dataclass
class ArticleSection:
    """Represents a section of an article for analysis"""
    title: str
    content: str
    start_pos: int
    end_pos: int

class DiffAnalyzer:
    """
    Analyzes differences between twin reports to identify:
    - Content gaps (what one covers that the other doesn't)
    - Overlaps (similar content coverage)
    - Contradictions (conflicting information)
    - Quality differences (depth, citations, etc.)
    """
    
    def __init__(self, mac_studio_endpoint: str, model_name: str = "deepseek-r1"):
        self.mac_studio_endpoint = mac_studio_endpoint
        self.model_name = model_name
        self.stop_words = set(stopwords.words('english'))
        
    async def analyze_differences(
        self, 
        article_1: Dict[str, Any], 
        article_2: Dict[str, Any], 
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Main analysis method that coordinates different types of diff analysis
        """
        logger.info("Starting diff analysis", 
                   article_1_id=article_1["id"], 
                   article_2_id=article_2["id"],
                   analysis_type=analysis_type)
        
        # Extract content
        content_1 = article_1["body_md"]
        content_2 = article_2["body_md"]
        
        # Parse articles into sections
        sections_1 = self._parse_sections(content_1)
        sections_2 = self._parse_sections(content_2)
        
        # Perform different types of analysis based on type
        if analysis_type == "quick":
            result = await self._quick_analysis(sections_1, sections_2)
        elif analysis_type == "detailed":
            result = await self._detailed_analysis(sections_1, sections_2, article_1, article_2)
        else:  # comprehensive
            result = await self._comprehensive_analysis(sections_1, sections_2, article_1, article_2)
        
        # Add metadata
        result["metadata"] = {
            "article_1_info": {
                "id": article_1["id"],
                "model_origin": article_1["model_origin"],
                "word_count": article_1["word_count"]
            },
            "article_2_info": {
                "id": article_2["id"],
                "model_origin": article_2["model_origin"],
                "word_count": article_2["word_count"]
            },
            "analysis_type": analysis_type,
            "sections_analyzed": {
                "article_1_sections": len(sections_1),
                "article_2_sections": len(sections_2)
            }
        }
        
        logger.info("Diff analysis completed", 
                   confidence_score=result["confidence_score"],
                   gaps_found=len(result["gaps"]))
        
        return result
    
    def _parse_sections(self, content: str) -> List[ArticleSection]:
        """Parse markdown content into sections based on headers"""
        sections = []
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for i, line in enumerate(lines):
            # Check for markdown headers
            if line.startswith('#'):
                # Save previous section
                if current_section:
                    sections.append(ArticleSection(
                        title=current_section,
                        content='\n'.join(current_content),
                        start_pos=len(sections),
                        end_pos=i
                    ))
                
                # Start new section
                current_section = line.strip('#').strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Add final section
        if current_section:
            sections.append(ArticleSection(
                title=current_section,
                content='\n'.join(current_content),
                start_pos=len(sections),
                end_pos=len(lines)
            ))
        
        return sections
    
    async def _quick_analysis(
        self, 
        sections_1: List[ArticleSection], 
        sections_2: List[ArticleSection]
    ) -> Dict[str, Any]:
        """Quick analysis using text similarity and basic diff"""
        
        # Find section matches using fuzzy matching
        section_matches = self._find_section_matches(sections_1, sections_2)
        
        # Identify gaps (sections in one but not the other)
        gaps_1_to_2 = self._find_unmatched_sections(sections_1, section_matches, "article_1")
        gaps_2_to_1 = self._find_unmatched_sections(sections_2, section_matches, "article_2")
        
        # Find overlaps (similar sections)
        overlaps = self._find_overlapping_sections(section_matches)
        
        # Basic summary
        summary = f"Quick analysis: {len(gaps_1_to_2)} unique sections in article 1, {len(gaps_2_to_1)} unique sections in article 2, {len(overlaps)} overlapping sections"
        
        return {
            "summary": summary,
            "gaps": gaps_1_to_2 + gaps_2_to_1,
            "overlaps": overlaps,
            "contradictions": [],  # Not analyzed in quick mode
            "confidence_score": 0.7  # Lower confidence for quick analysis
        }
    
    async def _comprehensive_analysis(
        self, 
        sections_1: List[ArticleSection], 
        sections_2: List[ArticleSection],
        article_1: Dict[str, Any],
        article_2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Comprehensive analysis using AI model for deep comparison"""
        
        # Start with structural analysis
        section_matches = self._find_section_matches(sections_1, sections_2)
        structural_gaps = self._find_unmatched_sections(sections_1, section_matches, "article_1")
        structural_gaps.extend(self._find_unmatched_sections(sections_2, section_matches, "article_2"))
        
        # AI-powered semantic analysis
        semantic_analysis = await self._ai_semantic_analysis(
            article_1["body_md"], 
            article_2["body_md"],
            article_1["model_origin"],
            article_2["model_origin"]
        )
        
        # Contradiction detection
        contradictions = await self._detect_contradictions(sections_1, sections_2)
        
        # Quality comparison
        quality_analysis = self._analyze_quality_differences(article_1, article_2)
        
        # Combine all analyses
        all_gaps = structural_gaps + semantic_analysis.get("semantic_gaps", [])
        all_overlaps = self._find_overlapping_sections(section_matches) + semantic_analysis.get("semantic_overlaps", [])
        
        summary = self._generate_comprehensive_summary(
            all_gaps, all_overlaps, contradictions, quality_analysis
        )
        
        return {
            "summary": summary,
            "gaps": all_gaps,
            "overlaps": all_overlaps,
            "contradictions": contradictions,
            "confidence_score": semantic_analysis.get("confidence", 0.85),
            "quality_analysis": quality_analysis
        }
    
    async def _detailed_analysis(
        self, 
        sections_1: List[ArticleSection], 
        sections_2: List[ArticleSection],
        article_1: Dict[str, Any],
        article_2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detailed analysis with both structural and semantic components"""
        
        # Perform comprehensive analysis
        comprehensive_result = await self._comprehensive_analysis(
            sections_1, sections_2, article_1, article_2
        )
        
        # Add detailed section-by-section analysis
        section_details = await self._detailed_section_analysis(sections_1, sections_2)
        
        comprehensive_result["section_details"] = section_details
        comprehensive_result["confidence_score"] = 0.9  # Higher confidence for detailed analysis
        
        return comprehensive_result
    
    def _find_section_matches(
        self, 
        sections_1: List[ArticleSection], 
        sections_2: List[ArticleSection],
        threshold: int = 70
    ) -> List[Dict[str, Any]]:
        """Find matching sections between articles using fuzzy matching"""
        matches = []
        
        for i, section_1 in enumerate(sections_1):
            for j, section_2 in enumerate(sections_2):
                # Compare section titles
                title_similarity = fuzz.ratio(section_1.title, section_2.title)
                
                # Compare content (first 500 chars for efficiency)
                content_similarity = fuzz.partial_ratio(
                    section_1.content[:500], 
                    section_2.content[:500]
                )
                
                # Combined similarity score
                overall_similarity = (title_similarity * 0.3 + content_similarity * 0.7)
                
                if overall_similarity > threshold:
                    matches.append({
                        "section_1_idx": i,
                        "section_2_idx": j,
                        "section_1_title": section_1.title,
                        "section_2_title": section_2.title,
                        "title_similarity": title_similarity,
                        "content_similarity": content_similarity,
                        "overall_similarity": overall_similarity
                    })
        
        # Remove duplicate matches (keep highest similarity)
        unique_matches = {}
        for match in matches:
            key = (match["section_1_idx"], match["section_2_idx"])
            if key not in unique_matches or match["overall_similarity"] > unique_matches[key]["overall_similarity"]:
                unique_matches[key] = match
        
        return list(unique_matches.values())
    
    def _find_unmatched_sections(
        self, 
        sections: List[ArticleSection], 
        matches: List[Dict[str, Any]], 
        article_key: str
    ) -> List[str]:
        """Find sections that don't have matches in the other article"""
        matched_indices = set()
        
        for match in matches:
            if article_key == "article_1":
                matched_indices.add(match["section_1_idx"])
            else:
                matched_indices.add(match["section_2_idx"])
        
        unmatched = []
        for i, section in enumerate(sections):
            if i not in matched_indices:
                unmatched.append(f"{section.title}: {section.content[:200]}...")
        
        return unmatched
    
    def _find_overlapping_sections(self, matches: List[Dict[str, Any]]) -> List[str]:
        """Identify overlapping content between matched sections"""
        overlaps = []
        
        for match in matches:
            overlap_desc = f"Section '{match['section_1_title']}' overlaps with '{match['section_2_title']}' (similarity: {match['overall_similarity']:.1f}%)"
            overlaps.append(overlap_desc)
        
        return overlaps
    
    async def _ai_semantic_analysis(
        self, 
        content_1: str, 
        content_2: str,
        model_1: str,
        model_2: str
    ) -> Dict[str, Any]:
        """Use AI model to perform semantic analysis of content differences"""
        
        prompt = f"""
        Analyze the semantic differences between these two research articles:

        ARTICLE 1 (from {model_1}):
        {content_1[:3000]}...

        ARTICLE 2 (from {model_2}):
        {content_2[:3000]}...

        Identify:
        1. Semantic gaps: Important topics covered in one but not the other
        2. Semantic overlaps: Similar concepts expressed differently
        3. Perspective differences: Different approaches to the same topics
        4. Depth variations: Areas where one provides more detail

        Respond in JSON format:
        {{
            "semantic_gaps": ["gap1", "gap2"],
            "semantic_overlaps": ["overlap1", "overlap2"],
            "perspective_differences": ["diff1", "diff2"],
            "depth_variations": ["variation1", "variation2"],
            "confidence": 0.85
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
                    
                    # Try to parse JSON from response
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # Fallback if JSON parsing fails
                        return {
                            "semantic_gaps": [],
                            "semantic_overlaps": [],
                            "perspective_differences": [],
                            "depth_variations": [],
                            "confidence": 0.5,
                            "raw_response": content
                        }
                else:
                    logger.error("AI semantic analysis failed", status_code=response.status_code)
                    return {"semantic_gaps": [], "semantic_overlaps": [], "confidence": 0.3}
                    
        except Exception as e:
            logger.error("AI semantic analysis error", error=str(e))
            return {"semantic_gaps": [], "semantic_overlaps": [], "confidence": 0.3}
    
    async def _detect_contradictions(
        self, 
        sections_1: List[ArticleSection], 
        sections_2: List[ArticleSection]
    ) -> List[str]:
        """Detect contradictory statements between articles"""
        contradictions = []
        
        # Use AI to detect contradictions in overlapping sections
        for section_1 in sections_1:
            for section_2 in sections_2:
                # Only check sections that might be about the same topic
                if fuzz.ratio(section_1.title, section_2.title) > 50:
                    contradiction = await self._check_section_contradiction(section_1, section_2)
                    if contradiction:
                        contradictions.append(contradiction)
        
        return contradictions
    
    async def _check_section_contradiction(
        self, 
        section_1: ArticleSection, 
        section_2: ArticleSection
    ) -> Optional[str]:
        """Check if two sections contain contradictory information"""
        
        if len(section_1.content) < 100 or len(section_2.content) < 100:
            return None  # Skip very short sections
        
        prompt = f"""
        Compare these two sections and identify if they contain contradictory information:

        SECTION 1 ({section_1.title}):
        {section_1.content[:1000]}

        SECTION 2 ({section_2.title}):
        {section_2.content[:1000]}

        Respond with "CONTRADICTION: [description]" if contradictory information is found, or "NO_CONTRADICTION" if not.
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
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    if content.startswith("CONTRADICTION:"):
                        return content
                    
        except Exception as e:
            logger.error("Contradiction detection error", error=str(e))
        
        return None
    
    def _analyze_quality_differences(
        self, 
        article_1: Dict[str, Any], 
        article_2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze quality differences between articles"""
        
        return {
            "word_count_difference": abs(article_1["word_count"] - article_2["word_count"]),
            "word_count_ratio": article_1["word_count"] / max(article_2["word_count"], 1),
            "model_comparison": {
                "article_1_model": article_1["model_origin"],
                "article_2_model": article_2["model_origin"]
            }
        }
    
    async def _detailed_section_analysis(
        self, 
        sections_1: List[ArticleSection], 
        sections_2: List[ArticleSection]
    ) -> List[Dict[str, Any]]:
        """Perform detailed analysis of each section pair"""
        detailed_analysis = []
        
        matches = self._find_section_matches(sections_1, sections_2, threshold=30)  # Lower threshold for detailed analysis
        
        for match in matches:
            section_1 = sections_1[match["section_1_idx"]]
            section_2 = sections_2[match["section_2_idx"]]
            
            # Character-level diff
            diff = list(difflib.unified_diff(
                section_1.content.splitlines(),
                section_2.content.splitlines(),
                lineterm='',
                n=3
            ))
            
            detailed_analysis.append({
                "section_1_title": section_1.title,
                "section_2_title": section_2.title,
                "similarity_score": match["overall_similarity"],
                "character_diff": diff[:50],  # Limit size
                "word_count_diff": len(section_1.content.split()) - len(section_2.content.split())
            })
        
        return detailed_analysis
    
    def _generate_comprehensive_summary(
        self, 
        gaps: List[str], 
        overlaps: List[str], 
        contradictions: List[str],
        quality_analysis: Dict[str, Any]
    ) -> str:
        """Generate a comprehensive summary of the diff analysis"""
        
        summary_parts = []
        
        summary_parts.append(f"Analysis identified {len(gaps)} content gaps, {len(overlaps)} overlapping sections, and {len(contradictions)} contradictions.")
        
        if quality_analysis.get("word_count_ratio", 1) > 1.5 or quality_analysis.get("word_count_ratio", 1) < 0.67:
            summary_parts.append(f"Significant length difference detected (ratio: {quality_analysis.get('word_count_ratio', 1):.2f}).")
        
        if gaps:
            summary_parts.append(f"Major gaps include: {gaps[0][:100]}...")
        
        if contradictions:
            summary_parts.append(f"Key contradiction: {contradictions[0][:100]}...")
        
        return " ".join(summary_parts) 