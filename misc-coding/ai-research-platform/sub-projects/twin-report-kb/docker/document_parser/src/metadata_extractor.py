#!/usr/bin/env python3
"""
Metadata Extractor for Document Parser
Extracts and enriches metadata from various document types
"""

import asyncio
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
import re

import magic
import textstat
import structlog

logger = structlog.get_logger(__name__)

class MetadataExtractor:
    """Extracts and enriches document metadata"""
    
    def __init__(self):
        self.supported_types = ['pdf', 'docx', 'xlsx', 'pptx', 'web', 'google_doc', 'chat_export']
    
    async def extract(self, content: bytes, content_type: str, existing_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract metadata from document content"""
        
        if existing_metadata is None:
            existing_metadata = {}
        
        logger.info("Starting metadata extraction", 
                   content_type=content_type,
                   content_size=len(content))
        
        try:
            metadata = existing_metadata.copy()
            
            # Add basic file information
            metadata.update({
                "content_size": len(content),
                "content_type": content_type,
                "extracted_at": datetime.now().isoformat(),
                "extractor_version": "1.0.0"
            })
            
            # Detect MIME type
            try:
                mime_type = magic.from_buffer(content, mime=True)
                metadata["mime_type"] = mime_type
            except Exception as e:
                logger.warning("Failed to detect MIME type", error=str(e))
                metadata["mime_type"] = "unknown"
            
            # Generate content hash
            metadata["content_hash"] = {
                "sha256": hashlib.sha256(content).hexdigest(),
                "md5": hashlib.md5(content).hexdigest()
            }
            
            # Extract text for analysis if content is text-based
            if content_type in ['pdf', 'docx', 'web', 'google_doc']:
                try:
                    text_content = content.decode('utf-8', errors='ignore')
                    text_metadata = await self._analyze_text_content(text_content)
                    metadata.update(text_metadata)
                except Exception as e:
                    logger.warning("Failed to analyze text content", error=str(e))
            
            logger.info("Metadata extraction completed", 
                       metadata_fields=len(metadata))
            
            return metadata
            
        except Exception as e:
            logger.error("Metadata extraction failed", 
                        content_type=content_type, 
                        error=str(e))
            return existing_metadata
    
    async def extract_from_url(self, url: str, existing_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract metadata from URL"""
        
        if existing_metadata is None:
            existing_metadata = {}
        
        try:
            metadata = existing_metadata.copy()
            
            # Parse URL
            parsed_url = urlparse(url)
            
            metadata.update({
                "source_url": url,
                "domain": parsed_url.netloc,
                "path": parsed_url.path,
                "scheme": parsed_url.scheme,
                "extracted_at": datetime.now().isoformat()
            })
            
            # Analyze domain
            domain_info = self._analyze_domain(parsed_url.netloc)
            metadata["domain_info"] = domain_info
            
            return metadata
            
        except Exception as e:
            logger.error("URL metadata extraction failed", url=url, error=str(e))
            return existing_metadata
    
    async def extract_from_google_doc(self, doc_id: str, existing_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract metadata from Google Doc ID"""
        
        if existing_metadata is None:
            existing_metadata = {}
        
        try:
            metadata = existing_metadata.copy()
            
            metadata.update({
                "google_doc_id": doc_id,
                "google_doc_url": f"https://docs.google.com/document/d/{doc_id}/edit",
                "source_type": "google_docs",
                "extracted_at": datetime.now().isoformat()
            })
            
            return metadata
            
        except Exception as e:
            logger.error("Google Doc metadata extraction failed", doc_id=doc_id, error=str(e))
            return existing_metadata
    
    async def _analyze_text_content(self, text: str) -> Dict[str, Any]:
        """Analyze text content for readability and other metrics"""
        
        if not text or len(text.strip()) == 0:
            return {"text_analysis": {"error": "No text content to analyze"}}
        
        try:
            analysis = {
                "text_analysis": {
                    "character_count": len(text),
                    "word_count": len(text.split()),
                    "sentence_count": len(re.findall(r'[.!?]+', text)),
                    "paragraph_count": len([p for p in text.split('\n\n') if p.strip()]),
                    "line_count": len(text.split('\n'))
                }
            }
            
            # Readability analysis
            try:
                readability = {
                    "flesch_reading_ease": textstat.flesch_reading_ease(text),
                    "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
                    "gunning_fog": textstat.gunning_fog(text),
                    "automated_readability_index": textstat.automated_readability_index(text),
                    "coleman_liau_index": textstat.coleman_liau_index(text),
                    "reading_time_minutes": textstat.reading_time(text, ms_per_char=14.69)
                }
                analysis["readability"] = readability
            except Exception as e:
                logger.warning("Readability analysis failed", error=str(e))
                analysis["readability"] = {"error": str(e)}
            
            # Language detection (basic)
            language_info = self._detect_language_hints(text)
            analysis["language"] = language_info
            
            # Content structure analysis
            structure_info = self._analyze_content_structure(text)
            analysis["structure"] = structure_info
            
            return analysis
            
        except Exception as e:
            logger.warning("Text content analysis failed", error=str(e))
            return {"text_analysis": {"error": str(e)}}
    
    def _analyze_domain(self, domain: str) -> Dict[str, Any]:
        """Analyze domain information"""
        
        info = {
            "domain": domain,
            "tld": domain.split('.')[-1] if '.' in domain else "",
            "is_subdomain": domain.count('.') > 1,
            "domain_type": "unknown"
        }
        
        # Classify domain types
        if domain.endswith('.edu'):
            info["domain_type"] = "educational"
        elif domain.endswith('.gov'):
            info["domain_type"] = "government"
        elif domain.endswith('.org'):
            info["domain_type"] = "organization"
        elif domain.endswith('.com'):
            info["domain_type"] = "commercial"
        elif domain.endswith('.net'):
            info["domain_type"] = "network"
        
        # Check for common platforms
        platform_indicators = {
            'wikipedia.org': 'wikipedia',
            'github.com': 'github',
            'stackoverflow.com': 'stackoverflow',
            'medium.com': 'medium',
            'youtube.com': 'youtube',
            'reddit.com': 'reddit',
            'arxiv.org': 'arxiv',
            'pubmed.ncbi.nlm.nih.gov': 'pubmed'
        }
        
        for platform_domain, platform_name in platform_indicators.items():
            if platform_domain in domain:
                info["platform"] = platform_name
                break
        
        return info
    
    def _detect_language_hints(self, text: str) -> Dict[str, Any]:
        """Detect language hints from text"""
        
        # Simple language detection based on common words
        language_indicators = {
            'english': ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with'],
            'spanish': ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no'],
            'french': ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir'],
            'german': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich'],
            'portuguese': ['o', 'de', 'a', 'e', 'do', 'da', 'em', 'um', 'para', 'é']
        }
        
        text_lower = text.lower()
        word_counts = {}
        
        for language, indicators in language_indicators.items():
            count = sum(1 for word in indicators if f' {word} ' in text_lower)
            if count > 0:
                word_counts[language] = count
        
        detected_language = max(word_counts, key=word_counts.get) if word_counts else 'unknown'
        confidence = word_counts.get(detected_language, 0) / len(language_indicators.get(detected_language, []))
        
        return {
            "detected_language": detected_language,
            "confidence": min(confidence, 1.0),
            "word_counts": word_counts
        }
    
    def _analyze_content_structure(self, text: str) -> Dict[str, Any]:
        """Analyze content structure"""
        
        structure = {
            "has_headings": bool(re.search(r'^#{1,6}\s+', text, re.MULTILINE)),
            "has_lists": bool(re.search(r'^\s*[-*+]\s+', text, re.MULTILINE)),
            "has_numbered_lists": bool(re.search(r'^\s*\d+\.\s+', text, re.MULTILINE)),
            "has_urls": bool(re.search(r'https?://[^\s]+', text)),
            "has_email_addresses": bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)),
            "has_phone_numbers": bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)),
            "has_dates": bool(re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)),
            "has_code_blocks": bool(re.search(r'```|`[^`]+`', text)),
            "has_tables": bool(re.search(r'\|.*\|', text))
        }
        
        # Count specific elements
        structure["url_count"] = len(re.findall(r'https?://[^\s]+', text))
        structure["email_count"] = len(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
        structure["heading_count"] = len(re.findall(r'^#{1,6}\s+', text, re.MULTILINE))
        
        # Analyze paragraph structure
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if paragraphs:
            paragraph_lengths = [len(p) for p in paragraphs]
            structure["paragraph_stats"] = {
                "count": len(paragraphs),
                "avg_length": sum(paragraph_lengths) / len(paragraph_lengths),
                "min_length": min(paragraph_lengths),
                "max_length": max(paragraph_lengths)
            }
        
        return structure
    
    def enrich_metadata(self, metadata: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Enrich existing metadata with additional analysis"""
        
        enriched = metadata.copy()
        
        try:
            # Add content fingerprint
            if content:
                enriched["content_fingerprint"] = {
                    "first_100_chars": content[:100],
                    "last_100_chars": content[-100:] if len(content) > 100 else content,
                    "content_preview": content[:500] + "..." if len(content) > 500 else content
                }
            
            # Add extraction context
            enriched["extraction_context"] = {
                "timestamp": datetime.now().isoformat(),
                "extractor": "document_parser_metadata_extractor",
                "version": "1.0.0"
            }
            
            return enriched
            
        except Exception as e:
            logger.warning("Metadata enrichment failed", error=str(e))
            return metadata
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported content types"""
        return self.supported_types 