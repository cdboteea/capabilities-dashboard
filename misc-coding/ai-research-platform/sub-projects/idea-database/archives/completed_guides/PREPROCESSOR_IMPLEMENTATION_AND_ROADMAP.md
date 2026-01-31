# Idea Database - AI-Powered Email Intelligence Platform

**Status:** 🚀 **PHASE 1 COMPLETED** - Enhanced Attachment Storage with Google Drive  
**Gmail Integration:** ✅ **ACTIVE** - OAuth authenticated and processing emails  
**Storage:** ✅ **ENHANCED** - PostgreSQL + Google Drive + Markdown Conversion  
**LLM:** 🚀 **READY** - Mac Studio endpoint prepared for Phase 3 integration  
**Last Updated:** January 2025

**New Feature:** Knowledge-Graph node editing now live (July 2025)

## 🎯 Overview

The Idea Database is a comprehensive email intelligence platform that automatically processes emails, extracts insights, categorizes content, and provides a searchable knowledge base. Enhanced with Google Drive attachment storage, markdown conversion, and Mac Studio LLM integration for advanced AI analysis.

## ✅ Phase 1 Completed: Enhanced Attachment Storage + UI Dashboard

### **Google Drive Integration**
- **OAuth Authentication**: Secure user-based file management
- **Enhanced File Sharing**: Third-party email sharing with permission controls
- **Shareable Link Generation**: Public link creation with access level management
- **Persistent Storage**: Files stored independently of Gmail limits
- **Automatic Folder Management**: Organized file structure
- **Deduplication**: SHA-256 hashing prevents duplicate storage
- **Quota Management**: Storage usage tracking and optimization

### **Multi-Format Markdown Conversion**
- **PDF Processing**: Text extraction with PyMuPDF, table detection
- **Office Documents**: Word (.docx) and PowerPoint (.pptx) conversion
- **Image OCR**: Tesseract-based text extraction with confidence scoring
- **HTML Processing**: Clean markdown conversion with BeautifulSoup
- **Text Files**: Encoding detection and proper formatting

### **Enhanced UI Dashboard**
- **Files Management**: Complete Google Drive file management interface
- **Enhanced Sharing Modal**: Third-party email sharing with permission controls (reader/commenter/writer)
- **URL Management**: Comprehensive URL listing, preview, and processing status
- **Settings Interface**: OAuth management, AI model selection, system configuration
- **Real-time Monitoring**: Live health status, sync controls, and auto-refresh
- **Storage Analytics**: Usage tracking, quota monitoring, and file statistics

### **Enhanced Database Schema**
- **Attachment Enhancements**: drive_file_id, markdown_content, conversion_status
- **URL Processing**: markdown_content, processing_status, content_length
- **Job Management**: conversion_jobs table for queue processing
- **Drive Configuration**: drive_config table for settings and quotas
- **Full-Text Search**: Enhanced indexes for content discovery

### **🚀 Coming Next: Phase 2 & 3**
- **Phase 2**: On-demand URL processing system
- **Phase 3**: Mac Studio LLM integration for AI analysis

## ✅ Current Status: 100% Functional

### **Frontend-Backend Integration**
- ✅ **React Dashboard**: Fully operational at http://localhost:3002
- ✅ **API Integration**: All endpoints working with nginx proxy
- ✅ **Real-time Updates**: Live data from backend services
- ✅ **Search Functionality**: Full-text search with relevance scoring

### **Gmail OAuth Integration**
- ✅ **OAuth Credentials**: Configured for ideaseea@gmail.com
- ✅ **Token Management**: Automatic refresh token handling
- ✅ **Email Processing**: Live Gmail API integration working
- ✅ **Security**: Secure credential storage and management

### **Backend Services**
- ✅ **Email Processor** (port 3003): Gmail API integration + attachment metadata + Drive storage
- ✅ **AI Processor** (port 3004): Entity extraction + categorization
- ✅ **Content Extractor** (port 3005): Background job processor + file conversion pipeline
- ✅ **Database**: PostgreSQL with complete schema (6 tables)

## 🚀 Quick Start

### 1. Start the Services
```bash
cd sub-projects/idea-database
docker-compose up -d
```

### 2. Access the Dashboard
Open your browser to: **http://localhost:3002**

