# Idea Database - Complete Technical Reference

**Project Type:** AI-Powered Email Intelligence Platform  
**Status:** ✅ **FULLY OPERATIONAL** - Database-driven taxonomy with LLM-based categorization  
**Architecture:** Microservices with Docker Compose  
**Last Updated:** July 2025

## 🚀 Recent Major Updates (January 2025)
- ✅ **Advanced Search & Filter System**: Multi-field search with entity type, sender, and date filtering
- ✅ **Complete Email Management Platform**: Full editing capabilities with knowledge graph management
- ✅ **Enhanced Dashboard Metrics**: Fixed processing time cards and activity charts
- ✅ **Database-Driven Taxonomy**: Replaced static YAML with dynamic database taxonomy
- ✅ **LLM-Based Categorization**: Replaced keyword matching with Mac Studio LLM categorization  
- ✅ **Modern Knowledge Graph**: Complete email→entity traceability with production implementation
- ✅ **Real-Time Taxonomy Editing**: Web interface for dynamic taxonomy management
- ✅ **Unified Service Architecture**: All services use database as single source of truth  

## 🎯 Project Overview

The Idea Database is a comprehensive email intelligence platform that automatically processes emails sent to a designated intake address, extracts insights, categorizes content, converts attachments to markdown, and provides a searchable knowledge base with AI analysis capabilities.

### Core Value Proposition
- **Automated Email Processing**: Turn emails into structured, searchable knowledge
- **Advanced Search & Filtering**: Multi-field search with entity type, sender, and date filtering
- **Complete Email Management**: Full editing capabilities with knowledge graph management
- **Attachment Intelligence**: Convert PDFs, Word docs, images to LLM-ready markdown
- **Google Drive Integration**: Persistent file storage independent of Gmail limits
- **AI Analysis**: Local Mac Studio LLM for intelligent entity extraction and categorization
- **Real-time Dashboard**: React frontend with live data updates and enhanced metrics

## 🏗️ Architecture Overview

### System Architecture Pattern
```
Frontend (React) → Nginx Proxy → Backend Services → PostgreSQL + Google Drive
                                      ↓
                              Mac Studio LLM (Phase 3)
```

### Technology Stack
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Backend**: FastAPI, Python 3.11, AsyncIO
- **Database**: PostgreSQL 15 with full-text search
- **Storage**: Google Drive API + PostgreSQL hybrid
- **Authentication**: Google OAuth2, Gmail API
- **Infrastructure**: Docker Compose, Nginx proxy
- **AI/ML**: Mac Studio LLM endpoint (OpenAI API compatible)

## 🐳 Docker Infrastructure

### Container Architecture
```yaml
services:
  web_interface:     # React frontend (port 3002)
  email_processor:   # Gmail integration + file processing (port 3003)
  ai_processor:      # Entity extraction + categorization (port 3004)
  content_extractor: # URL and attachment processing (port 3005)
  ai_platform_postgres: # Database (port 5432)
```

### Service Details

#### **Web Interface Container**
- **Image**: Multi-stage build (node:18-alpine → nginx:alpine)
- **Purpose**: Serves React app + API proxy
- **Port**: 3002 (external) → 3002 (internal)
- **Build Dependencies** (Node.js 18+):
  ```json
  # Production Dependencies (15 packages)
  react^18.2.0, react-dom^18.2.0, react-router-dom^6.20.1
  react-query^3.39.3, axios^1.6.2, date-fns^2.30.0
  lucide-react^0.294.0, recharts^2.8.0, react-flow-renderer^10.3.17
  react-select^5.8.0, react-virtualized-auto-sizer^1.0.20
  react-window^1.8.8, react-markdown^9.0.1, remark-gfm^4.0.0
  react-syntax-highlighter^15.5.0, clsx^2.0.0, tailwind-merge^2.1.0
  
  # Development Dependencies (14 packages)
  TypeScript, ESLint, Tailwind CSS, Vite, Autoprefixer
  @types/react, @vitejs/plugin-react, postcss
  ```
- **Runtime**: nginx:alpine with custom configuration
- **Proxy Configuration**:
  ```nginx
  /api/email/* → email_processor:8000
  /api/ai/* → ai_processor:8000
  /api/content/* → content_extractor:8000
  ```
- **Health Check**: HTTP GET /health
- **Dependencies**: All backend services

