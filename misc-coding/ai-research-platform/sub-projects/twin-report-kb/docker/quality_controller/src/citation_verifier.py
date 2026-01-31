"""
Citation Verifier - Validates citations and references
Checks accessibility, credibility, and format compliance
"""

import json
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
import structlog
from urllib.parse import urlparse
from .config_loader import get_config_loader

logger = structlog.get_logger(__name__)


class CitationVerifier:
    """Citation verification and validation"""
    
    def __init__(self, mac_studio_endpoint: str, model_name: str = "deepseek-r1"):
        self.mac_studio_endpoint = mac_studio_endpoint
        self.model_name = model_name
        self.config_loader = get_config_loader()
    
    async def verify_citations(self, content: str, sources: List[Dict[str, Any]], analysis_depth: str = "standard") -> Dict[str, Any]:
        """Main citation verification method"""
        
        logger.info("Starting citation verification", source_count=len(sources))
        
        # Extract and combine citations
        extracted_citations = self._extract_citations_fallback(content)
        all_citations = self._combine_citations(sources, extracted_citations)
        
        # Verify citations
        verification_results = await self._verify_citations_list(all_citations, analysis_depth)
        
        # Check formats
        format_analysis = self._check_citation_formats(all_citations)
        
        # Calculate score
        overall_score = self._calculate_citation_score(verification_results, format_analysis)
        
        return {
            "overall_score": overall_score,
            "total_citations": len(all_citations),
            "accessible_citations": verification_results.get("accessible_count", 0),
            "inaccessible_citations": verification_results.get("inaccessible_count", 0),
            "invalid_citations": verification_results.get("invalid_count", 0),
            "missing_citations": verification_results.get("missing_count", 0),
            "citation_details": verification_results.get("details", []),
            "format_analysis": format_analysis,
            "recommendations": self._generate_recommendations(verification_results, format_analysis)
        }
    
    def _extract_citations_fallback(self, content: str) -> List[Dict[str, Any]]:
        """Extract citations using regex patterns"""
        citations = []
        
        # Extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        
        for url in urls[:10]:  # Limit to 10
            citations.append({
                "text": url,
                "type": "url", 
                "url": url,
                "source": urlparse(url).netloc
            })
        
        return citations
    
    def _combine_citations(self, sources: List[Dict[str, Any]], extracted: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combine provided sources with extracted citations"""
        combined = []
        
        # Add provided sources
        for source in sources:
            combined.append({
                "text": source.get("title", source.get("url", "Unknown")),
                "type": source.get("type", "unknown"),
                "url": source.get("url", ""),
                "source": source.get("source", "provided")
            })
        
        # Add extracted
        combined.extend(extracted)
        
        # Remove duplicates
        seen = set()
        unique = []
        for citation in combined:
            identifier = citation.get("url") or citation.get("text", "")
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique.append(citation)
        
        return unique
    
    async def _verify_citations_list(self, citations: List[Dict[str, Any]], analysis_depth: str) -> Dict[str, Any]:
        """Verify list of citations"""
        
        results = {
            "accessible_count": 0,
            "inaccessible_count": 0, 
            "invalid_count": 0,
            "missing_count": 0,
            "details": []
        }
        
        # Limit based on analysis depth
        limit = {"quick": 5, "standard": 10, "deep": 20}.get(analysis_depth, 10)
        limited_citations = citations[:limit]
        
        for citation in limited_citations:
            url = citation.get("url", "")
            
            if not url:
                results["missing_count"] += 1
                results["details"].append({
                    "citation": citation["text"],
                    "status": "missing_url",
                    "accessibility_score": 0.0,
                    "issues": ["No URL provided"]
                })
                continue
            
            # Check accessibility
            if analysis_depth == "quick":
                # Just validate format for quick check
                if self._is_valid_url_format(url):
                    results["accessible_count"] += 1
                    results["details"].append({
                        "citation": citation["text"],
                        "status": "format_valid",
                        "accessibility_score": 0.7,
                        "issues": []
                    })
                else:
                    results["invalid_count"] += 1
                    results["details"].append({
                        "citation": citation["text"],
                        "status": "invalid_format",
                        "accessibility_score": 0.0,
                        "issues": ["Invalid URL format"]
                    })
            else:
                # Actually check URL
                accessibility_result = await self._check_url_accessibility(url)
                credibility_score = self._assess_source_credibility(url)
                
                if accessibility_result["accessible"]:
                    results["accessible_count"] += 1
                    status = "accessible"
                else:
                    results["inaccessible_count"] += 1
                    status = "inaccessible"
                
                results["details"].append({
                    "citation": citation["text"],
                    "status": status,
                    "accessibility_score": accessibility_result["score"],
                    "credibility_score": credibility_score,
                    "issues": accessibility_result.get("issues", [])
                })
        
        return results
    
    async def _check_url_accessibility(self, url: str) -> Dict[str, Any]:
        """Check if URL is accessible"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.head(url, follow_redirects=True)
                
                if response.status_code == 200:
                    return {"accessible": True, "score": 1.0, "issues": []}
                elif response.status_code in [301, 302, 303, 307, 308]:
                    return {"accessible": True, "score": 0.8, "issues": ["Redirected"]}
                else:
                    return {"accessible": False, "score": 0.0, "issues": [f"HTTP {response.status_code}"]}
        except Exception as e:
            return {"accessible": False, "score": 0.0, "issues": [f"Error: {str(e)[:50]}"]}
    
    def _is_valid_url_format(self, url: str) -> bool:
        """Check URL format validity"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except:
            return False
    
    def _assess_source_credibility(self, url: str) -> float:
        """Assess source credibility"""
        try:
            domain = urlparse(url).netloc.lower()
            
            # Check trusted domains
            trusted_domains = self.config_loader.get_trusted_domains()
            for trusted in trusted_domains:
                if trusted in domain:
                    return 0.9
            
            # Domain type scoring
            if domain.endswith('.edu'):
                return 0.85
            elif domain.endswith('.gov'):
                return 0.9
            elif domain.endswith('.org'):
                return 0.7
            
            return 0.5
        except:
            return 0.3
    
    def _check_citation_formats(self, citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check citation format compliance"""
        
        format_issues = []
        compliant_count = 0
        
        for citation in citations:
            issues = []
            
            # Check URL format
            url = citation.get("url", "")
            if url and not self._is_valid_url_format(url):
                issues.append("Invalid URL format")
            
            # Check for missing info
            if not citation.get("text"):
                issues.append("Missing citation text")
            
            if issues:
                format_issues.append({"citation": citation["text"], "issues": issues})
            else:
                compliant_count += 1
        
        total = len(citations)
        compliance_score = compliant_count / total if total > 0 else 1.0
        
        return {
            "compliance_score": compliance_score,
            "compliant_citations": compliant_count,
            "format_issues": format_issues
        }
    
    def _calculate_citation_score(self, verification_results: Dict[str, Any], format_analysis: Dict[str, Any]) -> float:
        """Calculate overall citation score"""
        
        total = sum([
            verification_results.get("accessible_count", 0),
            verification_results.get("inaccessible_count", 0),
            verification_results.get("invalid_count", 0),
            verification_results.get("missing_count", 0)
        ])
        
        if total == 0:
            return 0.5
        
        accessibility_score = verification_results.get("accessible_count", 0) / total
        format_score = format_analysis.get("compliance_score", 0.5)
        
        # Simple weighted average
        return (accessibility_score * 0.6) + (format_score * 0.4)
    
    def _generate_recommendations(self, verification_results: Dict[str, Any], format_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations"""
        
        recommendations = []
        
        if verification_results.get("missing_count", 0) > 0:
            recommendations.append(f"Add URLs for {verification_results['missing_count']} citations")
        
        if verification_results.get("inaccessible_count", 0) > 0:
            recommendations.append(f"Fix {verification_results['inaccessible_count']} inaccessible citations")
        
        if len(format_analysis.get("format_issues", [])) > 0:
            recommendations.append(f"Fix formatting in {len(format_analysis['format_issues'])} citations")
        
        if not recommendations:
            recommendations.append("Citation quality is good")
        
        return recommendations 