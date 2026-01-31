# AI Research Platform - Email Processing Pipeline

> **Status**: ✅ Production Ready (Verified July 2025)  
> **Pipeline Documentation**: 📋 [Complete Architecture Reference](docs/EMAIL_PROCESSING_PIPELINE.md)

## 🎯 Overview

The Email Processing Pipeline automatically converts Gmail emails into structured knowledge graphs with Google Drive file storage. This system processes emails in real-time, extracting entities, relationships, and files to create a searchable knowledge base.

**Live System**: Currently processing emails with full knowledge graph extraction and Drive integration.

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- PostgreSQL database (`ai_platform_postgres`)
- Mac Studio LLM endpoint (llama4:scout)
- Gmail API credentials with OAuth
- Google Drive API credentials

### Launch Pipeline
```bash
cd sub-projects/idea-database
docker-compose up -d
```

### Process Emails
```bash
curl -X POST http://localhost:3003/process-emails
```

### Access Dashboard
```bash
open http://localhost:3000
```

---

## 🏗️ Architecture

### Services (5 Microservices)
1. **Email Processor** (port 3003) - Gmail integration & orchestration
2. **AI Processor** (port 8001) - LLM entity extraction 
3. **Content Extractor** (port 8002) - File processing & Drive uploads
4. **Pre Processor** (port 8003) - Text normalization
5. **Web Interface** (port 3000) - React dashboard

### Data Flow
```
Gmail → Email Processor → AI Processor → Knowledge Graph
                    ↓
         Content Extractor → Google Drive
                    ↓
              Web Interface Dashboard
```

### Database Schema
- `source_emails` - Primary email records
- `knowledge_graph_nodes` - Extracted entities
- `knowledge_graph_edges` - Entity relationships  
- `attachments` - File metadata with Drive integration
- `conversion_jobs` - Asynchronous processing queue

---

## 📊 Current Status

### ✅ Verified Working Features
- **Email Processing**: 5 emails processed ✅
- **Knowledge Graph**: 31 entities, 22 relationships ✅
- **Drive Integration**: File upload pipeline operational ✅
- **Dashboard**: Real-time stats and visualization ✅
- **Search & Filtering**: Full-text search with entity filters ✅
- **Anti-duplication**: Gmail-level duplicate prevention ✅

### 📈 Processing Stats
```sql
source_emails: 5 records
knowledge_graph_nodes: 31 records  
knowledge_graph_edges: 22 records
attachments: 1 Drive file (95KB)
conversion_jobs: All completed successfully
```

---

## 🔗 Key Resources

| Resource | Description | Path |
|----------|-------------|------|
| **🏗️ Complete Pipeline Docs** | Comprehensive architecture reference | [docs/EMAIL_PROCESSING_PIPELINE.md](docs/EMAIL_PROCESSING_PIPELINE.md) |
| **⚙️ Docker Compose** | Service deployment configuration | [docker-compose.yml](docker-compose.yml) |
| **🗄️ Database Schema** | PostgreSQL table definitions | [database/schema.sql](database/schema.sql) |
| **📊 Dashboard** | Web interface for email management | http://localhost:3000 |
| **🔌 API Endpoints** | REST API documentation | [docs/EMAIL_PROCESSING_PIPELINE.md#service-architecture](docs/EMAIL_PROCESSING_PIPELINE.md#service-architecture) |

---

## 🛠️ Common Operations

### Monitor System Health
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Check Processing Stats
```bash
curl -s http://localhost:3003/dashboard/stats | jq
```

### View Logs
```bash
docker logs idea_db_email_processor    # Email processing
docker logs idea_db_ai_processor       # LLM extraction  
docker logs idea_db_content_extractor  # File processing
```

### Database Queries
```sql
-- Check email processing
SELECT COUNT(*) FROM idea_database.source_emails;

-- Check knowledge graph  
SELECT COUNT(*) FROM idea_database.knowledge_graph_nodes;

-- Check Drive files
SELECT filename, storage_type FROM idea_database.attachments 
WHERE storage_type = 'drive';
```

---

## 🔧 Troubleshooting

### Issue: No Emails Processing
**Check**: Gmail OAuth tokens, PostgreSQL connectivity, AI Processor endpoint

### Issue: Files Not Uploading to Drive  
**Check**: Drive OAuth tokens, conversion job creation, Content Extractor logs

### Issue: Empty Knowledge Graph
**Check**: AI Processor database connection, Mac Studio LLM endpoint

### Issue: Dashboard Not Loading
**Check**: Email Processor API responses, database connectivity, CORS settings

---

## 📖 Documentation

- **📋 [Complete Pipeline Architecture](docs/EMAIL_PROCESSING_PIPELINE.md)** - Comprehensive system documentation
- **🏗️ [Service Details](docs/EMAIL_PROCESSING_PIPELINE.md#service-architecture)** - Individual service specifications  
- **🗄️ [Database Schema](docs/EMAIL_PROCESSING_PIPELINE.md#database-schema-postgresql)** - Table definitions and relationships
- **🔄 [Data Flow](docs/EMAIL_PROCESSING_PIPELINE.md#complete-data-flow)** - End-to-end processing explanation
- **⚙️ [Configuration](docs/EMAIL_PROCESSING_PIPELINE.md#configuration--deployment)** - Environment and deployment settings

---

## 🎯 System Verification

**Last Verified**: July 19, 2025  
**Pipeline Status**: ✅ Fully Operational  
**Data Processing**: ✅ Gmail → Knowledge Graph → Drive Storage  
**Frontend**: ✅ Dashboard + Search + Filtering  
**File Handling**: ✅ PDF → Drive Upload Working

**Contact**: See pipeline documentation for detailed troubleshooting and architecture details. 