#### **Email Processor Container**
- **Image**: python:3.11-slim
- **Purpose**: Gmail API integration, attachment processing, Google Drive storage
- **Port**: 3003 (external) → 8000 (internal)
- **System Dependencies**: curl
- **Python Dependencies** (53 packages):
  ```
  # Gmail & Google Drive API
  google-api-python-client==2.111.0, google-auth==2.24.0
  google-auth-httplib2==0.2.0, google-auth-oauthlib==1.2.0
  google-api-core==2.14.0
  
  # Database & ORM
  psycopg2-binary==2.9.9, sqlalchemy==2.0.23, asyncpg==0.29.0
  
  # Web Framework
  fastapi==0.104.1, uvicorn==0.24.0, httpx==0.25.2, requests==2.31.0
  
  # Phase 1 Conversion Pipeline
  PyMuPDF==1.23.26, python-docx==1.1.0, python-pptx==0.6.23
  markdownify==0.11.6, beautifulsoup4==4.12.2, lxml==4.9.3
  Pillow==10.1.0, pytesseract==0.3.10, opencv-python==4.8.1.78
  python-magic==0.4.27, chardet==5.2.0, pypdf==3.17.1
  
  # Data Processing
  pydantic==2.5.0, pydantic-settings==2.1.0, PyYAML==6.0.1
  python-multipart==0.0.6, email-validator==2.1.0
  python-dateutil==2.8.2, structlog==23.2.0
  ```
- **Volumes**: 
  - `./gmail_credentials:/app/credentials` (OAuth tokens)
  - `./config:/app/config` (service account keys)
- **Environment**: 
  ```
  POSTGRES_URL, MAC_STUDIO_ENDPOINT, DEFAULT_MODEL,
  CHROMA_URL, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
  ```

#### **AI Processor Container**
- **Image**: python:3.11-slim
- **Purpose**: Entity extraction, content categorization, AI analysis
- **Port**: 3004 (external) → 8000 (internal)
- **System Dependencies**: curl
- **Python Dependencies** (19 packages):
  ```
  # Web Framework & API
  fastapi==0.104.1, uvicorn[standard]==0.24.0, httpx==0.25.2
  
  # AI & ML Libraries
  openai==1.3.7, anthropic==0.7.8, chromadb==0.4.18
  
  # Database & ORM
  asyncpg==0.29.0, sqlalchemy==2.0.23, alembic==1.13.0
  
  # Authentication & Security
  PyJWT==2.8.0, passlib[bcrypt]==1.7.4, python-jose[cryptography]==3.3.0
  
  # Task Queue & Monitoring
  redis==5.0.1, celery==5.3.4, prometheus-client==0.19.0
  
  # Utilities
  pydantic==2.5.0, structlog==23.2.0, python-multipart==0.0.6, python-dotenv==1.0.0
  ```
- **Status**: Basic health endpoint implemented, processing endpoints pending
- **Future Integration**: Mac Studio LLM endpoint

#### **Content Extractor Container**
- **Image**: python:3.11-slim
- **Purpose**: URL content extraction, web scraping, HTML processing
- **Port**: 3005 (external) → 8000 (internal)
- **System Dependencies**: curl, wget, poppler-utils, tesseract-ocr, libreoffice, pandoc
- **Python Dependencies** (23 packages):
  ```
  # Web Framework & HTTP
  fastapi==0.104.1, uvicorn[standard]==0.24.0, httpx==0.25.2
  requests==2.31.0, aiofiles==23.2.1
  
  # Content Processing
  beautifulsoup4==4.12.2, markdownify==0.11.6, python-magic==0.4.27
  PyPDF2==3.0.1, python-docx==1.1.0, openpyxl==3.1.2
  pillow==10.1.0, pytesseract==0.3.10
  
  # Database & Storage
  asyncpg==0.29.0, sqlalchemy==2.0.23, minio==7.2.0
  
  # Task Queue & Monitoring
  redis==5.0.1, celery==5.3.4, prometheus-client==0.19.0
  
  # Utilities
  pydantic==2.5.0, structlog==23.2.0, python-multipart==0.0.6, python-dotenv==1.0.0
  ```
- **Status**: Basic health endpoint implemented, extraction endpoints pending
- **Future Features**: Browser automation, bulk URL processing

#### **PostgreSQL Container**
- **Image**: postgres:15-alpine
- **Purpose**: Primary data storage with full-text search
- **Port**: 5432 (internal only)
- **Database**: `ai_platform`
- **User**: `ai_user` / `ai_platform_secure_password`
- **Persistence**: Docker volume for data retention

## 📊 Database Schema

### Core Tables

#### **ideas** (Main email content)
```sql
id UUID PRIMARY KEY
subject TEXT
cleaned_content TEXT
category VARCHAR(50)  -- 6 predefined categories
sender_email VARCHAR(255)
sender_name VARCHAR(255)
received_date TIMESTAMP WITH TIME ZONE
processing_status VARCHAR(20) DEFAULT 'pending'
confidence_score DECIMAL(3,2)
created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
```

