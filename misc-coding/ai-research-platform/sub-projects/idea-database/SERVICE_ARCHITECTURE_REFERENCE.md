# Service Architecture Reference - Modern Knowledge Graph System

**Last Updated:** January 17, 2025  
**Status:** ✅ **PRODUCTION READY** - Complete Email→Entity Traceability  
**Purpose:** Architectural reference for modern knowledge graph-based email processing pipeline

---

## 🎯 Modern System Overview

The AI Research Platform processes emails into a structured knowledge graph using Mac Studio LLM endpoint with complete traceability from emails to extracted entities and relationships.

### **Core Architecture Principles**
- **Complete Traceability**: Every entity/relationship links back to source email via `source_email_id`
- **Modern Taxonomy**: Database-driven 9-node semantic taxonomy (concept, organization, technology, etc.)
- **LLM-Powered Extraction**: Mac Studio endpoint (`llama4:scout`) for intelligent entity extraction
- **Service Separation**: Clear boundaries with no functional duplication

---

## 🚀 Service Responsibilities Matrix

| Service | Primary Purpose | Input → Output | Database Tables Used |
|---------|----------------|----------------|----------------------|
| **Email Processor** | Gmail integration & orchestration | Gmail → source_emails + orchestration | `source_emails`, `urls`, `attachments` |
| **AI Processor** | LLM-powered knowledge extraction | Email content → entities/relationships | `knowledge_graph_nodes`, `knowledge_graph_edges`, `taxonomy_*` |
| **Content Extractor** | Binary file processing | PDF/Word/Images → raw text | `attachments`, `conversion_jobs` |
| **Pre-Processor** | Text normalization | HTML/markdown → cleaned text | N/A (stateless processing) |
| **Web Interface** | User interface & visualization | API calls → web dashboard | All tables (read-only) |

---

## 🔗 Modern Data Flow Architecture

### **Primary Email Processing Pipeline**
```
Gmail API → Email Processor → {
    1. Store in source_emails table
    2. Extract URLs → urls table (with source_email_id FK)
    3. Extract Attachments → attachments table (with source_email_id FK)
    4. Send content to AI Processor
}

AI Processor → {
    1. Query database taxonomy (taxonomy_node_types, taxonomy_edge_types)
    2. Call Mac Studio LLM (llama4:scout) for entity extraction
    3. Store entities → knowledge_graph_nodes (with source_email_id FK)
    4. Store relationships → knowledge_graph_edges (with source_email_id FK)
}

Binary Attachments → Content Extractor → {
    1. Convert PDF/Word/Images to text
    2. Upload to Google Drive
    3. Update attachment record with drive_file_id
}
```

### **Complete Traceability Schema**
```sql
source_emails.id (UUID)
├── knowledge_graph_nodes.source_email_id (FK) → Entities extracted from this email
├── knowledge_graph_edges.source_email_id (FK) → Relationships extracted from this email  
├── urls.source_email_id (FK) → URLs found in this email
└── attachments.source_email_id (FK) → Files attached to this email
```

---

## 🧠 LLM Integration Architecture

### **Mac Studio LLM Endpoint**
- **Endpoint**: `https://matiass-mac-studio.tail174e9b.ts.net/v1`
- **Model**: `llama4:scout`
- **Purpose**: Extract entities and relationships using database-driven taxonomy

### **Taxonomy-Driven Extraction**
```python
# AI Processor queries live taxonomy from database
node_types = fetch_from_db("taxonomy_node_types")  # concept, organization, technology...
edge_types = fetch_from_db("taxonomy_edge_types")  # is-a, part-of, related-to...

# LLM prompt includes current taxonomy definitions
prompt = f"Extract entities using ONLY these types: {node_types}..."
```

---

## 🏗️ Database Schema Summary

### **Modern Tables (Current Production)**
```sql
-- Email Storage
source_emails (id, gmail_message_id, subject, sender_email, cleaned_content...)

-- Knowledge Graph  
knowledge_graph_nodes (id, name, node_type, source_email_id, description...)
knowledge_graph_edges (id, source_node_id, target_node_id, edge_type, source_email_id...)

-- Taxonomy System
taxonomy_node_types (id, name, color, definition...)
taxonomy_edge_types (id, name, color, definition...)

-- Assets
urls (id, url, domain, title, source_email_id...)
attachments (id, filename, file_type, drive_file_id, source_email_id...)
```

### **Legacy Tables (Maintained for Compatibility)**
```sql
-- Legacy schema still exists but not actively used
ideas, entities, categories (legacy pipeline tables)
```

---

## ⚠️ Critical Integration Rules

### **🚨 NEVER DUPLICATE THESE FUNCTIONS**

