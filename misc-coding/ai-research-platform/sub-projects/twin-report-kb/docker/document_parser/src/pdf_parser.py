#!/usr/bin/env python3
"""
PDF Parser for Document Parser
Extracts text, metadata, and structure from PDF documents
"""

import io
from typing import Dict, List, Any, Optional
import asyncio

import PyPDF2
import pdfplumber
import structlog

logger = structlog.get_logger(__name__)

class PDFParser:
    """Parses PDF documents and extracts content"""
    
    def __init__(self):
        self.supported_formats = ['pdf']
    
    async def parse(self, pdf_content: bytes, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Parse PDF content and extract text, metadata, and structure"""
        
        if options is None:
            options = {}
        
        logger.info("Starting PDF parsing", 
                   content_size=len(pdf_content),
                   options=options)
        
        try:
            # Use both PyPDF2 and pdfplumber for comprehensive extraction
            pypdf_result = await self._parse_with_pypdf2(pdf_content, options)
            plumber_result = await self._parse_with_pdfplumber(pdf_content, options)
            
            # Combine results, preferring pdfplumber for text and PyPDF2 for metadata
            combined_result = {
                "title": pypdf_result.get("title") or plumber_result.get("title", "Untitled PDF"),
                "content": plumber_result.get("content") or pypdf_result.get("content", ""),
                "metadata": {
                    **pypdf_result.get("metadata", {}),
                    **plumber_result.get("metadata", {}),
                    "parser_info": {
                        "pypdf2_pages": pypdf_result.get("page_count", 0),
                        "pdfplumber_pages": plumber_result.get("page_count", 0),
                        "primary_parser": "pdfplumber" if plumber_result.get("content") else "pypdf2"
                    }
                },
                "structure": {
                    "pages": plumber_result.get("structure", {}).get("pages", []),
                    "tables": plumber_result.get("structure", {}).get("tables", []),
                    "images": plumber_result.get("structure", {}).get("images", []),
                    "bookmarks": pypdf_result.get("structure", {}).get("bookmarks", [])
                },
                "stats": {
                    "page_count": max(
                        pypdf_result.get("page_count", 0),
                        plumber_result.get("page_count", 0)
                    ),
                    "word_count": len((plumber_result.get("content") or pypdf_result.get("content", "")).split()),
                    "character_count": len(plumber_result.get("content") or pypdf_result.get("content", "")),
                    "table_count": len(plumber_result.get("structure", {}).get("tables", [])),
                    "image_count": len(plumber_result.get("structure", {}).get("images", []))
                }
            }
            
            logger.info("PDF parsing completed successfully",
                       page_count=combined_result["stats"]["page_count"],
                       word_count=combined_result["stats"]["word_count"])
            
            return combined_result
            
        except Exception as e:
            logger.error("PDF parsing failed", error=str(e))
            return {
                "title": "PDF Parsing Failed",
                "content": f"Error parsing PDF: {str(e)}",
                "metadata": {"error": str(e)},
                "structure": {},
                "stats": {"error": True}
            }
    
    async def _parse_with_pypdf2(self, pdf_content: bytes, options: Dict[str, Any]) -> Dict[str, Any]:
        """Parse PDF using PyPDF2 library"""
        
        try:
            pdf_stream = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            # Extract metadata
            metadata = {}
            if pdf_reader.metadata:
                metadata.update({
                    "title": pdf_reader.metadata.get("/Title", ""),
                    "author": pdf_reader.metadata.get("/Author", ""),
                    "subject": pdf_reader.metadata.get("/Subject", ""),
                    "creator": pdf_reader.metadata.get("/Creator", ""),
                    "producer": pdf_reader.metadata.get("/Producer", ""),
                    "creation_date": str(pdf_reader.metadata.get("/CreationDate", "")),
                    "modification_date": str(pdf_reader.metadata.get("/ModDate", ""))
                })
            
            # Extract text content
            content_parts = []
            page_info = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        content_parts.append(page_text)
                        page_info.append({
                            "page_number": page_num + 1,
                            "text_length": len(page_text),
                            "has_text": bool(page_text.strip())
                        })
                except Exception as e:
                    logger.warning("Failed to extract text from page", 
                                 page_number=page_num + 1, 
                                 error=str(e))
                    page_info.append({
                        "page_number": page_num + 1,
                        "text_length": 0,
                        "has_text": False,
                        "error": str(e)
                    })
            
            # Extract bookmarks/outline
            bookmarks = []
            if hasattr(pdf_reader, 'outline') and pdf_reader.outline:
                bookmarks = self._extract_bookmarks(pdf_reader.outline)
            
            return {
                "title": metadata.get("title", ""),
                "content": "\n\n".join(content_parts),
                "metadata": metadata,
                "structure": {
                    "pages": page_info,
                    "bookmarks": bookmarks
                },
                "page_count": len(pdf_reader.pages)
            }
            
        except Exception as e:
            logger.error("PyPDF2 parsing failed", error=str(e))
            return {"error": str(e)}
    
    async def _parse_with_pdfplumber(self, pdf_content: bytes, options: Dict[str, Any]) -> Dict[str, Any]:
        """Parse PDF using pdfplumber library for better text and table extraction"""
        
        try:
            pdf_stream = io.BytesIO(pdf_content)
            
            with pdfplumber.open(pdf_stream) as pdf:
                content_parts = []
                page_info = []
                tables = []
                images = []
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # Extract text
                        page_text = page.extract_text()
                        if page_text:
                            content_parts.append(page_text)
                        
                        # Extract tables
                        page_tables = page.extract_tables()
                        for table_idx, table in enumerate(page_tables):
                            if table:
                                tables.append({
                                    "page": page_num + 1,
                                    "table_index": table_idx,
                                    "rows": len(table),
                                    "columns": len(table[0]) if table else 0,
                                    "data": table if options.get("include_table_data", False) else None
                                })
                        
                        # Extract images info
                        page_images = page.images
                        for img_idx, img in enumerate(page_images):
                            images.append({
                                "page": page_num + 1,
                                "image_index": img_idx,
                                "x0": img.get("x0"),
                                "y0": img.get("y0"),
                                "x1": img.get("x1"),
                                "y1": img.get("y1"),
                                "width": img.get("width"),
                                "height": img.get("height")
                            })
                        
                        page_info.append({
                            "page_number": page_num + 1,
                            "text_length": len(page_text) if page_text else 0,
                            "has_text": bool(page_text and page_text.strip()),
                            "table_count": len(page_tables),
                            "image_count": len(page_images),
                            "width": page.width,
                            "height": page.height
                        })
                        
                    except Exception as e:
                        logger.warning("Failed to extract from page with pdfplumber", 
                                     page_number=page_num + 1, 
                                     error=str(e))
                        page_info.append({
                            "page_number": page_num + 1,
                            "text_length": 0,
                            "has_text": False,
                            "error": str(e)
                        })
                
                # Combine all text
                full_content = "\n\n".join(content_parts)
                
                return {
                    "title": "",  # pdfplumber doesn't extract metadata
                    "content": full_content,
                    "metadata": {
                        "total_pages": len(pdf.pages),
                        "parser": "pdfplumber"
                    },
                    "structure": {
                        "pages": page_info,
                        "tables": tables,
                        "images": images
                    },
                    "page_count": len(pdf.pages)
                }
                
        except Exception as e:
            logger.error("pdfplumber parsing failed", error=str(e))
            return {"error": str(e)}
    
    def _extract_bookmarks(self, outline, level: int = 0) -> List[Dict[str, Any]]:
        """Extract bookmarks/outline from PDF"""
        
        bookmarks = []
        
        try:
            for item in outline:
                if isinstance(item, list):
                    # Nested bookmark
                    bookmarks.extend(self._extract_bookmarks(item, level + 1))
                else:
                    # Individual bookmark
                    bookmark = {
                        "title": str(item.title) if hasattr(item, 'title') else str(item),
                        "level": level
                    }
                    
                    if hasattr(item, 'page') and item.page:
                        bookmark["page"] = item.page.idnum if hasattr(item.page, 'idnum') else None
                    
                    bookmarks.append(bookmark)
                    
        except Exception as e:
            logger.warning("Failed to extract bookmarks", error=str(e))
        
        return bookmarks
    
    async def extract_text_from_page(self, pdf_content: bytes, page_number: int) -> str:
        """Extract text from a specific page"""
        
        try:
            pdf_stream = io.BytesIO(pdf_content)
            
            with pdfplumber.open(pdf_stream) as pdf:
                if 0 <= page_number - 1 < len(pdf.pages):
                    page = pdf.pages[page_number - 1]
                    return page.extract_text() or ""
                else:
                    raise ValueError(f"Page {page_number} does not exist")
                    
        except Exception as e:
            logger.error("Failed to extract text from page", 
                        page_number=page_number, 
                        error=str(e))
            return ""
    
    async def extract_tables_from_page(self, pdf_content: bytes, page_number: int) -> List[List[List[str]]]:
        """Extract tables from a specific page"""
        
        try:
            pdf_stream = io.BytesIO(pdf_content)
            
            with pdfplumber.open(pdf_stream) as pdf:
                if 0 <= page_number - 1 < len(pdf.pages):
                    page = pdf.pages[page_number - 1]
                    return page.extract_tables()
                else:
                    raise ValueError(f"Page {page_number} does not exist")
                    
        except Exception as e:
            logger.error("Failed to extract tables from page", 
                        page_number=page_number, 
                        error=str(e))
            return []
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return self.supported_formats 