#### **attachments** (Enhanced Phase 1)
```sql
id UUID PRIMARY KEY
idea_id UUID REFERENCES ideas(id)
filename VARCHAR(255)
original_filename VARCHAR(255)
file_type VARCHAR(100)
file_size BIGINT
content_hash VARCHAR(64)
-- Phase 1 Enhancements:
drive_file_id VARCHAR(255)      -- Google Drive file ID
drive_file_url TEXT             -- Direct Drive link
markdown_content TEXT           -- Converted content
conversion_status VARCHAR(20) DEFAULT 'pending'
conversion_error TEXT
storage_type VARCHAR(20) DEFAULT 'local'
created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
```

#### **urls** (Enhanced Phase 1)
```sql
id UUID PRIMARY KEY
idea_id UUID REFERENCES ideas(id)
url TEXT
title VARCHAR(500)
domain VARCHAR(255)
fetch_status VARCHAR(20) DEFAULT 'pending'
content_type VARCHAR(100)
-- Phase 1 Enhancements:
markdown_content TEXT           -- Processed webpage content
processing_status VARCHAR(20) DEFAULT 'pending'
processing_error TEXT
content_length INTEGER
processed_date TIMESTAMP WITH TIME ZONE
```

#### **entities** (AI extracted)
```sql
id UUID PRIMARY KEY
idea_id UUID REFERENCES ideas(id)
entity_type VARCHAR(50)  -- person, company, technology, etc.
entity_value TEXT
confidence DECIMAL(3,2)
context TEXT
```

#### **conversion_jobs** (Phase 1 Queue Management)
```sql
id UUID PRIMARY KEY
attachment_id UUID REFERENCES attachments(id)
url_id UUID REFERENCES urls(id)
job_type VARCHAR(20) NOT NULL
status VARCHAR(20) DEFAULT 'pending'
priority INTEGER DEFAULT 5
retry_count INTEGER DEFAULT 0
error_message TEXT
started_at TIMESTAMP WITH TIME ZONE
completed_at TIMESTAMP WITH TIME ZONE
created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
```

#### **drive_config** (Phase 1 Google Drive)
```sql
id UUID PRIMARY KEY
service_account_email VARCHAR(255)
drive_folder_id VARCHAR(255)
folder_name VARCHAR(255)
quota_bytes BIGINT DEFAULT 15000000000
used_bytes BIGINT DEFAULT 0
is_active BOOLEAN DEFAULT TRUE
```

### Performance Indexes
```sql
-- Full-text search
CREATE INDEX idx_ideas_content_search ON ideas USING gin(to_tsvector('english', cleaned_content));
CREATE INDEX idx_attachments_markdown_search ON attachments USING gin(to_tsvector('english', markdown_content));

-- Category and status filtering
CREATE INDEX idx_ideas_category ON ideas(category);
CREATE INDEX idx_ideas_status ON ideas(processing_status);
CREATE INDEX idx_attachments_conversion_status ON attachments(conversion_status);

-- Date-based queries
CREATE INDEX idx_ideas_received_date ON ideas(received_date);
CREATE INDEX idx_conversion_jobs_created_at ON conversion_jobs(created_at);
```

## 📧 Gmail Integration

### OAuth Configuration
- **Client ID**: `1068903107047-qlvd3kcfuc8hladp83lh51ora8lmj30a.apps.googleusercontent.com`
- **Project**: `ideas-dashboard-463714`
- **Scopes**: `gmail.readonly`, `gmail.modify`
- **Intake Email**: `ideaseea@gmail.com`

### Credential Management
```
gmail_credentials/
├── gmail_credentials.json  # OAuth client credentials
└── gmail_token.json       # Access/refresh tokens (auto-refreshed)
```

### Email Processing Workflow
1. **Intake**: Emails sent to `ideaseea@gmail.com`
2. **API Fetch**: Gmail API retrieves new/unread emails
3. **Content Extraction**: Subject, body, sender, attachments, URLs
4. **Attachment Processing**: Download → Google Drive → Markdown conversion
5. **AI Categorization**: Assign to one of 6 categories
6. **Entity Extraction**: People, companies, technologies
7. **Database Storage**: Structured data with full-text search
8. **Status Update**: Mark as processed in Gmail

### Email Categories (AI Classification)
```yaml
categories:
  personal_thoughts: "Personal notes and reflections"
  dev_tools: "Development tools and resources"
  research_papers: "Academic papers and research"
  ai_implementations: "AI/ML implementations and code"
  industry_news: "News and industry updates"
  reference_materials: "Documentation and references"
```

