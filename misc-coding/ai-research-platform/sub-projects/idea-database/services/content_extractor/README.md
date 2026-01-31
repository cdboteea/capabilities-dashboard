# Content Extractor Service: Binary File Processing

## 🎯 Service Purpose & Architecture Role

The Content Extractor service handles **BINARY FILE PROCESSING ONLY** - converting files that cannot be read as plain text into readable content. It coordinates with the Pre-Processor service for all text normalization needs.

### ⚠️ CRITICAL ARCHITECTURAL BOUNDARY

**Content Extractor handles:**
- ✅ PDF → text extraction using PyPDF2
- ✅ Word documents → text extraction using python-docx
- ✅ Images → text extraction via OCR (tesseract)
- ✅ File format detection and metadata extraction
- ✅ Gmail attachment download/upload coordination
- ✅ Background job processing for automation
- ✅ Manual file processing API endpoints

**Content Extractor does NOT handle:**
- ❌ HTML → markdown conversion (Pre-Processor handles this)
- ❌ Plain text → formatted markdown (Pre-Processor handles this)
- ❌ YAML front-matter injection (Pre-Processor handles this)
- ❌ Text chunking and language detection (Pre-Processor handles this)

### 🔗 Service Integration Pattern

```
Binary Files → Content Extractor (extract raw text) → Pre-Processor (normalize text) → AI Processor
```

**Example Processing Flow:**
1. PDF attachment received via Gmail
2. Content Extractor: Extracts raw text from PDF
3. Content Extractor calls Pre-Processor: Converts raw text to markdown with metadata
4. Pre-Processor returns formatted content for AI analysis

**DO NOT duplicate text processing in this service!**

## ✅ Current Implementation Status (as of 2025-07-17)

- **Service:** FastAPI, Dockerized, port 3005:8000, on ai_platform network
- **Status:** ✅ PRODUCTION READY with full functionality
- **Integration:** Successfully integrated with Pre-Processor service
- **Background Processing:** 10-second polling for Gmail attachments
- **Manual Processing:** API endpoints for user-triggered conversion

### 🚀 Implemented Features

#### 1. Binary File Processing
- ✅ **PDF Processing:** PyPDF2 with page-by-page extraction
- ✅ **Word Documents:** python-docx with table support  
- ✅ **Image OCR:** pytesseract with confidence scoring
- ✅ **File Detection:** python-magic for MIME type identification
- ✅ **Error Handling:** Graceful fallback for processing failures

#### 2. Automatic Gmail Workflow  
- ✅ **Background Jobs:** 10-second polling for pending conversions
- ✅ **Drive Upload:** Coordination with Email Processor for file storage
- ✅ **Hash Deduplication:** Prevents duplicate file processing
- ✅ **Retry Logic:** Configurable retry policy for failed jobs
- ✅ **Database Integration:** asyncpg connection pooling

#### 3. Manual Processing APIs
- ✅ **File Upload:** `/manual/process-file` for user-triggered conversion
- ✅ **Text Processing:** `/manual/process-text` (delegates to Pre-Processor)
- ✅ **Format Support:** PDF, DOCX, Images, HTML, plain text
- ✅ **Real-time Response:** Immediate processing with status feedback

#### 4. Pre-Processor Integration
- ✅ **HTTP Client:** PreProcessorClient for service communication
- ✅ **Text Delegation:** HTML/text files sent to Pre-Processor for normalization
- ✅ **Error Handling:** Graceful fallback for Pre-Processor unavailability
- ✅ **Response Handling:** Proper parsing of normalized markdown content

## 📡 API Endpoints

### GET `/health`
Service health check with status information.

**Response:**
```json
{
  "status": "healthy",
  "service": "content_extractor", 
  "version": "1.0.0"
}
```

### POST `/manual/process-file`
Manual file processing for user uploads.

**Request:** Multipart form data
- `file`: File upload (PDF, DOCX, Images, HTML, Text)
- `idea_id`: Optional identifier (default: "manual")
- `source`: Optional source name (default: "manual_upload")

**Response:**
```json
{
  "success": true,
  "processing_type": "binary_converted|pre_processor_normalized",
  "markdown_content": "# Document Title\n\nExtracted content...",
  "metadata": {
    "original_filename": "document.pdf",
    "mime_type": "application/pdf",
    "file_size": 1048576,
    "processing_info": {...}
  }
}
```

### POST `/manual/process-text`
Manual text processing (delegates to Pre-Processor).

**Request:**
```json
{
  "content": "Text or HTML content",
  "idea_id": "manual",
  "source": "manual_text", 
  "content_type": "text/html"
}
```

**Response:**
```json
{
  "success": true,
  "processing_type": "text_normalized",
  "markdown_content": "---\nidea_id: manual\n---\n\n# Content...",
  "metadata": {
    "original_content_length": 150,
    "content_type": "text/html"
  }
}
```

### Background Processing
Automatic Gmail attachment processing via background jobs:
- Downloads attachments from Gmail
- Uploads to Google Drive for user access
- Processes files for AI analysis (optional)
- Updates database with processing status

## 🛠️ Technical Implementation