#### **LLM Entity Extraction**
- ✅ **ONLY in AI Processor**: Single source of truth for entity/relationship extraction
- ❌ **Never in**: Email Processor, Pre-Processor, Content Extractor
- **Reason**: Maintains consistency with database taxonomy

#### **Database Taxonomy Management**  
- ✅ **ONLY in AI Processor**: Reads/writes taxonomy tables
- ❌ **Never in**: Other services (read-only access only)
- **Reason**: Prevents taxonomy corruption

#### **source_email_id Foreign Keys**
- ✅ **REQUIRED**: All extracted data MUST link to source_emails.id
- ❌ **Never**: Orphaned entities without email traceability
- **Reason**: Enables email→entity editing in UI

### **🔄 Service Communication Patterns**

#### **Email Processor → AI Processor**
```python
# Email Processor sends content for analysis
POST /ai_processor/process/email
{
    "email_id": "gmail_message_id", 
    "subject": "...",
    "body": "...",
    "sender": "...",
    "timestamp": "..."
}
```

#### **AI Processor → Database**
```python
# AI Processor stores with complete traceability
INSERT INTO knowledge_graph_nodes (name, node_type, source_email_id, ...)
INSERT INTO knowledge_graph_edges (source_node_id, target_node_id, source_email_id, ...)
```

---

## 📊 API Endpoint Architecture

### **Production Endpoints (Web Interface)**
```
GET  /dashboard/stats          → Dashboard metrics
GET  /ideas                   → Source emails (legacy compatibility)
GET  /knowledge-graph         → All nodes and edges  
GET  /urls                    → Extracted URLs with email links
GET  /drive/files            → Google Drive attachments
POST /process-emails         → Trigger email processing
```

### **AI Processing Endpoints**
```
POST /process/email          → Process single email
GET  /taxonomy/nodes         → Dynamic node types
GET  /taxonomy/edges         → Dynamic edge types
POST /extract/manual         → Manual LLM extraction
```

---

## 🎯 Current Production Status

### **✅ Fully Operational**
- Email processing with anti-duplication safeguards
- Mac Studio LLM integration with taxonomy compliance  
- Complete email→entity→relationship traceability
- URL and attachment extraction with email linkage
- Modern knowledge graph visualization
- Google Drive integration for attachment storage

### **📊 Verified Metrics**
- **Emails Processed**: Multiple production emails
- **Entity Extraction**: 100% compliance with database taxonomy
- **Traceability**: 100% of entities/relationships link to source emails
- **URL/Attachment Extraction**: Working with proper FK linkages
- **Anti-Duplication**: Confirmed working via Gmail client tracking

---

## 🔄 Deployment Architecture

### **Docker Containers**
```
ai_platform_postgres     → Database (all tables)
idea_db_email_processor  → Gmail integration & orchestration  
idea_db_ai_processor     → LLM extraction & taxonomy
idea_db_content_extractor → Binary file processing
idea_db_pre_processor    → Text normalization
idea_db_web_interface    → React frontend
idea_db_redis           → Task queue (optional)
```

### **External Dependencies**
```
Mac Studio LLM Endpoint → https://matiass-mac-studio.tail174e9b.ts.net/v1
Gmail API              → OAuth integration with ideaseea@gmail.com
Google Drive API       → File upload/storage for attachments
```

---

## ✅ Completed Implementation Status (January 2025)

### **Phase 2: API Enhancement** ✅ **COMPLETED**
- Created `/source-emails/{id}/knowledge-graph` endpoints ✅
- Added email-specific entity editing capabilities ✅ 
- Implemented taxonomy CRUD operations via web interface ✅
- Enhanced search and filter API endpoints ✅

### **Phase 3: Frontend Modernization** ✅ **COMPLETED**
- Updated EmailDetail component to show extracted entities ✅
- Replaced legacy category dropdown with modern taxonomy editing ✅
- Implemented visual email→entity relationship editing ✅
- Added comprehensive search and filter interface ✅

### **Phase 4: Advanced Features** ✅ **COMPLETED**
- Multi-field search across subject, content, and sender ✅
- Entity type filtering (concept, organization, technology) ✅  
- Sender filtering with dynamic autocomplete ✅
- Visual filter interface with tags and reset functionality ✅
- Enhanced dashboard metrics and processing activity charts ✅

### **Additional Enhancements Beyond Original Plan** ✅ **COMPLETED**
- PostgreSQL full-text search with ranking ✅
- Combined search+filter operations ✅
- Real-time filter updates and performance optimization ✅

---

**✅ System Status**: Production ready with complete email→entity traceability, modern knowledge graph architecture, and advanced search/filter capabilities. All planned development phases completed. 