## 🗂️ Google Drive Integration (Phase 1)

### Service Account Setup
- **Authentication**: Service account with JSON key file
- **Folder Structure**: Automatic folder creation for organization
- **Deduplication**: SHA-256 hashing prevents duplicate storage
- **Quota Management**: 15GB default with usage tracking

### File Processing Pipeline
```
Gmail Attachment → Binary Download → Google Drive Upload → Metadata Storage → Conversion Queue
                                                                                      ↓
                                                            Markdown Conversion ← File Retrieval
```

### Supported File Types
```yaml
documents:
  pdf: "PyMuPDF text extraction + table detection"
  docx: "python-docx paragraph + table conversion"
  pptx: "python-pptx slide-by-slide processing"
  
images:
  jpg/png: "Tesseract OCR with confidence scoring"
  preprocessing: "OpenCV image enhancement"
  
web:
  html: "BeautifulSoup clean markdown conversion"
  
text:
  txt: "Encoding detection + formatting"
```

### Conversion Quality Metrics
- **PDF**: Text extraction accuracy, table preservation
- **Images**: OCR confidence scores, text detection
- **Office Docs**: Style preservation, formatting retention
- **HTML**: Clean markdown output, link preservation

## 🎛️ Dashboard Frontend

### React Architecture
```
src/
├── components/          # Reusable UI components
│   ├── Dashboard.tsx   # Main overview
│   ├── EmailList.tsx   # Paginated email display
│   ├── SearchBar.tsx   # Advanced search interface
│   └── AttachmentViewer.tsx  # Phase 1 enhanced viewer
├── pages/              # Route components
│   ├── DashboardPage.tsx
│   ├── EmailsPage.tsx
│   ├── SearchPage.tsx
│   ├── AnalyticsPage.tsx
│   └── SettingsPage.tsx
├── services/           # API integration
│   └── api.ts         # Centralized API calls
└── types/             # TypeScript definitions
    └── index.ts
```

### Dashboard Features

#### **📊 Overview Dashboard**
- **Statistics Cards**: Total emails, categories, processing status
- **Recent Activity**: Latest processed emails with metadata
- **Category Distribution**: Visual breakdown of email types
- **Processing Health**: Service status and performance metrics

#### **📧 Email Management**
- **Paginated List**: 20 emails per page with infinite scroll
- **Advanced Filtering**: Category, date range, sender, status
- **Full-Text Search**: Content and attachment search
- **Bulk Operations**: Category reassignment, deletion

#### **🔍 Search Interface**
- **Semantic Search**: Content similarity matching
- **Exact Match**: Keyword and phrase search
- **Metadata Filtering**: File types, dates, categories
- **Relevance Scoring**: Search result ranking

#### **📈 Analytics Dashboard**
- **Category Trends**: Email volume by category over time
- **Sender Analytics**: Top senders and frequency
- **Attachment Statistics**: File types and conversion status
- **Processing Metrics**: Success rates and error tracking

#### **⚙️ Settings Management**
- **Email Configuration**: Intake address and processing rules
- **Category Management**: Custom categories and rules
- **Integration Status**: Gmail and Drive connection health
- **Performance Tuning**: Batch sizes and intervals

### API Integration Layer
```typescript
// Centralized API service
class ApiService {
  // Dashboard data
  getDashboardStats(): Promise<DashboardStats>
  getRecentActivity(limit: number): Promise<Activity[]>
  
  // Email operations
  getEmails(page: number, filters: EmailFilters): Promise<EmailPage>
  searchEmails(query: SearchQuery): Promise<SearchResults>
  updateEmail(id: string, updates: EmailUpdates): Promise<void>
  
  // Phase 1 enhanced endpoints
  downloadAttachment(id: string): Promise<Blob>
  getAttachmentMarkdown(id: string): Promise<MarkdownContent>
  getConversionStats(): Promise<ConversionStats>
  
  // Processing controls
  triggerEmailProcessing(options: ProcessingOptions): Promise<void>
  getProcessingStatus(): Promise<ProcessingStatus>
}
```

## 🔄 Data Flow Architecture

### Email Processing Flow
```
1. Email Reception (ideaseea@gmail.com)
   ↓
2. Gmail API Fetch (email_processor)
   ↓
3. Content Extraction (subject, body, attachments, URLs)
   ↓
4. Attachment Processing Pipeline:
   Gmail Download → Google Drive Upload → Conversion Queue → Markdown Generation
   ↓
5. AI Analysis (ai_processor):
   Category Classification → Entity Extraction → Confidence Scoring
   ↓
6. Database Storage (PostgreSQL):
   Structured Data → Full-text Indexing → Relationship Mapping
   ↓
7. Frontend Update (WebSocket/Polling):
   Real-time Dashboard → Search Index Update → Analytics Refresh
```