### Dependencies
- **FastAPI:** Async HTTP API framework
- **PyPDF2:** PDF text extraction
- **python-docx:** Word document processing
- **pytesseract:** OCR text extraction from images
- **python-magic:** File type detection
- **httpx:** HTTP client for Pre-Processor integration
- **asyncpg:** PostgreSQL async database operations
- **structlog:** Structured logging

### File Processing Pipeline
1. **File Detection:** MIME type identification with python-magic
2. **Binary Processing:** Specialized extraction based on file type
3. **Text Delegation:** HTML/text files sent to Pre-Processor
4. **Metadata Collection:** File size, processing info, extraction details
5. **Error Handling:** Graceful fallback with error reporting

### Background Job System
- **ConversionJobProcessor:** Main background processing class
- **Database Polling:** 10-second intervals for pending jobs
- **Gmail Integration:** Downloads via Email Processor API
- **Drive Upload:** Coordination for file storage
- **Error Recovery:** Retry logic with exponential backoff

## 🔧 Configuration

### Environment Variables
```bash
POSTGRES_URL=postgresql://user:pass@host:5432/db
EMAIL_PROCESSOR_HOST=idea_db_email_processor
PRE_PROCESSOR_HOST=idea_db_pre_processor
CONTENT_EXTRACTOR_PORT=8000
```

### Service Discovery
- **Container Name:** `idea_db_content_extractor`
- **Network:** `ai_platform`
- **Port:** `3005:8000`
- **Health Check:** `curl http://localhost:3005/health`

### System Dependencies (Docker)
```dockerfile
# Required system packages
libmagic1          # File type detection
libmagic-dev       # Magic library development headers
tesseract-ocr      # OCR engine
tesseract-ocr-eng  # English OCR language pack
poppler-utils      # PDF utilities
```

## 🚨 Important Notes for Developers

### ⚠️ DO NOT DUPLICATE PRE-PROCESSOR FUNCTIONALITY

This service focuses on **binary file conversion only**. For all text processing:

1. **Use Pre-Processor API** for HTML/text normalization
2. **Never import markdownify** in this service
3. **Delegate text processing** to Pre-Processor service
4. **Focus on binary formats** (PDF, Word, Images)

### 🔄 Integration Pattern Example
```python
# ✅ CORRECT - Binary file processing with Pre-Processor delegation
async def process_file(file_content, filename, mime_type):
    if mime_type in ['text/html', 'text/plain']:
        # Delegate to Pre-Processor
        raw_content = file_content.decode('utf-8')
        return await self.pre_processor_client.normalize_content(
            raw_content, idea_id, source
        )
    else:
        # Handle binary file processing here
        return await self.file_converter.convert_to_markdown(
            file_content, filename, mime_type
        )

# ❌ WRONG - Don't duplicate Pre-Processor functionality
from markdownify import markdownify  # Never import this!
```

## 🧪 Testing

### Manual API Testing
```bash
# Test file upload processing
curl -X POST http://localhost:3005/manual/process-file \
  -F "file=@document.pdf" \
  -F "idea_id=test_123"

# Test text processing (delegates to Pre-Processor)
curl -X POST http://localhost:3005/manual/process-text \
  -H "Content-Type: application/json" \
  -d '{"content": "<h1>Test</h1><p>Content</p>", "idea_id": "test"}'
```

### Integration Testing
1. **Upload various file types** through manual processing API
2. **Verify Pre-Processor delegation** for HTML/text files
3. **Test background job processing** with Gmail attachments
4. **Check error handling** with malformed files

### Supported File Formats
- **PDF:** ✅ Text extraction with page separation
- **Word (DOCX):** ✅ Text, tables, and basic formatting
- **Images (JPEG, PNG, GIF, BMP, TIFF):** ✅ OCR text extraction
- **HTML:** ✅ Delegates to Pre-Processor for markdown conversion
- **Plain Text:** ✅ Delegates to Pre-Processor for formatting

## 📊 Performance Characteristics

- **PDF Processing:** ~2-5 seconds for typical documents
- **Word Processing:** ~1-3 seconds for standard documents
- **Image OCR:** ~5-15 seconds depending on image complexity
- **Background Jobs:** 10-second polling interval
- **Memory Usage:** Optimized with streaming and temporary file cleanup
- **Concurrent Processing:** Async support for multiple simultaneous requests

## 🔗 Service Dependencies

### Required Services
- **Pre-Processor:** Text normalization and markdown conversion
- **Email Processor:** Gmail attachment download/upload coordination
- **PostgreSQL:** Background job storage and status tracking

### Optional Services
- **AI Processor:** Downstream processing of converted content
- **Web Interface:** UI for manual processing triggers (planned)

## 📚 Documentation References

- **Pre-Processor Service:** [README.md](../pre_processor/README.md)
- **Service Architecture:** [DOCKER_ARCHITECTURE.md](../../../docs/DOCKER_ARCHITECTURE.md)
- **API Integration:** [TECHNICAL_SPECS.md](../../../docs/TECHNICAL_SPECS.md)

---

**Last Updated:** 2025-07-17  
**Status:** ✅ Production Ready - Binary File Processing Authority  
**Next Steps:** Add UI buttons for manual processing integration 