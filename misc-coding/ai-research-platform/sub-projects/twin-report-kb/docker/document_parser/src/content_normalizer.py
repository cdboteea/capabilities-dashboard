#!/usr/bin/env python3
"""
Content Normalizer for Document Parser
Cleans and standardizes extracted content from various sources
"""

import re
import asyncio
from typing import Dict, List, Any, Optional
import html
import unicodedata

import structlog

logger = structlog.get_logger(__name__)

class ContentNormalizer:
    """Normalizes and cleans extracted content"""
    
    def __init__(self):
        self.supported_types = ['text', 'web', 'pdf', 'docx', 'xlsx', 'pptx', 'google_doc', 'chat_export']
    
    async def normalize(self, content: str, content_type: str, options: Dict[str, Any] = None) -> str:
        """Normalize content based on type"""
        
        if options is None:
            options = {}
        
        logger.info("Starting content normalization", 
                   content_type=content_type,
                   content_length=len(content),
                   options=options)
        
        try:
            # Apply general cleaning first
            normalized = self._general_cleanup(content)
            
            # Apply type-specific normalization
            if content_type in ['web', 'html']:
                normalized = self._normalize_web_content(normalized, options)
            elif content_type == 'pdf':
                normalized = self._normalize_pdf_content(normalized, options)
            elif content_type in ['docx', 'xlsx', 'pptx']:
                normalized = self._normalize_office_content(normalized, options)
            elif content_type == 'google_doc':
                normalized = self._normalize_google_doc_content(normalized, options)
            elif content_type == 'chat_export':
                normalized = self._normalize_chat_content(normalized, options)
            
            # Apply final cleanup
            normalized = self._final_cleanup(normalized, options)
            
            logger.info("Content normalization completed",
                       original_length=len(content),
                       normalized_length=len(normalized),
                       reduction_ratio=1 - len(normalized) / len(content) if content else 0)
            
            return normalized
            
        except Exception as e:
            logger.error("Content normalization failed", 
                        content_type=content_type, 
                        error=str(e))
            return content  # Return original content if normalization fails
    
    def _general_cleanup(self, content: str) -> str:
        """Apply general cleanup to all content"""
        
        if not content:
            return ""
        
        # Decode HTML entities
        content = html.unescape(content)
        
        # Normalize Unicode characters
        content = unicodedata.normalize('NFKC', content)
        
        # Remove null bytes and other control characters
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        # Normalize line endings
        content = re.sub(r'\r\n|\r', '\n', content)
        
        # Remove excessive whitespace
        content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces/tabs to single space
        content = re.sub(r'\n[ \t]+', '\n', content)  # Leading whitespace on lines
        content = re.sub(r'[ \t]+\n', '\n', content)  # Trailing whitespace on lines
        
        return content
    
    def _normalize_web_content(self, content: str, options: Dict[str, Any]) -> str:
        """Normalize web/HTML content"""
        
        # Remove markdown artifacts that might come from html2text
        if options.get('clean_markdown', True):
            # Remove markdown links but keep the text
            content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
            
            # Remove markdown formatting
            content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # Bold
            content = re.sub(r'\*([^*]+)\*', r'\1', content)      # Italic
            content = re.sub(r'`([^`]+)`', r'\1', content)        # Code
        
        # Remove navigation and UI elements
        nav_patterns = [
            r'(?i)(home|menu|navigation|nav|breadcrumb|sitemap)',
            r'(?i)(login|logout|sign in|sign up|register)',
            r'(?i)(search|contact|about|privacy|terms)',
            r'(?i)(cookie|gdpr|consent)',
            r'(?i)(advertisement|ads|sponsored)'
        ]
        
        for pattern in nav_patterns:
            content = re.sub(f'^.*{pattern}.*$', '', content, flags=re.MULTILINE)
        
        # Remove excessive newlines from web content
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    def _normalize_pdf_content(self, content: str, options: Dict[str, Any]) -> str:
        """Normalize PDF content"""
        
        # Fix common PDF extraction issues
        
        # Fix broken words (common in PDF extraction)
        if options.get('fix_broken_words', True):
            # Join lines that end with lowercase and start with lowercase (likely broken words)
            content = re.sub(r'([a-z])\n([a-z])', r'\1\2', content)
            
            # Fix hyphenated words across lines
            content = re.sub(r'([a-z])-\n([a-z])', r'\1\2', content)
        
        # Remove page numbers and headers/footers
        if options.get('remove_page_elements', True):
            # Remove standalone numbers (likely page numbers)
            content = re.sub(r'^\s*\d+\s*$', '', content, flags=re.MULTILINE)
            
            # Remove common header/footer patterns
            content = re.sub(r'^.*Page \d+ of \d+.*$', '', content, flags=re.MULTILINE)
            content = re.sub(r'^.*\d+/\d+.*$', '', content, flags=re.MULTILINE)
        
        # Fix spacing issues
        content = re.sub(r'([.!?])\n([A-Z])', r'\1 \2', content)  # Sentence breaks
        
        return content
    
    def _normalize_office_content(self, content: str, options: Dict[str, Any]) -> str:
        """Normalize Microsoft Office content"""
        
        # Remove table formatting artifacts
        if options.get('clean_tables', True):
            # Clean up table separators
            content = re.sub(r'\s*\|\s*', ' | ', content)
            content = re.sub(r'\n\s*\|\s*\n', '\n', content)
        
        # Remove slide indicators for PowerPoint
        if 'Slide ' in content:
            content = re.sub(r'^Slide \d+:\s*', '', content, flags=re.MULTILINE)
        
        # Remove sheet indicators for Excel
        if 'Sheet:' in content:
            content = re.sub(r'^Sheet: [^\n]*\n', '', content, flags=re.MULTILINE)
        
        return content
    
    def _normalize_google_doc_content(self, content: str, options: Dict[str, Any]) -> str:
        """Normalize Google Docs content"""
        
        # Remove Google Docs specific artifacts
        content = re.sub(r'\[INLINE_OBJECT\]', '', content)
        content = re.sub(r'---PAGE_BREAK---', '\n\n', content)
        
        # Clean up table formatting
        content = re.sub(r'\s*\|\s*', ' | ', content)
        
        return content
    
    def _normalize_chat_content(self, content: str, options: Dict[str, Any]) -> str:
        """Normalize chat export content"""
        
        # Remove media placeholders
        if options.get('remove_media_placeholders', True):
            content = re.sub(r'\[ATTACHMENT\]', '', content)
            content = re.sub(r'\[PHOTO\]', '', content)
            content = re.sub(r'\[VIDEO\]', '', content)
            content = re.sub(r'\[AUDIO\]', '', content)
            content = re.sub(r'\[FILE\]', '', content)
        
        # Normalize timestamp formats
        if options.get('normalize_timestamps', True):
            # Remove timestamps if requested
            content = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s+', '', content, flags=re.MULTILINE)
            content = re.sub(r'^\d{2}:\d{2}\s+', '', content, flags=re.MULTILINE)
        
        # Clean up participant names
        if options.get('clean_participant_format', True):
            content = re.sub(r'^([^:]+):\s*', r'\1: ', content, flags=re.MULTILINE)
        
        return content
    
    def _final_cleanup(self, content: str, options: Dict[str, Any]) -> str:
        """Apply final cleanup steps"""
        
        # Remove excessive blank lines
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        
        # Remove leading and trailing whitespace
        content = content.strip()
        
        # Remove empty lines at the beginning and end
        lines = content.split('\n')
        
        # Remove empty lines from start
        while lines and not lines[0].strip():
            lines.pop(0)
        
        # Remove empty lines from end
        while lines and not lines[-1].strip():
            lines.pop()
        
        content = '\n'.join(lines)
        
        # Ensure content ends with a single newline if it's not empty
        if content and not content.endswith('\n'):
            content += '\n'
        
        # Remove very short lines that are likely artifacts (unless they're meaningful)
        if options.get('remove_short_lines', False):
            lines = content.split('\n')
            filtered_lines = []
            
            for line in lines:
                line_stripped = line.strip()
                # Keep line if it's empty (paragraph break) or longer than 3 chars
                # or contains meaningful punctuation
                if (not line_stripped or 
                    len(line_stripped) > 3 or 
                    any(char in line_stripped for char in '.!?:;')):
                    filtered_lines.append(line)
            
            content = '\n'.join(filtered_lines)
        
        # Apply character limits if specified
        max_length = options.get('max_length')
        if max_length and len(content) > max_length:
            # Truncate at word boundary
            content = content[:max_length]
            last_space = content.rfind(' ')
            if last_space > max_length * 0.9:  # If we can find a space near the end
                content = content[:last_space] + '...'
            else:
                content = content + '...'
        
        return content
    
    def get_content_statistics(self, original: str, normalized: str) -> Dict[str, Any]:
        """Get statistics about the normalization process"""
        
        return {
            "original_length": len(original),
            "normalized_length": len(normalized),
            "reduction_percentage": (1 - len(normalized) / len(original)) * 100 if original else 0,
            "original_lines": len(original.split('\n')) if original else 0,
            "normalized_lines": len(normalized.split('\n')) if normalized else 0,
            "original_words": len(original.split()) if original else 0,
            "normalized_words": len(normalized.split()) if normalized else 0
        }
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported content types"""
        return self.supported_types 