### Phase 1 Enhanced Attachment Flow
```
Email Attachment Detection
   ↓
Binary Content Download (Gmail API)
   ↓
SHA-256 Hash Generation (Deduplication)
   ↓
Google Drive Upload (Service Account)
   ↓
Metadata Storage (PostgreSQL)
   ↓
Conversion Job Creation (Queue)
   ↓
File Type Detection (python-magic)
   ↓
Format-Specific Processing:
   ├── PDF → PyMuPDF → Text + Tables
   ├── Word → python-docx → Structured Content
   ├── PowerPoint → python-pptx → Slide Content
   ├── Images → OpenCV + Tesseract → OCR Text
   └── HTML → BeautifulSoup → Clean Markdown
   ↓
Markdown Content Storage (PostgreSQL)
   ↓
Full-text Search Index Update
   ↓
Frontend Notification (Conversion Complete)
```

## 🔌 API Endpoints Reference

### Core Email Processing
```http
GET    /health                          # Service health check
GET    /config                          # Configuration details
POST   /process-emails                  # Trigger email processing
GET    /stats                           # Processing statistics
```

### Dashboard Data
```http
GET    /dashboard/stats                 # Overview statistics
GET    /ideas?page=1&per_page=20        # Paginated email list
POST   /search                          # Full-text search
GET    /dashboard/activity              # Recent activity feed
```

### Phase 1 Enhanced Endpoints
```http
# Attachment Management
GET    /attachments/{id}/download       # Stream file from Google Drive
GET    /attachments/{id}/markdown       # Get converted markdown content

# Conversion System
GET    /conversion/stats                # Storage usage and metrics
GET    /conversion/jobs                 # Pending conversion queue
POST   /conversion/jobs/{id}/retry      # Retry failed conversion

# Google Drive Integration
GET    /drive/quota                     # Storage quota information

# URL Processing (Phase 2 Ready)
POST   /urls/{id}/process               # Trigger URL content extraction

# OAuth Token Management
GET    /oauth/status                    # OAuth status for all services
POST   /oauth/refresh/gmail             # Refresh Gmail OAuth tokens
POST   /oauth/refresh/drive             # Refresh Google Drive OAuth tokens
```

### Response Formats
```json
// Dashboard Stats
{
  "total_ideas": 150,
  "by_category": {
    "research_papers": 45,
    "dev_tools": 32,
    "personal_thoughts": 28
  },
  "processing_health": {
    "emails_processed_today": 12,
    "avg_processing_time": "2.3s",
    "success_rate": 98.5
  }
}

// Enhanced Attachment (Phase 1)
{
  "id": "uuid",
  "filename": "document.pdf",
  "storage_type": "google_drive",
  "drive_file_id": "1ABC123...",
  "conversion_status": "completed",
  "markdown_available": true,
  "file_size": 1048576,
  "created_at": "2025-01-15T10:30:00Z"
}

// Conversion Stats (Phase 1)
{
  "storage_stats": {
    "total_drive_files": 45,
    "total_drive_size": 234567890,
    "conversion_stats": {
      "completed": 42,
      "pending": 3,
      "failed": 0
    }
  },
  "drive_integration": {
    "enabled": true,
    "folder_configured": true,
    "quota_used_percentage": 15.7
  }
}

// OAuth Status Response
{
  "gmail": {
    "enabled": true,
    "configured": true,
    "valid": true,
    "expired": false,
    "method": "oauth",
    "requires_refresh": false
  },
  "drive": {
    "enabled": true,
    "configured": true,
    "valid": true,
    "expired": false,
    "method": "oauth",
    "requires_refresh": false
  }
}

// OAuth Refresh Response
{
  "success": true,
  "message": "Gmail OAuth tokens refreshed successfully",
  "status": {
    "valid": true,
    "expired": false,
    "service_reinitialized": true
  }
}
```

## 🖥️ Mac Studio Infrastructure

### Hardware Specifications
- **System**: Mac Studio M3 Ultra (Apple Silicon)
- **Memory**: 128GB+ unified memory
- **Architecture**: ARM64 with dedicated ML accelerators
- **Network**: Tailscale mesh networking + public funnel
- **Power Management**: 24/7 availability (system sleep disabled)

