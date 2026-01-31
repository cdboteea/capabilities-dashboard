# Attachment Storage Architecture

**Version:** 2.0  
**Date:** December 2024  
**Status:** Implementation Ready

## Overview

The Idea Database implements a hybrid attachment storage system combining PostgreSQL metadata with Google Drive file storage, ensuring data persistence and efficient LLM integration through markdown conversion.

## Architecture Components

### 1. Storage Layer

#### **PostgreSQL Database**
- **Metadata Storage**: filename, size, type, processing status
- **Reference Storage**: Google Drive file IDs, content hashes
- **Search Indexes**: Full-text search on converted markdown content

#### **Google Drive Storage**
- **File Organization**: `/Idea-Database-Attachments/{idea_id}/{filename}`
- **Access Control**: Service account with Drive API access
- **Deduplication**: Content-based hashing prevents duplicate storage

### 2. Processing Pipeline (Updated Implementation)

```
Email Processing → Attachment Metadata Storage → Conversion Job Creation
                                                           ↓
Content Extractor (Background) → Download from Email API → File Processing
                                                               ↓
                      Database Update ← Drive Upload ← Format Conversion
```

#### **Step 1: Email Processing (Email Processor Service)**
- Extract attachment metadata from Gmail API
- Store attachment record in database with `pending` status
- **Automatically create conversion job** in `conversion_jobs` table
- Return attachment IDs to caller

#### **Step 2: Background Job Processing (Content Extractor Service)**
- Poll `conversion_jobs` table every 10 seconds for pending jobs
- Download attachment content via Email Processor `/drive/upload` endpoint
- Process file content based on MIME type

#### **Step 3: File Format Conversion**
- **PDFs**: PyMuPDF → structured markdown (placeholder)
- **Word Docs**: python-docx → markdownify (placeholder)
- **Images**: pytesseract OCR → markdown (placeholder)
- **Other**: Metadata extraction with type notation

#### **Step 4: Google Drive Upload**
- Upload processed content to Drive via Email Processor API
- Organize files in `/Idea-Database-Attachments/` structure
- Generate Drive file ID and shareable URL

#### **Step 5: Database Update**
- Update attachment record with Drive URLs and markdown content
- Mark conversion job as `completed` or `failed`
- Update conversion status and timestamps

### 3. Service Components

#### **GoogleDriveManager**
```python
class GoogleDriveManager:
    async def store_attachment(self, content, filename, idea_id) -> str
    async def retrieve_attachment(self, drive_file_id) -> bytes
    async def delete_attachment(self, drive_file_id) -> bool
    def _ensure_folder_structure(self, idea_id) -> str
```

#### **MarkdownConverter**
```python
class MarkdownConverter:
    async def convert_pdf(self, content) -> str
    async def convert_docx(self, content) -> str
    async def convert_image(self, content) -> str
    async def detect_and_convert(self, content, mime_type) -> str
```

#### **AttachmentProcessor**
```python
class AttachmentProcessor:
    async def process_gmail_attachment(self, message_id, attachment_id, idea_id)
    async def store_with_conversion(self, content, metadata, idea_id)
    async def get_attachment_content(self, attachment_id) -> Dict
```

## API Endpoints

### **Download Endpoint Enhancement**
```python
@app.get("/attachments/{att_id}/download")
async def download_attachment(att_id: str):
    # Option 1: Stream original file from Google Drive
    # Option 2: Return markdown content for LLM processing
    # Option 3: Return metadata with download links
```

### **New Processing Endpoints**
```python
@app.post("/attachments/{att_id}/reprocess")
async def reprocess_attachment(att_id: str)

@app.get("/attachments/{att_id}/markdown")
async def get_attachment_markdown(att_id: str)
```

## LLM Integration

### **Context Building**
```python
def build_llm_context(idea_id: str) -> str:
    context = f"""
    Email Content:
    {email_content}
    
    Attachments:
    {attachment_markdown_content}
    
    URLs:
    {processed_url_content}
    """
    return context
```

### **Mac Studio Endpoint Integration**
```python
class MacStudioLLM:
    def __init__(self):
        self.endpoint = "http://mac-studio-endpoint:8000/v1/chat/completions"
    
    async def process_with_attachments(self, idea_id: str, prompt: str):
        context = await self.build_context(idea_id)
        response = await self.call_llm(prompt, context)
        return response
```

## Security & Access Control

### **Google Drive Permissions**
- Service account with limited scope
- Folder-level access control
- Audit logging for file operations

### **Data Protection**
- Content hashing for integrity verification
- Encrypted storage through Google Drive
- Access logging and monitoring

## Performance Considerations

### **Optimization Strategies**
- Lazy loading of attachment content
- Caching of frequently accessed files
- Batch processing for multiple attachments
- Async processing pipeline

### **Resource Management**
- Memory-efficient streaming for large files
- Cleanup of temporary processing files
- Rate limiting for Google Drive API calls

## Monitoring & Logging

### **Key Metrics**
- Attachment processing success rate
- Google Drive API usage
- Markdown conversion accuracy
- Storage space utilization

### **Error Handling**
- Retry mechanisms for API failures
- Fallback to metadata-only storage
- User notification for processing failures

## Implementation Phases

### **Phase 1: Core Infrastructure**
1. Google Drive API integration
2. Enhanced Gmail attachment downloading
3. Basic markdown conversion (PDF focus)
4. Database schema updates

### **Phase 2: Advanced Processing**
1. Multi-format conversion support
2. OCR for image attachments
3. Content quality validation
4. Batch processing capabilities

### **Phase 3: LLM Integration**
1. Mac Studio endpoint integration
2. Context building optimization
3. Intelligent content summarization
4. Advanced search capabilities

## Configuration

### **Environment Variables**
```bash
GOOGLE_DRIVE_CREDENTIALS_PATH=/app/credentials/drive_service_account.json
GOOGLE_DRIVE_FOLDER_ID=1234567890abcdef
MAC_STUDIO_LLM_ENDPOINT=http://mac-studio:8000
ATTACHMENT_MAX_SIZE_MB=50
MARKDOWN_CONVERSION_TIMEOUT=300
```

### **Dependencies**
```txt
# Markdown Conversion
pymupdf>=1.23.0
python-docx>=0.8.11
python-pptx>=0.6.21
markdownify>=0.11.6
pytesseract>=0.3.10

# Google Drive
google-api-python-client>=2.100.0
google-auth>=2.23.0

# LLM Integration
openai>=1.0.0
aiohttp>=3.8.0
```

This architecture ensures reliable attachment storage, efficient processing, and seamless LLM integration while maintaining data integrity and user control. 