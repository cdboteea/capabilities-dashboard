#!/usr/bin/env python3
"""
Google Docs Parser for Document Parser
Extracts content from Google Docs using Google Drive API
"""

import asyncio
from typing import Dict, List, Any, Optional
import os
import json

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import structlog

logger = structlog.get_logger(__name__)

class GoogleDocsParser:
    """Parses Google Docs documents"""
    
    def __init__(self):
        self.supported_formats = ['google_doc', 'gdoc']
        self.scopes = ['https://www.googleapis.com/auth/documents.readonly']
        self.service = None
        self._credentials = None
    
    async def parse(self, doc_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Parse Google Docs document"""
        
        if options is None:
            options = {}
        
        logger.info("Starting Google Docs parsing", doc_id=doc_id, options=options)
        
        try:
            # Initialize Google Docs API service
            await self._initialize_service()
            
            if not self.service:
                return self._create_placeholder_result(doc_id, "Google Docs API not configured")
            
            # Fetch document
            document = self.service.documents().get(documentId=doc_id).execute()
            
            # Extract content and structure
            content = self._extract_text_content(document)
            title = document.get('title', 'Untitled Google Doc')
            metadata = self._extract_metadata(document)
            structure = self._extract_structure(document)
            
            result = {
                "title": title,
                "content": content,
                "metadata": metadata,
                "structure": structure,
                "stats": {
                    "word_count": len(content.split()),
                    "character_count": len(content),
                    "paragraph_count": len(structure.get("paragraphs", [])),
                    "heading_count": len(structure.get("headings", []))
                }
            }
            
            logger.info("Google Docs parsing completed successfully",
                       doc_id=doc_id,
                       title=title,
                       word_count=result["stats"]["word_count"])
            
            return result
            
        except Exception as e:
            logger.error("Google Docs parsing failed", doc_id=doc_id, error=str(e))
            return self._create_placeholder_result(doc_id, str(e))
    
    async def _initialize_service(self):
        """Initialize Google Docs API service"""
        
        try:
            # Check for credentials
            creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', '/app/credentials/google_credentials.json')
            token_path = os.getenv('GOOGLE_TOKEN_PATH', '/app/credentials/google_token.json')
            
            creds = None
            
            # Load existing token
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, self.scopes)
            
            # If no valid credentials, try to get them
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif os.path.exists(creds_path):
                    flow = InstalledAppFlow.from_client_secrets_file(creds_path, self.scopes)
                    # For server environment, we can't do interactive auth
                    logger.warning("Google Docs credentials need manual setup")
                    return
                else:
                    logger.warning("Google Docs credentials not found", 
                                 creds_path=creds_path)
                    return
            
            # Save credentials for next run
            if creds and creds.valid:
                os.makedirs(os.path.dirname(token_path), exist_ok=True)
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            # Build service
            self.service = build('docs', 'v1', credentials=creds)
            self._credentials = creds
            
            logger.info("Google Docs API service initialized")
            
        except Exception as e:
            logger.warning("Failed to initialize Google Docs service", error=str(e))
            self.service = None
    
    def _extract_text_content(self, document: Dict[str, Any]) -> str:
        """Extract plain text content from Google Docs document"""
        
        content_parts = []
        
        try:
            body = document.get('body', {})
            content = body.get('content', [])
            
            for element in content:
                if 'paragraph' in element:
                    paragraph_text = self._extract_paragraph_text(element['paragraph'])
                    if paragraph_text.strip():
                        content_parts.append(paragraph_text)
                elif 'table' in element:
                    table_text = self._extract_table_text(element['table'])
                    if table_text.strip():
                        content_parts.append(table_text)
            
            return '\n\n'.join(content_parts)
            
        except Exception as e:
            logger.error("Failed to extract text content", error=str(e))
            return ""
    
    def _extract_paragraph_text(self, paragraph: Dict[str, Any]) -> str:
        """Extract text from a paragraph element"""
        
        text_parts = []
        
        try:
            elements = paragraph.get('elements', [])
            
            for element in elements:
                if 'textRun' in element:
                    text_run = element['textRun']
                    content = text_run.get('content', '')
                    text_parts.append(content)
                elif 'inlineObjectElement' in element:
                    # Handle inline objects (images, etc.)
                    text_parts.append('[INLINE_OBJECT]')
                elif 'pageBreak' in element:
                    text_parts.append('\n---PAGE_BREAK---\n')
            
            return ''.join(text_parts).strip()
            
        except Exception as e:
            logger.warning("Failed to extract paragraph text", error=str(e))
            return ""
    
    def _extract_table_text(self, table: Dict[str, Any]) -> str:
        """Extract text from a table element"""
        
        table_parts = []
        
        try:
            rows = table.get('tableRows', [])
            
            for row in rows:
                row_cells = []
                cells = row.get('tableCells', [])
                
                for cell in cells:
                    cell_content = []
                    content = cell.get('content', [])
                    
                    for element in content:
                        if 'paragraph' in element:
                            cell_text = self._extract_paragraph_text(element['paragraph'])
                            if cell_text:
                                cell_content.append(cell_text)
                    
                    row_cells.append(' '.join(cell_content))
                
                if row_cells:
                    table_parts.append(' | '.join(row_cells))
            
            return '\n'.join(table_parts)
            
        except Exception as e:
            logger.warning("Failed to extract table text", error=str(e))
            return ""
    
    def _extract_metadata(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from Google Docs document"""
        
        metadata = {
            "document_id": document.get('documentId'),
            "title": document.get('title'),
            "revision_id": document.get('revisionId'),
            "parser": "google_docs_api"
        }
        
        # Extract document style information
        if 'documentStyle' in document:
            doc_style = document['documentStyle']
            metadata['document_style'] = {
                "background_color": doc_style.get('background', {}).get('color'),
                "page_size": doc_style.get('pageSize'),
                "margin_top": doc_style.get('marginTop'),
                "margin_bottom": doc_style.get('marginBottom'),
                "margin_left": doc_style.get('marginLeft'),
                "margin_right": doc_style.get('marginRight')
            }
        
        # Extract named styles
        if 'namedStyles' in document:
            metadata['named_styles'] = len(document['namedStyles'].get('styles', []))
        
        # Extract inline objects (images, etc.)
        if 'inlineObjects' in document:
            metadata['inline_objects_count'] = len(document['inlineObjects'])
        
        # Extract lists
        if 'lists' in document:
            metadata['lists_count'] = len(document['lists'])
        
        return metadata
    
    def _extract_structure(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract document structure information"""
        
        structure = {
            "paragraphs": [],
            "headings": [],
            "tables": [],
            "lists": [],
            "images": []
        }
        
        try:
            body = document.get('body', {})
            content = body.get('content', [])
            
            for idx, element in enumerate(content):
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    paragraph_info = self._analyze_paragraph_structure(paragraph, idx)
                    structure["paragraphs"].append(paragraph_info)
                    
                    # Check if it's a heading
                    if paragraph_info.get("is_heading"):
                        structure["headings"].append(paragraph_info)
                
                elif 'table' in element:
                    table = element['table']
                    table_info = self._analyze_table_structure(table, idx)
                    structure["tables"].append(table_info)
            
            # Extract list information
            if 'lists' in document:
                for list_id, list_data in document['lists'].items():
                    list_info = {
                        "list_id": list_id,
                        "nesting_levels": len(list_data.get('listProperties', {}).get('nestingLevels', []))
                    }
                    structure["lists"].append(list_info)
            
            # Extract inline objects (images)
            if 'inlineObjects' in document:
                for obj_id, obj_data in document['inlineObjects'].items():
                    if 'inlineObjectProperties' in obj_data:
                        props = obj_data['inlineObjectProperties']
                        if 'embeddedObject' in props:
                            embedded = props['embeddedObject']
                            image_info = {
                                "object_id": obj_id,
                                "title": embedded.get('title', ''),
                                "description": embedded.get('description', ''),
                                "image_properties": embedded.get('imageProperties', {})
                            }
                            structure["images"].append(image_info)
            
            return structure
            
        except Exception as e:
            logger.error("Failed to extract document structure", error=str(e))
            return structure
    
    def _analyze_paragraph_structure(self, paragraph: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Analyze paragraph structure and styling"""
        
        info = {
            "index": index,
            "text_length": 0,
            "is_heading": False,
            "heading_level": None,
            "alignment": None,
            "indent": None,
            "line_spacing": None
        }
        
        try:
            # Extract text length
            elements = paragraph.get('elements', [])
            total_text = ''
            for element in elements:
                if 'textRun' in element:
                    total_text += element['textRun'].get('content', '')
            
            info["text_length"] = len(total_text.strip())
            
            # Check paragraph style
            if 'paragraphStyle' in paragraph:
                style = paragraph['paragraphStyle']
                
                # Check if it's a heading
                named_style_type = style.get('namedStyleType', '')
                if 'HEADING' in named_style_type:
                    info["is_heading"] = True
                    # Extract heading level (HEADING_1, HEADING_2, etc.)
                    if '_' in named_style_type:
                        try:
                            level = int(named_style_type.split('_')[1])
                            info["heading_level"] = level
                        except (ValueError, IndexError):
                            pass
                
                # Extract other style properties
                info["alignment"] = style.get('alignment')
                info["indent"] = {
                    "start": style.get('indentStart'),
                    "end": style.get('indentEnd'),
                    "first_line": style.get('indentFirstLine')
                }
                info["line_spacing"] = style.get('lineSpacing')
            
            return info
            
        except Exception as e:
            logger.warning("Failed to analyze paragraph structure", error=str(e))
            return info
    
    def _analyze_table_structure(self, table: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Analyze table structure"""
        
        info = {
            "index": index,
            "rows": 0,
            "columns": 0,
            "total_cells": 0
        }
        
        try:
            rows = table.get('tableRows', [])
            info["rows"] = len(rows)
            
            if rows:
                # Count columns from first row
                first_row_cells = rows[0].get('tableCells', [])
                info["columns"] = len(first_row_cells)
                
                # Count total cells
                total_cells = 0
                for row in rows:
                    total_cells += len(row.get('tableCells', []))
                info["total_cells"] = total_cells
            
            return info
            
        except Exception as e:
            logger.warning("Failed to analyze table structure", error=str(e))
            return info
    
    def _create_placeholder_result(self, doc_id: str, error_message: str) -> Dict[str, Any]:
        """Create placeholder result when parsing fails"""
        
        return {
            "title": f"Google Doc {doc_id}",
            "content": f"Google Docs parsing not available: {error_message}\n\nTo enable Google Docs parsing:\n1. Set up Google Cloud credentials\n2. Enable Google Docs API\n3. Configure authentication",
            "metadata": {
                "document_id": doc_id,
                "error": error_message,
                "parser": "google_docs_placeholder"
            },
            "structure": {
                "paragraphs": [],
                "headings": [],
                "tables": [],
                "lists": [],
                "images": []
            },
            "stats": {
                "word_count": 0,
                "character_count": 0,
                "error": True
            }
        }
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported formats"""
        return self.supported_formats 