### Software Stack
- **LLM Server**: Ollama (latest)
- **Process Management**: macOS launchd service
- **Network Proxy**: Tailscale Serve (HTTPS proxy)
- **API Compatibility**: OpenAI API standard
- **Health Monitoring**: Automated watchdog scripts

### Access Methods
```bash
# Primary Tailnet URL (requires Tailscale)
https://matiass-mac-studio.tail174e9b.ts.net/v1

# SSH Access
ssh mmirvois@matiass-mac-studio.tail174e9b.ts.net

# Screen Sharing
open vnc://mmirvois@matiass-mac-studio.tail174e9b.ts.net

# Health Check
curl -s https://matiass-mac-studio.tail174e9b.ts.net/v1/models
```

### Available Models (6 total)

| Model | Identifier | Specialization | Size | Use Case |
|-------|------------|----------------|------|----------|
| **DeepSeek R1** | `deepseek-r1` | Primary reasoning | 70B+ | Complex analysis, problem-solving |
| **Qwen 3** | `qwen3:32b` | Multilingual | 32B | General purpose, Chinese/English |
| **Qwen 2.5** | `qwen25` | Fast inference | 7B-14B | Quick responses, general tasks |
| **Qwen 2.5 Vision** | `qwen2.5vl` | Vision-language | 7B+ | Image analysis, multimodal |
| **Llama 4 Scout** | `llama4:scout` | Domain expertise | 70B+ | Technical analysis, research |
| **Llama 4 Maverick** | `llama4:maverick` | Creative research | 70B+ | Exploration, creative writing |

### Model Selection Strategy
- **Primary**: `deepseek-r1` for reasoning and analysis
- **Secondary**: `llama4:scout` for domain expertise
- **Creative**: `llama4:maverick` for exploration
- **Vision**: `qwen2.5vl` for image processing
- **Fast**: `qwen25` for quick responses
- **Multilingual**: `qwen3:32b` for international content

### Performance Characteristics
- **Concurrent Requests**: Multiple simultaneous connections
- **Model Switching**: Hot-swappable without server restart
- **Response Time**: 30-60 seconds for complex reasoning
- **Uptime**: 99.9% (optimized power management)
- **Throughput**: ~10-20 requests/minute depending on complexity

### Integration Examples
```python
# Python OpenAI SDK
from openai import OpenAI
client = OpenAI(
    base_url="https://matiass-mac-studio.tail174e9b.ts.net/v1",
    api_key="ollama"
)

# Chat completion
response = client.chat.completions.create(
    model="deepseek-r1",
    messages=[{"role": "user", "content": "Analyze this email content..."}]
)

# Available models
models = client.models.list()
```

```bash
# cURL example
curl -s \
  -H "Content-Type: application/json" \
  -d '{"model":"llama4:scout","messages":[{"role":"user","content":"Extract entities from this text..."}]}' \
  https://matiass-mac-studio.tail174e9b.ts.net/v1/chat/completions
```

## 🧠 AI Integration (Mac Studio LLM)

### Current Implementation Status
- **Phase 1**: ✅ Database schema and API endpoints ready
- **Phase 2**: 🚧 URL processing system (next)
- **Phase 3**: 📋 Mac Studio LLM integration (planned)

### Mac Studio LLM Configuration
```yaml
# Primary Endpoint Configuration
endpoint: "https://matiass-mac-studio.tail174e9b.ts.net/v1"
api_key: "ollama"  # placeholder - Ollama ignores authentication
api_compatibility: "OpenAI API"
server_technology: "Ollama on Mac Studio M3 Ultra"

# Available Models (6 models)
available_models:
  deepseek_r1: "deepseek-r1"           # Primary reasoning model
  qwen3_32b: "qwen3:32b"               # 32B parameter Chinese/English model
  qwen25: "qwen25"                     # Qwen 2.5 general purpose
  qwen25_vision: "qwen2.5vl"           # Vision-language model
  llama4_scout: "llama4:scout"         # Domain expertise & analysis
  llama4_maverick: "llama4:maverick"   # Creative research generation

# Infrastructure Details
hardware:
  system: "Mac Studio M3 Ultra"
  architecture: "Apple Silicon M3 Ultra"
  memory: "128GB+ unified memory"
  networking: "Tailscale mesh + public funnel"
  availability: "24/7 (sleep disabled)"

# Access Methods
access:
  tailnet_url: "https://matiass-mac-studio.tail174e9b.ts.net/v1"
  public_funnel: "Available via Tailscale Funnel"
  ssh_access: "matiass-mac-studio.tail174e9b.ts.net"
  screen_sharing: "vnc://mmirvois@matiass-mac-studio.tail174e9b.ts.net"

# Capabilities by Model
model_specializations:
  deepseek_r1: "Primary reasoning, complex analysis"
  qwen3_32b: "Multilingual, general purpose"
  qwen25: "Fast inference, general tasks"
  qwen2_5vl: "Vision + text processing"
  llama4_scout: "Domain expertise, technical analysis"
  llama4_maverick: "Creative research, exploration"

# Performance Characteristics
performance:
  concurrent_requests: "Multiple simultaneous"
  model_switching: "Hot-swappable without restart"
  response_time: "30-60s for complex reasoning"
  uptime: "99.9% (power management optimized)"
```