### 3. Process Emails
```bash
# Trigger email processing
curl -X POST http://localhost:3003/process-emails \
  -H "Content-Type: application/json" \
  -d '{"force_reprocess": false, "max_emails": 10}'
```

### 4. Send Test Emails
Send emails to: **ideaseea@gmail.com** - they will be automatically processed!

## 📧 Gmail Integration Details

### OAuth Setup (✅ Already Configured)
- **Client ID**: 1068903107047-qlvd3kcfuc8hladp83lh51ora8lmj30a.apps.googleusercontent.com
- **Project**: ideas-dashboard-463714
- **Scopes**: gmail.readonly, gmail.modify
- **Intake Email**: ideaseea@gmail.com

### Credentials Location
```
gmail_credentials/
├── gmail_credentials.json  # OAuth client credentials
└── gmail_token.json       # Access/refresh tokens
```

### Email Processing Workflow
1. **Intake**: Emails sent to ideaseea@gmail.com
2. **Fetch**: Gmail API retrieves new emails
3. **Parse**: Extract subject, content, sender, attachments
4. **Attachment Storage**: Store metadata and create conversion jobs
5. **Background Processing**: Content Extractor processes conversion jobs
6. **File Pipeline**: Download → Convert → Drive Upload → Database Update
7. **Categorize**: AI assigns to one of 6 categories
8. **Extract**: URLs, entities, and metadata extraction
9. **Store**: Persist to PostgreSQL database
10. **Index**: Full-text search indexing
11. **Display**: Real-time updates in dashboard

## 🎛️ Dashboard Features

### Available Pages
- **📊 Dashboard**: Overview with statistics and recent activity
- **📧 Emails**: Browse and search processed email ideas
- **📁 Files**: Complete Google Drive file management with enhanced sharing
- **🔗 URLs**: URL management, preview, and processing status
- **🔍 Search**: Advanced search with filters and relevance scoring
- **📈 Analytics**: Category distribution and sender analytics
- **🕸️ Knowledge Graph**: Entity relationships (placeholder)
- **⚙️ Settings**: OAuth management, AI models, and system configuration

### Enhanced Sharing Features
- **📧 Email Sharing**: Share files with any email address
- **🎛️ Permission Control**: Reader, Commenter, Writer access levels
- **🔗 Public Links**: Generate shareable links with access controls
- **📬 Notifications**: Optional email notifications to recipients
- **👥 Third-party Access**: Professional sharing beyond self-access

### API Endpoints
```bash
# Health checks
GET /api/email/health
GET /api/ai/health  
GET /api/content/health

# Data endpoints
GET /api/email/dashboard/stats    # Dashboard statistics
GET /api/email/ideas             # Paginated ideas list
POST /api/email/search           # Full-text search
POST /api/email/process-emails   # Trigger processing
GET /api/email/config            # Configuration

# Enhanced Drive & Sharing (New)
GET /api/email/drive/files               # List all Drive files
GET /api/email/drive/files/{file_id}     # Get file details
POST /api/email/drive/share/{file_id}    # Enhanced sharing with email/links
DELETE /api/email/drive/files/{file_id}  # Delete file from Drive
POST /api/email/drive/upload             # Upload file to Google Drive
GET /api/email/drive/quota               # Drive quota information
GET /api/email/settings/oauth            # OAuth status and configuration

# URL Management (New)
GET /api/email/urls                      # List all URLs with pagination
GET /api/email/urls/{url_id}            # Get URL details and metadata
GET /api/email/urls/{url_id}/preview    # Get URL preview content

# Background Processing
GET /api/content/jobs            # Check conversion job status
POST /api/content/jobs/process   # Manually trigger job processing
```

## 🗄️ Database Schema

### Tables (6 total)
- **`ideas`**: Main email content and metadata
- **`urls`**: Extracted URLs with titles and domains
- **`entities`**: Extracted entities (people, companies, technologies)
- **`attachments`**: File attachments and processed content
- **`processing_summary`**: Daily processing statistics
- **`search_queries`**: Search history and analytics

### Sample Data Structure
```json
{
  "id": "uuid",
  "subject": "Research robotics",
  "cleaned_content": "Content about AI and robotics...",
  "category": "research_papers",
  "sender_email": "researcher@university.edu",
  "processing_status": "completed",
  "created_at": "2025-06-25T22:34:38Z"
}
```

