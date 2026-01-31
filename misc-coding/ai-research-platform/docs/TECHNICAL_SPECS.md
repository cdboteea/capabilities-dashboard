# AI Research Platform - Technical Specifications

> Complete technical documentation for self-hosted intelligence platform

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Idea Database](#idea-database)
3. [Twin-Report KB](#twin-report-kb)
4. [Infrastructure](#infrastructure)
5. [API Reference](#api-reference)
6. [Deployment Guide](#deployment-guide)
7. [Development](#development)

## Architecture Overview

### System Components
```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Idea Database     │    │   Twin-Report KB    │    │  Real-Time Intel    │
│   Port: 8080        │    │   Ports: 8100-8102  │    │  Ports: 8200+       │
│                     │    │                     │    │     (Planned)       │
│ • Gmail Processing  │    │ • Topic Management  │    │ • News Crawling     │
│ • Content Extract   │    │ • Report Generation │    │ • Event Routing     │
│ • Categorization    │    │ • Gap Analysis      │    │ • Portfolio Alert   │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     │
            ┌─────────────────────────▼─────────────────────────┐
            │              Core Infrastructure                  │
            │                                                  │
            │ PostgreSQL (5432) • Chroma DB (8000)             │
            │ MinIO (9000/9001) • NATS (4222)                  │
            │ Redis (6379)      • Mac Studio LLM Endpoint      │
            └──────────────────────────────────────────────────┘
```

### Data Flow
1. **Ingestion**: Gmail → Idea Database → PostgreSQL
2. **Research**: Topics → Twin Reports → Quality Analysis
3. **Storage**: Vector embeddings → Chroma, Documents → MinIO
4. **Processing**: Background tasks → Redis/Celery → Mac Studio LLMs

## Idea Database

### Overview
Gmail-powered knowledge ingestion system that automatically processes incoming emails, extracts content, categorizes information, and builds a searchable knowledge base.

### Core Components

#### 1. Email Processor (`services/email_processor/`)
- **Gmail Client**: OAuth2 authentication with graceful fallback
- **Email Parser**: Content extraction, URL detection, attachment handling
- **Database Manager**: Async PostgreSQL operations with connection pooling

#### 2. Database Schema
```sql
-- Core tables in idea_database schema
ideas(id, title, content, category, source_email_id, created_at)
source_emails(id, message_id, subject, sender, received_at, processed)
categories(id, name, description, keyword_list)
entities(id, name, entity_type, confidence_score)
idea_entities(idea_id, entity_id, relationship_type)
urls(id, url, title, content_preview, idea_id, fetched_at)
```

#### 3. API Endpoints
- `GET /health` - Service health check
- `POST /process-emails` - Trigger email processing
- `GET /ideas` - List all ideas with filtering
- `GET /ideas/{id}` - Get specific idea details
- `GET /categories` - List available categories

#### 4. Configuration
```yaml
# config/email_config.yml
email:
  intake_email: "ideaseea@gmail.com"
  processing:
    batch_size: 50
    check_interval_minutes: 15
    auto_categorize: true
```

### Key Features
- **Automatic Categorization**: AI-powered content classification
- **Entity Extraction**: People, organizations, locations identification
- **URL Processing**: Automatic link following and content extraction
- **Placeholder Support**: Development-friendly configuration

## Twin-Report KB

### Overview
Dual AI research system that generates comprehensive reports using multiple models, compares outputs for gaps and contradictions, and builds a knowledge base of high-quality research.

### Core Components

#### 1. Topic Manager Service (`docker/topic_manager/`)
- **FastAPI Backend**: Async request handling with PostgreSQL
- **Background Processing**: Celery workers for report generation
- **Mac Studio Integration**: Direct API calls to local LLM endpoint
- **Quality Control**: Citation verification and fact-checking

#### 2. Database Schema (pgvector enabled)
```sql
-- Core tables in twin_report schema  
twin_topics(id, title, description, metadata, created_at)
twin_articles(id, topic_id, model_name, content, word_count, generated_at)
twin_web_archives(id, url, title, content, embedding, archived_at)
twin_diff(id, article1_id, article2_id, diff_summary, gaps, overlaps)
twin_quality_checks(id, article_id, check_type, status, details)
```

#### 3. Microservices Architecture
- **Topic Manager** (8101): API gateway and orchestration
- **Quality Controller** (8102): Fact-checking and citation verification
- **Diff Worker** (8103): AI-powered report comparison and gap analysis
- **Document Parser** (8000): Google Docs, PDFs, chat exports, web content
- **Frontend Interface** (3000): Modern web UI with dashboard and document upload

#### 4. Mac Studio Model Integration
```python
# Local models available via endpoint
AVAILABLE_MODELS = {
    "deepseek-r1": "671B parameter reasoning model",
    "qwq-32b": "32B parameter efficient reasoning", 
    "llama4-scout": "Specialized domain analysis",
    "llama4-maverick": "Creative research generation",
    "qwen-2.5-vl": "Vision-language for document analysis"
}
```

### API Examples

#### Topic Management
```bash
# Create research topic
POST /topics
{
  "title": "Climate Change Impacts",
  "description": "Comprehensive analysis of climate change effects on global ecosystems",
  "generation_method": "local",
  "metadata": {"priority": "high", "domain": "environmental"}
}

# Generate twin reports
POST /topics/{id}/generate-twin-reports
{
  "models": ["deepseek-r1", "qwq-32b"],
  "max_words": 8000,
  "include_citations": true,
  "research_depth": "comprehensive"
}
```

#### Report Retrieval
```bash
# Get all articles for topic
GET /topics/{id}/articles

# Get specific article
GET /articles/{id}

# Get diff analysis between twin reports
GET /topics/{id}/diff-analysis
```

## Infrastructure

### Core Services

#### PostgreSQL Database
```yaml
# Master database with multiple schemas
Schemas:
  - idea_database: Content ingestion and categorization
  - twin_report: Research management with pgvector
  - shared_services: Cross-platform utilities
  
Extensions:
  - pgvector: Vector similarity search
  - uuid-ossp: UUID generation
  - pg_trgm: Full-text search optimization
```

#### Chroma Vector Database
```bash
# Vector storage for semantic search
Endpoint: http://localhost:8000
Collections:
  - idea_embeddings: Email content vectors
  - research_embeddings: Report and article vectors
  - web_archive_embeddings: Archived content vectors
```

#### MinIO Object Storage
```bash
# WORM-compliant document storage
Console: http://localhost:9001
Buckets:
  - ideas-attachments: Email attachments
  - research-documents: Generated reports
  - web-archives: Cached web content
```

#### Mac Studio LLM Endpoint
```bash
# Local model inference
Endpoint: https://matiass-mac-studio.tail174e9b.ts.net/v1
Models: DeepSeek R1, QwQ-32B, Llama 4 variants, Qwen 2.5VL
Memory: 512GB unified memory for 72B+ models
```

### Data Persistence
All services use named Docker volumes for persistence:
- `postgres_data`: Database files
- `chroma_data`: Vector embeddings
- `minio_data`: Object storage
- Data survives container restarts and system reboots

## API Reference

### Idea Database API

#### Health Check
```http
GET /health
```

#### Process Emails
```http
POST /process-emails
Content-Type: application/json

{
  "force_reprocess": false,
  "limit": 100
}
```

#### List Ideas
```http
GET /ideas?category=research&limit=20&offset=0
```

#### Get Idea Details
```http
GET /ideas/{id}
```

### Twin-Report KB API

#### Topics
```http
GET /topics                    # List all topics
POST /topics                   # Create new topic
GET /topics/{id}              # Get topic details
PUT /topics/{id}              # Update topic
DELETE /topics/{id}           # Delete topic
```

#### Articles
```http
GET /topics/{id}/articles     # Get topic articles
GET /articles/{id}            # Get article details
POST /topics/{id}/generate-twin-reports  # Generate reports
```

#### Analysis
```http
GET /topics/{id}/diff-analysis   # Get gap analysis
GET /articles/{id}/quality      # Get quality checks
```

### Diff Worker API (Port 8103)

#### Diff Analysis
```http
POST /analyze-diff               # Compare twin reports
POST /analyze-gaps               # Multi-article gap analysis
GET /twin-set/{id}/diffs         # Get all diffs for twin set
GET /diff/{id}                   # Get specific diff result
GET /health                      # Service health check
```

#### Request Examples
```bash
# Analyze differences between two reports
curl -X POST http://localhost:8103/analyze-diff \
  -H "Content-Type: application/json" \
  -d '{
    "twin_set_id": "uuid",
    "article_1_id": "uuid", 
    "article_2_id": "uuid",
    "analysis_type": "comprehensive"
  }'

# Perform gap analysis across multiple articles
curl -X POST http://localhost:8103/analyze-gaps \
  -H "Content-Type: application/json" \
  -d '{
    "twin_set_id": "uuid",
    "articles": ["id1", "id2", "id3"],
    "analysis_depth": "standard"
  }'
```

### Frontend Interface API (Port 3000)

#### Web Dashboard
```http
GET /                          # Main dashboard
GET /upload                    # Document upload page
GET /health                    # Service health check
GET /api/health                # API health endpoint
GET /api/services/status       # All services status
```

#### Document Processing
```http
POST /api/upload/file          # Upload document files
POST /api/upload/url           # Process web URL
POST /api/upload/google-doc    # Process Google Doc
GET /api/tasks/{id}/status     # Check processing status
GET /api/statistics            # Platform statistics
```

#### Frontend Features
- **Modern Responsive UI**: Bootstrap 5 with custom CSS animations
- **Drag & Drop Upload**: Multi-file support with real-time validation
- **Service Health Monitoring**: Live status indicators for all backend services
- **Progress Tracking**: Real-time processing status with step indicators
- **Multiple Upload Methods**: Files, URLs, Google Docs with unified interface
- **Document Support**: PDF, DOCX, XLSX, PPTX, TXT, HTML, MD (up to 100MB)

#### Frontend Architecture
```
Frontend (FastAPI + Jinja2)
├── Templates: base.html, index.html, upload.html
├── Static Assets: CSS, JavaScript, responsive design
├── API Client: Async HTTP integration with all backend services
├── Background Tasks: Document processing queue management
└── Service Integration: Topic Manager, Document Parser, Quality Controller, Diff Worker
```

## Deployment Guide

### Prerequisites
- Docker and Docker Compose
- 16GB+ RAM (32GB recommended)
- Access to Mac Studio LLM endpoint

### Step-by-Step Deployment

#### 1. Clone and Configure
```bash
git clone https://github.com/mirvoism/AI-Research-Platform.git
cd AI-Research-Platform
cp config/environment.example .env
# Edit .env with your settings
```

#### 2. Start Core Infrastructure
```bash
docker-compose -f docker-compose.master.yml up -d
```

#### 3. Verify Infrastructure
```bash
# Check all services
docker-compose -f docker-compose.master.yml ps

# Test database
docker exec ai_platform_postgres psql -U ai_user -d ai_platform -c "SELECT 1;"

# Test vector database
curl http://localhost:8000/api/v1/heartbeat

# Test object storage
curl http://localhost:9000/minio/health/ready
```

#### 4. Deploy Sub-Projects
```bash
# Idea Database
cd sub-projects/idea-database
docker-compose up -d

# Twin-Report KB  
cd ../twin-report-kb
docker-compose up -d
```

#### 5. Verify Sub-Projects
```bash
# Test Idea Database
curl http://localhost:8080/health

# Test Twin-Report KB
curl http://localhost:8100/health
```

### Production Configuration

#### Gmail Setup (Idea Database)
```bash
# 1. Gmail account configured: ideaseea@gmail.com
# 2. Enable Gmail API in Google Cloud Console for ideaseea@gmail.com
# 3. Create OAuth2 credentials
# 4. Update config/email_config.yml
# 5. Add credentials to Docker secrets
```

#### Security Hardening
```bash
# Update default passwords in .env
# Configure SSL certificates
# Set up firewall rules
# Enable audit logging
```

## Development

### Local Development Setup
```bash
# Create development environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r sub-projects/idea-database/services/email_processor/requirements.txt
pip install -r sub-projects/twin-report-kb/docker/topic_manager/requirements.txt
```

### Database Migrations
```bash
# Run initial schema setup
docker exec ai_platform_postgres psql -U ai_user -d ai_platform -f /docker-entrypoint-initdb.d/init_schemas.sql

# Apply Twin-Report schema
docker exec ai_platform_postgres psql -U ai_user -d ai_platform -f /app/migrations/twin_report_schema.sql
```

### Testing
```bash
# Test email processing
curl -X POST http://localhost:8080/process-emails

# Test topic creation
curl -X POST http://localhost:8100/topics \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Topic", "description": "Test research topic"}'

# Test report generation
curl -X POST http://localhost:8100/topics/1/generate-twin-reports \
  -H "Content-Type: application/json" \
  -d '{"models": ["deepseek-r1"], "max_words": 1000}'
```

### Monitoring
```bash
# View logs
docker-compose -f docker-compose.master.yml logs -f
docker-compose -f sub-projects/idea-database/docker-compose.yml logs -f
docker-compose -f sub-projects/twin-report-kb/docker-compose.yml logs -f

# Monitor resources
docker stats
```

---

**Last Updated**: January 22, 2025  
**Version**: 2.0 - Both Idea Database and Twin-Report KB implemented 