### AI Analysis Pipeline (Phase 3)
```
Email Content + Attachments + URLs
   ↓
Context Building (Unified markdown)
   ↓
Mac Studio LLM Processing:
   ├── Summarization
   ├── Entity Extraction
   ├── Category Classification
   ├── Sentiment Analysis
   └── Key Insights Generation
   ↓
Structured Results Storage
   ↓
Interactive Query Interface
```

### Planned AI Features
- **Automated Summarization**: Email and attachment content
- **Smart Categorization**: Context-aware classification
- **Entity Recognition**: People, companies, technologies, dates
- **Question Answering**: Query specific emails or topics
- **Trend Analysis**: Identify patterns across email history
- **Content Recommendations**: Suggest related emails/attachments

## 🔧 Configuration Management

### Environment Variables
```bash
# Database
POSTGRES_URL=postgresql://ai_user:ai_platform_secure_password@ai_platform_postgres:5432/ai_platform

# Gmail Integration
GMAIL_INTAKE_EMAIL=ideaseea@gmail.com
GMAIL_CREDENTIALS_PATH=/app/credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=/app/credentials/gmail_token.json

# Google Drive (Phase 1)
DRIVE_SERVICE_ACCOUNT_PATH=/app/config/drive_service_account.json
DRIVE_FOLDER_NAME=idea-database-attachments
DRIVE_MAX_FILE_SIZE_MB=100

# Mac Studio LLM Integration (Phase 3)
MAC_STUDIO_ENDPOINT=https://matiass-mac-studio.tail174e9b.ts.net/v1
MAC_STUDIO_API_KEY=ollama
DEFAULT_MODEL=deepseek-r1
REASONING_MODEL=llama4:scout

# Available Model Options
# deepseek-r1, qwen3:32b, qwen25, qwen2.5vl, llama4:scout, llama4:maverick
```

### Service Configuration Files
```yaml
# config/email_config.yml
email:
  intake_email: "ideaseea@gmail.com"
  processing:
    batch_size: 50
    max_age_days: 30
    check_interval_minutes: 15

# Phase 1 Google Drive settings
google_drive:
  folder_name: "idea-database-attachments"
  max_file_size_mb: 100
  deduplication: true

# Phase 1 Markdown conversion settings
markdown_conversion:
  ocr_languages: ["eng"]
  image_max_size_mb: 10
  pdf_extract_images: true
  word_preserve_formatting: true
```

## 🚀 Deployment and Operations

### Development Setup
```bash
# Clone and navigate
cd sub-projects/idea-database

# Start all services
docker-compose up -d

# Access points
Frontend: http://localhost:3002
Email API: http://localhost:3003
AI API: http://localhost:3004
Content API: http://localhost:3005
```

### Health Monitoring
```bash
# Service health checks
curl http://localhost:3003/health  # Email processor
curl http://localhost:3004/health  # AI processor
curl http://localhost:3005/health  # Content extractor

# Database connectivity
docker exec idea_db_email_processor python -c "
import asyncpg
conn = asyncpg.connect('postgresql://ai_user:ai_platform_secure_password@ai_platform_postgres:5432/ai_platform')
print('Database OK')
"
```

### Performance Metrics
```yaml
response_times:
  frontend_load: "<500ms"
  api_proxy: "<100ms"
  database_queries: "<50ms"
  search_operations: "<200ms"
  email_processing: "<2s per email"
  gmail_api_calls: "<1s"

throughput:
  emails_per_minute: 30
  attachments_per_minute: 10
  search_queries_per_second: 50
```

## 📋 Implementation Phases

### ✅ Phase 1: Enhanced Attachment Storage (COMPLETED)
**Duration**: 1 week  
**Status**: Production ready

**Completed Features**:
- Google Drive API integration with service account authentication
- Multi-format markdown conversion (PDF, Word, PowerPoint, images with OCR)
- Enhanced database schema with drive_file_id, markdown_content columns
- New conversion_jobs and drive_config tables for queue management
- Enhanced API endpoints for file streaming and conversion status
- Comprehensive error handling and retry mechanisms