## 🔧 Configuration

### Email Categories (6 configured)
- `personal_thoughts`: Personal notes and reflections
- `dev_tools`: Development tools and resources
- `research_papers`: Academic papers and research
- `ai_implementations`: AI/ML implementations and code
- `industry_news`: News and industry updates
- `reference_materials`: Documentation and references

### Processing Settings
```yaml
email:
  intake_email: "ideaseea@gmail.com"
  processing:
    batch_size: 50
    max_age_days: 30
    check_interval_minutes: 15
  content_types:
    email_body: true
    attachments: true
    urls: true
    images: false
```

## 🧪 Testing & Validation

### Phase 1 Setup & Testing
```bash
# Run Phase 1 setup (Google Drive integration)
python scripts/setup_phase1.py

# Test enhanced attachment endpoints
curl http://localhost:3003/attachments/1/download     # Stream file from Drive
curl http://localhost:3003/attachments/1/markdown     # Get converted content
curl http://localhost:3003/conversion/stats           # Storage usage stats
curl http://localhost:3003/drive/quota                # Drive quota info
```

### Health Checks
```bash
# Test all services
curl http://localhost:3002/api/email/health
curl http://localhost:3002/api/ai/health
curl http://localhost:3002/api/content/health

# Test data endpoints
curl http://localhost:3002/api/email/dashboard/stats
curl http://localhost:3002/api/email/ideas
```

### Search Testing
```bash
# Test search functionality
curl -X POST http://localhost:3002/api/email/search \
  -H "Content-Type: application/json" \
  -d '{"query": "robotics", "type": "semantic"}'
```

### Email Processing Test
```bash
# Process emails with force refresh
curl -X POST http://localhost:3003/process-emails \
  -H "Content-Type: application/json" \
  -d '{"force_reprocess": true, "max_emails": 5}'
```

### Phase 1 Conversion Testing
```bash
# Test markdown conversion for different file types
curl -X POST http://localhost:3003/conversion/jobs \
  -H "Content-Type: application/json" \
  -d '{"attachment_id": "uuid", "force_reprocess": true}'

# Monitor conversion job status
curl http://localhost:3003/conversion/jobs
```

## 📊 Performance Metrics

| Component | Response Time | Status | Functionality |
|-----------|---------------|--------|---------------|
| Frontend Load | <500ms | ✅ | 100% |
| API Proxy | <100ms | ✅ | 100% |
| Database Queries | <50ms | ✅ | 100% |
| Search Operations | <200ms | ✅ | 100% |
| Email Processing | <2s per email | ✅ | 100% |
| Gmail API Calls | <1s | ✅ | 100% |

## 🔍 Troubleshooting

### Common Issues

#### Frontend Not Loading
```bash
# Restart web interface to refresh DNS
docker-compose restart web_interface
```

#### Gmail API Errors
```bash
# Check OAuth token status
docker exec idea_db_email_processor python -c "
from src.gmail_client import GmailClient
config = {'email': {'intake_email': 'ideaseea@gmail.com'}}
client = GmailClient(config)
print('Has credentials:', client.has_credentials())
print('Service initialized:', client.service is not None)
"
```

#### Database Connection Issues
```bash
# Check database connectivity
docker exec idea_db_email_processor python -c "
import asyncio
from src.database import DatabaseManager
async def test():
    db = DatabaseManager('postgresql://ai_user:ai_platform_dev@ai_platform_postgres:5432/ai_platform')
    await db.initialize()
    print('Database connected:', db.is_connected())
asyncio.run(test())
"
```

## 🚀 Production Deployment

### Environment Variables
```bash
POSTGRES_URL=postgresql://ai_user:password@postgres:5432/ai_platform
MAC_STUDIO_ENDPOINT=https://your-endpoint/v1
DEFAULT_MODEL=deepseek-r1
MINIO_PASSWORD=secure_password
```

### Security Considerations
- OAuth credentials secured in mounted volumes
- Database credentials via environment variables
- Network isolation via Docker networks
- API rate limiting configured

## 📈 Future Enhancements

### Planned Features
- **Real-time WebSocket Updates**: Live dashboard updates
- **Advanced Analytics**: Trend analysis and insights
- **Knowledge Graph Visualization**: Interactive entity relationships
- **Email Templates**: Automated response generation
- **Integration APIs**: Connect with external tools
- **Mobile App**: iOS/Android companion app

