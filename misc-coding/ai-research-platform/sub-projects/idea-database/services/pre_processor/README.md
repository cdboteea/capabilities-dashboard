# Pre-Processor Service: Text Normalization & Chunking

## 🎯 Service Purpose & Architecture Role

The Pre-Processor service is responsible for **ALL TEXT NORMALIZATION** in the AI Research Platform. It handles conversion of text content (HTML, plain text, etc.) to standardized markdown format with YAML front-matter and semantic chunking for LLM processing.

### ⚠️ CRITICAL ARCHITECTURAL BOUNDARY

**Pre-Processor handles:** 
- ✅ HTML → markdown conversion using markdownify
- ✅ Plain text → formatted markdown  
- ✅ YAML front-matter injection (idea_id, source, timestamps)
- ✅ Semantic chunking (by headings, paragraphs, with overlap)
- ✅ Language detection and metadata enrichment
- ✅ Deduplication by content hash

**Pre-Processor does NOT handle:**
- ❌ Binary file processing (PDF, Word, Images) → Content Extractor handles this
- ❌ Drive upload/download → Email Processor handles this
- ❌ File storage management → Other services handle this

### 🔗 Service Integration Pattern

```
Email Content → Pre-Processor → AI Processor
Binary Files → Content Extractor → Pre-Processor → AI Processor
Manual Text → Content Extractor → Pre-Processor → AI Processor
```

**DO NOT duplicate HTML/text processing in other services!**

## ✅ Current Implementation Status (as of 2025-07-17)

- **Service:** FastAPI, Dockerized, port 3006:8000, on ai_platform network
- **Status:** ✅ PRODUCTION READY with full functionality
- **Endpoints:** All operational with complete feature set
- **Integration:** Successfully integrated with Content Extractor service
- **Testing:** Verified working with live content processing

### 🚀 Implemented Features

#### 1. Text Normalization (`/normalize`)
- ✅ HTML → clean markdown conversion using markdownify
- ✅ Plain text → formatted markdown
- ✅ YAML front-matter injection with metadata
- ✅ Input validation and size limits (1MB max)
- ✅ Error handling for malformed content
- ✅ Redis event publishing for downstream processing

#### 2. Semantic Chunking (`/chunk`)
- ✅ Intelligent splitting by headings (H2/H3 sections)
- ✅ Paragraph-based fallback chunking
- ✅ Configurable chunk size (4000 chars max, 400 chars overlap)
- ✅ Deduplication by SHA1 hash
- ✅ Language detection per chunk
- ✅ Token counting and metadata enrichment
- ✅ YAML front-matter removal before chunking

#### 3. Service Integration
- ✅ Content Extractor integration via HTTP API
- ✅ Redis event publishing for AI Processor
- ✅ Async request handling with FastAPI
- ✅ Comprehensive error handling and logging

## 📡 API Endpoints

### POST `/normalize`
Converts text content to standardized markdown with YAML front-matter.

**Request:**
```json
{
  "idea_id": "string",
  "source": "string", 
  "payload": "string (HTML or plain text)"
}
```

**Response:**
```json
{
  "markdown": "---\nidea_id: xyz\nsource: email\ncreated_at: 2025-07-17T...\n---\n\n# Content..."
}
```

### POST `/chunk`
Splits markdown into semantic chunks for LLM processing.

**Request:**
```json
{
  "idea_id": "string",
  "markdown": "string (markdown with YAML front-matter)"
}
```

**Response:**
```json
[
  {
    "chunk_id": "string",
    "idea_id": "string", 
    "order": 0,
    "text": "string",
    "token_count": 150,
    "lang": "en",
    "hash": "sha1_hash",
    "created_at": "2025-07-17T..."
  }
]
```

### GET `/health`
Service health check.

## 🛠️ Technical Implementation

### Dependencies
- FastAPI for async HTTP API
- markdownify for HTML→markdown conversion
- PyYAML for front-matter injection
- langdetect for language identification  
- redis for event publishing
- pydantic for request validation

### Processing Pipeline
1. **Input Validation** - Size limits, content type validation
2. **Content Detection** - HTML vs plain text identification
3. **Normalization** - markdownify conversion or text formatting
4. **Metadata Injection** - YAML front-matter with timestamps
5. **Event Publishing** - Redis notification for downstream services

### Performance
- **Max Input Size:** 1MB per request
- **Processing Time:** <100ms for typical content
- **Chunking:** 4000 char max chunks with 400 char overlap
- **Memory Usage:** Minimal footprint with streaming processing

## 🔧 Configuration

### Environment Variables
```bash
REDIS_URL=redis://localhost:6379/0
EVENT_CHANNEL=idea.events
MAX_INPUT_SIZE=1048576  # 1MB
```

### Service Discovery
- **Container Name:** `idea_db_pre_processor`
- **Network:** `ai_platform`
- **Port:** `3006:8000`
- **Health Check:** `curl http://localhost:3006/health`

## 🚨 Important Notes for Developers

### ⚠️ DO NOT DUPLICATE FUNCTIONALITY
This service is the **SINGLE SOURCE OF TRUTH** for text normalization. Do not implement HTML→markdown conversion in other services. Instead:

1. **Use this service** via HTTP API for all text processing
2. **Content Extractor** should call `/normalize` for HTML/text files
3. **Email Processor** should call `/normalize` for email content
4. **Other services** should integrate via the API, not duplicate logic

### 🔄 Integration Pattern Example
```python
# ✅ CORRECT - Use Pre-Processor API
async def process_html_content(html_content, idea_id):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://idea_db_pre_processor:8000/normalize",
            json={
                "idea_id": idea_id,
                "source": "content_extractor", 
                "payload": html_content
            }
        )
        return response.json()["markdown"]

# ❌ WRONG - Don't duplicate markdownify
from markdownify import markdownify  # Don't do this!
```

## 🧪 Testing

### Manual Testing
```bash
# Test normalization
curl -X POST http://localhost:3006/normalize \
  -H "Content-Type: application/json" \
  -d '{"idea_id": "test", "source": "manual", "payload": "<h1>Test</h1><p>Content</p>"}'

# Test chunking  
curl -X POST http://localhost:3006/chunk \
  -H "Content-Type: application/json" \
  -d '{"idea_id": "test", "markdown": "# Test\n\nLong content..."}'
```

### Integration Testing
Verify integration with Content Extractor by uploading HTML files through the manual processing API.

## 📚 Documentation References

- **Service Architecture:** [DOCKER_ARCHITECTURE.md](../../../docs/DOCKER_ARCHITECTURE.md)
- **API Integration:** [TECHNICAL_SPECS.md](../../../docs/TECHNICAL_SPECS.md)  
- **Content Processing:** Content Extractor service documentation

---

**Last Updated:** 2025-07-17  
**Status:** ✅ Production Ready - Fully Functional  
**Next Steps:** Monitor integration usage and optimize performance as needed 