**Technical Deliverables**:
- `drive_client.py`: Google Drive operations
- `markdown_converter.py`: Multi-format conversion
- Enhanced `gmail_client.py`: Drive integration
- Database migration: `001_phase1_attachment_storage.sql`
- 8 new API endpoints for attachment and conversion management

### ✅ Completed Implementation (Production Ready)

**All phases completed as of January 2025:**

#### **Phase 2: URL Processing System** ✅ **COMPLETED**
- URL browser interface development ✅
- On-demand URL processing pipeline ✅
- HTML to markdown conversion ✅
- Processing queue management ✅
- Enhanced frontend URL management ✅

#### **Phase 3: Mac Studio LLM Integration** ✅ **COMPLETED**
- OpenAI API-compatible client implementation ✅
- Context building from emails, attachments, and URLs ✅
- AI analysis endpoints (entity extraction, categorization) ✅
- Interactive search and filter system ✅
- Performance optimization with PostgreSQL full-text search ✅

#### **Enhanced Features Beyond Original Plan** ✅ **COMPLETED**
- **Advanced Search System**: Multi-field search across subject, content, and sender
- **Entity Type Filtering**: Filter by concept, organization, technology types
- **Sender Filtering**: Dynamic sender filtering with autocomplete
- **Visual Filter Interface**: Interactive filter tags with reset functionality
- **Dashboard Metrics**: Fixed processing time cards and activity charts
- **Complete Knowledge Graph**: Full email→entity traceability with relationship management

## 🔍 Troubleshooting Guide

### Common Issues

#### **Gmail API Authentication**
```bash
# Check OAuth token status
docker exec idea_db_email_processor python -c "
from src.gmail_client import GmailClient
config = {'email': {'intake_email': 'ideaseea@gmail.com'}}
client = GmailClient(config)
print('Has credentials:', client.has_credentials())
"
```

#### **Database Connection Issues**
```bash
# Test database connectivity
docker exec idea_db_email_processor python -c "
import asyncio, asyncpg
async def test():
    conn = await asyncpg.connect('postgresql://ai_user:ai_platform_secure_password@ai_platform_postgres:5432/ai_platform')
    result = await conn.fetchval('SELECT 1')
    print('Database connected:', result == 1)
asyncio.run(test())
"
```

#### **Google Drive Configuration**
```bash
# Check Drive integration status
curl http://localhost:3003/conversion/stats
curl http://localhost:3003/drive/quota
```

### Service Recovery
```bash
# Restart specific service
docker-compose restart email_processor

# Rebuild after code changes
docker compose --progress plain build email_processor
docker-compose up -d email_processor

# Check service logs
docker logs idea_db_email_processor --tail 20
```

## 📊 Success Metrics

### Functional Metrics
- **Email Processing Success Rate**: >95%
- **Attachment Conversion Success Rate**: >90%
- **Search Response Time**: <200ms
- **Dashboard Load Time**: <500ms
- **Database Query Performance**: <50ms average

### Business Metrics
- **Knowledge Base Growth**: Emails and attachments processed
- **Search Utilization**: Query frequency and success
- **Content Accessibility**: Markdown conversion coverage
- **User Engagement**: Dashboard usage patterns

### Technical Metrics
- **System Uptime**: >99.5%
- **API Response Times**: Within SLA targets
- **Storage Efficiency**: Drive quota utilization
- **Processing Throughput**: Emails per hour

---

## 💡 Key Design Decisions

### **Why Microservices Architecture?**
- **Scalability**: Independent service scaling
- **Maintainability**: Clear separation of concerns
- **Technology Flexibility**: Different languages/frameworks per service
- **Fault Isolation**: Service failures don't cascade

### **Why Google Drive for Storage?**
- **Persistence**: Independent of Gmail storage limits
- **Accessibility**: Direct file access and sharing
- **Cost Effectiveness**: 15GB free, affordable expansion
- **API Maturity**: Robust, well-documented API

### **Why PostgreSQL over NoSQL?**
- **ACID Compliance**: Data consistency requirements
- **Full-text Search**: Built-in search capabilities
- **Relationship Management**: Complex data relationships
- **Performance**: Proven performance at scale

### **Why React Frontend?**
- **Developer Experience**: Excellent tooling and ecosystem
- **Performance**: Virtual DOM and optimization
- **Component Reusability**: Modular UI development
- **TypeScript Integration**: Type safety and developer productivity

---

**This document serves as the complete technical reference for the Idea Database project. It contains all information necessary for LLMs to understand the architecture, make informed decisions, and assist with development tasks.** 