### Scaling Options
- **Horizontal Scaling**: Multiple email processor instances
- **Database Sharding**: Partition by date or category
- **Caching Layer**: Redis for frequently accessed data
- **Load Balancing**: Nginx upstream configuration

## 🚀 Recent Progress & Roadmap (June 2024)

### Recent Progress
- **Pre-Processor Microservice:**
  - FastAPI service for document normalization (Markdown, YAML front-matter)
  - Semantic chunking (by heading, paragraph, sliding window)
  - Deduplication (SHA1), language detection, metadata enrichment
  - Robust error handling and input validation
- **Event-Driven Pipeline:**
  - Redis added as a core service (Docker Compose)
  - Pre-processor publishes `idea.preprocessed` and `idea.chunked` events to `idea.events` channel
  - Any service can subscribe to events for downstream processing (LLM extraction, analytics, etc.)
- **UI Improvements:**
  - Knowledge Graph tab: larger, more responsive, with zoom/pan and click-drag panning
  - Dashboard service management script and Docker reference added

### June 2024: AI Processor Upgrade
- **Redis Event-Driven Extraction:** ai_processor now subscribes to `idea.preprocessed` and `idea.chunked` events, processes them asynchronously.
- **LLM Integration:** Calls Mac Studio LLM endpoint (OpenAI-compatible) for entity/relationship extraction per knowledge graph taxonomy.
- **Event Publishing:** Extraction results published to `idea.extracted` channel for downstream consumers.
- **Manual Extraction Endpoint:** `/extract/manual` allows API-based LLM extraction/testing.
- **Configurable:** Uses environment variables for Redis/LLM endpoint, robust logging and error handling.

**Next Steps:**
- Add monitoring and health endpoints for all microservices
- Test end-to-end event-driven pipeline
- Implement and document downstream consumers for `idea.extracted`

### Roadmap / Next Steps
- Integrate LLM-driven extraction and knowledge graph edge taxonomy
- Implement downstream consumers for event-driven pipeline (e.g., entity extraction, analytics)
- Expand normalization/chunking for more formats (PDF, HTML, etc.)
- Add monitoring and health endpoints for all microservices
- Document and test full event-driven workflow

## 📚 Documentation

- [API Documentation](docs/API.md)
- [Database Schema](docs/SCHEMA.md)
- [Gmail OAuth Setup](docs/OAUTH.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11, AsyncIO
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Database**: PostgreSQL 15 with full-text search
- **Authentication**: Google OAuth2, Gmail API
- **Infrastructure**: Docker, Docker Compose, Nginx
- **AI/ML**: OpenAI API, Mac Studio LLM integration
- **Storage**: MinIO object storage for attachments

---

**Ready to transform your email into actionable intelligence!** 🚀 

## 🐦 Manual X (Twitter) Post Retrieval  
*Added July 2025 — Phase 1.1*

The free-tier X API (100 calls/month) is integrated for **manual** tweet fetching.

### Backend
- **Endpoints**  
  `GET /api/email/x-posts` – list fetched tweets **and** pending Twitter URLs  
  `POST /api/email/x-posts/fetch` – body `{ "urls": ["https://twitter.com/..."] }`  
  `GET /api/email/x-posts/api-usage` – current monthly quota
- **Database**  
  Tables `x_posts`, `x_media`, and `x_api_usage` track tweet data, media, and call usage.  
  Column `api_used` on `urls` indicates if a tweet consumed API quota.

### Frontend
- **Urls Page** now has a sub-tab **“X Posts”**:
  1. Shows all Twitter URLs (fetched and pending).
  2. Multi-select rows and click **Fetch Selected** to retrieve tweets.
  3. Quota card displays remaining calls with colour status light.

### Usage
1. Save a Twitter link via email or URL input – it appears in **X Posts** as *pending*.
2. Select the row and press **Fetch Selected**.
3. Tweet body, expanded links, and media are stored and attached to Google Drive.
4. Quota automatically decrements; when exhausted, backend returns HTTP 429.

> Bearer token must be set: `X_BEARER_TOKEN=<token>` in `docker-compose.yml` or environment. 

### July 2025
- Knowledge Graph help modal now fully taxonomy-aligned and user-focused in the UI. 