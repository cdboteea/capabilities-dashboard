# Idea Database Project – **Complete Technical Specification**

> **Version:** 2025-06-14 v1.0  
> **Parent Project:** EEA AI Research Platform  
> **Maintainer:** Matias Mirvois  
> **Status:** *Initial Specification - Ready for Implementation*

---

## 0. Executive Summary

A personal knowledge ingestion system that automatically processes emails containing ideas, URLs, articles, PDFs, and thoughts into a searchable database. The system uses a dedicated Gmail account as the input funnel, with daily AI-powered processing to extract entities, categorize content, and create semantic search capabilities. Built as a sub-project of the EEA AI Research Platform, leveraging existing infrastructure while maintaining complete independence.

```
Gmail Inbox → Email Processor → Content Extractor → AI Analyzer → Database + Vector Store
     ↓              ↓               ↓               ↓              ↓
Email Cleanup   URL Fetching   Entity Extraction  Categorization  Web Dashboard
     ↓              ↓               ↓               ↓              ↓
Archive Storage  PDF Processing   Summary Generation  Search API    Daily Reports
```

*Primary deployment: Mac Studio M3 Ultra with inherited EEA infrastructure*

---

## 1. Project Architecture & Inheritance

### 1.1 EEA AI Research Platform Integration

**Inherited Infrastructure:**
- **Local LLM**: Qwen-3-72B MLX (swappable to API)
- **Vector Database**: Chroma with semantic search capabilities
- **Object Storage**: MinIO WORM for compliance and archival
- **Web Archiver**: Universal markdown archiving service
- **MCP Integration**: Complete development automation
- **Docker Orchestration**: Shared services and networking

**Independent Components:**
- **Gmail Integration**: Dedicated email processing service
- **Content Pipeline**: Custom analysis and categorization
- **Database Schema**: PostgreSQL with idea-specific structure
- **Web Dashboard**: Purpose-built interface for idea management
- **Report Generator**: Daily summaries and discovery reports

### 1.2 Project Structure

```
idea-database/
├── docs/
│   ├── IDEA_DATABASE_SPEC.md          # This document
│   ├── DATABASE_SCHEMA.md             # Detailed schema documentation
│   └── API_DOCUMENTATION.md           # Query interface specifications
├── services/
│   ├── email_processor/               # Gmail API integration
│   │   ├── gmail_client.py           # OAuth2 + Gmail API wrapper
│   │   ├── email_parser.py           # Email content extraction
│   │   └── attachment_handler.py     # File processing (PDF, images, etc.)
│   ├── content_extractor/             # URL and content processing
│   │   ├── url_fetcher.py            # Web scraping with rate limits
│   │   ├── pdf_processor.py          # PDF text extraction
│   │   └── content_cleaner.py        # HTML to markdown conversion
│   ├── ai_processor/                  # LLM analysis and categorization
│   │   ├── llm_client.py             # Qwen-3-72B or API interface
│   │   ├── entity_extractor.py       # Named entity recognition
│   │   ├── categorizer.py            # Content classification
│   │   └── summarizer.py             # Summary generation
│   ├── database_service/              # PostgreSQL + Vector operations
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   ├── vector_ops.py             # Chroma integration
│   │   └── query_engine.py           # Search and retrieval
│   └── web_interface/                 # Dashboard and API
│       ├── api.py                    # FastAPI endpoints
│       ├── dashboard.py              # Streamlit or React interface
│       └── report_generator.py       # Daily reports and insights
├── workflows/
│   ├── daily_processor.py             # Main orchestration script
│   ├── content_pipeline.py           # Extract → Analyze → Store workflow
│   └── report_scheduler.py           # Daily report generation
├── database/
│   ├── schema.sql                    # Initial database structure
│   ├── migrations/                   # Database evolution scripts
│   └── seed_data.sql                 # Initial categories and configuration
├── shared/                           # Inherited from EEA platform
│   ├── llm_service/                  # Shared Qwen-3-72B access
│   ├── vector_db/                    # Shared Chroma instance
│   └── web_archiver/                 # Universal content archival
├── config/
│   ├── gmail_config.yml             # Email processing configuration
│   ├── categories.yml               # Content classification rules
│   └── prompts/                     # LLM prompt templates
├── docker-compose.yml               # Service orchestration
└── requirements.txt                 # Python dependencies
```

---

## 2. Content Categories & Classification

### 2.1 Primary Categories (6 Core Types)

| Category | Description | Example Entities | Auto-Detection Keywords |
|----------|-------------|------------------|------------------------|
| **Personal Thoughts** | Original ideas, reflections, concepts to explore | Topics, concepts, questions | "idea:", "thought:", "explore:", "investigate:" |
| **Dev Tools & Libraries** | GitHub repos, Python packages, development tools | Repository names, package names, frameworks | "github.com", "pypi.org", "npm", "library", "framework" |
| **Research Papers** | Academic papers, studies, technical documents | Authors, institutions, DOIs, methodologies | "arxiv", "doi:", "abstract", "methodology", "findings" |
| **AI Implementations** | Use cases, workflows, implementation examples | Technologies, use cases, workflows | "implementation", "use case", "workflow", "tutorial", "guide" |
| **Industry News** | News articles, company updates, market analysis | Companies, people, products, events | News domains, company names, product releases |
| **Reference Materials** | Documentation, tutorials, how-to guides | Technologies, procedures, tools | "documentation", "tutorial", "how-to", "guide", "reference" |

### 2.2 Entity Types for Extraction

**Primary Entities:**
- **Technologies**: Programming languages, frameworks, AI models, tools
- **People**: Researchers, engineers, thought leaders, authors
- **Companies**: Organizations, startups, institutions
- **Research Papers**: Titles, DOIs, authors, publication venues
- **GitHub Repositories**: Repo names, owners, primary languages
- **Concepts**: Technical concepts, methodologies, approaches

**Secondary Entities:**
- **URLs**: Domain classification, link relationships
- **Dates**: Publication dates, event dates, deadlines
- **Locations**: Geographic references, institutions
- **Products**: Software products, services, platforms

---

## 3. Database Schema Design

### 3.1 Core Tables

```sql
-- Main ideas/entries table
CREATE TABLE ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id VARCHAR(255) UNIQUE NOT NULL,
    message_id VARCHAR(255) NOT NULL,
    subject TEXT,
    sender_email VARCHAR(255),
    sender_name VARCHAR(255),
    received_date TIMESTAMP WITH TIME ZONE,
    processed_date TIMESTAMP WITH TIME ZONE,
    content_type VARCHAR(50), -- 'email', 'url', 'attachment', 'mixed'
    category VARCHAR(50), -- One of the 6 primary categories
    processing_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    ai_summary TEXT,
    original_content TEXT,
    cleaned_content TEXT,
    language VARCHAR(10) DEFAULT 'en',
    needs_manual_review BOOLEAN DEFAULT FALSE,
    priority_score DECIMAL(3,2), -- 0.00 to 1.00
    sentiment_score DECIMAL(3,2), -- -1.00 to 1.00
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- URLs and links extracted from content
CREATE TABLE urls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    domain VARCHAR(255),
    title TEXT,
    description TEXT,
    content_type VARCHAR(50), -- 'article', 'github', 'paper', 'documentation', etc.
    fetch_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'fetched', 'failed', 'blocked'
    archive_path TEXT, -- Path to archived markdown content
    word_count INTEGER,
    fetch_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- File attachments
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_type VARCHAR(50), -- 'pdf', 'image', 'document', etc.
    file_size BIGINT,
    file_path TEXT NOT NULL, -- Path to stored file
    content_hash VARCHAR(64) UNIQUE, -- SHA-256 for deduplication
    extracted_text TEXT, -- For PDFs and documents
    processing_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Extracted entities
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
    entity_type VARCHAR(50), -- 'technology', 'person', 'company', 'repository', etc.
    entity_value TEXT NOT NULL,
    normalized_value TEXT, -- Cleaned/standardized version
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    context_snippet TEXT, -- Surrounding text for context
    source_type VARCHAR(20), -- 'content', 'url', 'attachment'
    source_id UUID, -- Reference to URL or attachment
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Categories and topics
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    color_code VARCHAR(7), -- Hex color for UI
    icon_name VARCHAR(50),
    parent_category_id UUID REFERENCES categories(id),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Topics and tags (many-to-many with ideas)
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category_id UUID REFERENCES categories(id),
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE idea_topics (
    idea_id UUID REFERENCES ideas(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    relevance_score DECIMAL(3,2) DEFAULT 0.50,
    PRIMARY KEY (idea_id, topic_id)
);

-- Vector embeddings (integration with Chroma)
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
    content_type VARCHAR(20), -- 'summary', 'full_content', 'title'
    vector_id VARCHAR(255) NOT NULL, -- Reference to Chroma collection
    embedding_model VARCHAR(100) DEFAULT 'e5-mistral-8B',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Processing logs and audit trail
CREATE TABLE processing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID REFERENCES ideas(id) ON DELETE CASCADE,
    step_name VARCHAR(100) NOT NULL, -- 'email_parse', 'url_fetch', 'ai_analysis', etc.
    status VARCHAR(20) NOT NULL, -- 'started', 'completed', 'failed'
    processing_time_ms INTEGER,
    error_message TEXT,
    metadata JSONB, -- Additional processing details
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3.2 Indexes and Constraints

```sql
-- Performance indexes
CREATE INDEX idx_ideas_received_date ON ideas(received_date DESC);
CREATE INDEX idx_ideas_category ON ideas(category);
CREATE INDEX idx_ideas_processing_status ON ideas(processing_status);
CREATE INDEX idx_ideas_priority_score ON ideas(priority_score DESC);
CREATE INDEX idx_urls_domain ON urls(domain);
CREATE INDEX idx_entities_type_value ON entities(entity_type, entity_value);
CREATE INDEX idx_entities_idea_id ON entities(idea_id);
CREATE INDEX idx_attachments_content_hash ON attachments(content_hash);

-- Full-text search indexes
CREATE INDEX idx_ideas_content_fts ON ideas USING gin(to_tsvector('english', coalesce(ai_summary, '') || ' ' || coalesce(cleaned_content, '')));
CREATE INDEX idx_urls_content_fts ON urls USING gin(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '')));

-- Constraints
ALTER TABLE ideas ADD CONSTRAINT check_priority_score CHECK (priority_score >= 0.00 AND priority_score <= 1.00);
ALTER TABLE ideas ADD CONSTRAINT check_sentiment_score CHECK (sentiment_score >= -1.00 AND sentiment_score <= 1.00);
ALTER TABLE entities ADD CONSTRAINT check_confidence_score CHECK (confidence_score >= 0.00 AND confidence_score <= 1.00);
```

---

## 4. Email Processing Workflow

### 4.1 Gmail Integration Setup

**OAuth2 Configuration:**
```yaml
gmail:
  oauth2:
    client_id: "${GMAIL_CLIENT_ID}"
    client_secret: "${GMAIL_CLIENT_SECRET}"
    redirect_uri: "http://localhost:8080/oauth2callback"
    scopes:
      - "https://www.googleapis.com/auth/gmail.readonly"
      - "https://www.googleapis.com/auth/gmail.modify"
  
  processing:
    inbox_label: "INBOX"
    processed_label: "IDEAS_PROCESSED"
    error_label: "IDEAS_ERROR"
    batch_size: 50
    max_emails_per_run: 200
```

**Email Processing Pipeline:**
```python
class DailyEmailProcessor:
    def process_daily_batch(self):
        """Main daily processing workflow"""
        1. Connect to Gmail API
        2. Fetch unprocessed emails (not labeled as processed)
        3. For each email:
           a. Parse email content and metadata
           b. Extract attachments and save with deduplication
           c. Extract URLs and queue for content fetching
           d. Create initial database entry
           e. Queue for AI processing
           f. Label email as processed
        4. Process AI analysis queue
        5. Generate daily report
        6. Clean up temporary files
```

### 4.2 Content Extraction Pipeline

**URL Processing:**
```python
class URLContentExtractor:
    async def process_url(self, url: str, idea_id: UUID):
        """Extract and archive web content"""
        1. Check if URL already processed (avoid duplicates)
        2. Fetch content with rate limiting and robots.txt respect
        3. Convert HTML to clean markdown
        4. Extract metadata (title, description, author)
        5. Store in MinIO archive following EEA pattern
        6. Update URL record with fetch status and archive path
        7. Queue extracted content for AI analysis
```

**Attachment Processing:**
```python
class AttachmentProcessor:
    def process_attachment(self, attachment_data: bytes, filename: str, idea_id: UUID):
        """Process email attachments"""
        1. Calculate SHA-256 hash for deduplication
        2. Check if file already exists in system
        3. If new:
           a. Save file to secure storage
           b. Extract text content (PDF, DOC, etc.)
           c. Generate thumbnail if image
           d. Create database record
        4. Link attachment to idea
        5. Queue extracted text for AI analysis
```

---

## 5. AI Processing & Analysis

### 5.1 LLM Integration (Swappable Architecture)

**Local LLM Configuration:**
```python
# Local Qwen-3-72B MLX
LOCAL_LLM_CONFIG = {
    "endpoint": "http://qwen-mlx:8080/v1/chat/completions",
    "model": "qwen-3-72b",
    "max_tokens": 4000,
    "temperature": 0.1,
    "timeout": 30
}

# API Fallback Configuration
API_LLM_CONFIG = {
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "model": "gpt-4o-mini",
    "max_tokens": 4000,
    "temperature": 0.1
}

class LLMClient:
    def __init__(self, use_local: bool = True):
        self.config = LOCAL_LLM_CONFIG if use_local else API_LLM_CONFIG
```

### 5.2 AI Analysis Prompts

**Content Categorization Prompt:**
```markdown
Analyze the following content and classify it into one of these 6 categories:

1. **Personal Thoughts** - Original ideas, reflections, concepts to explore
2. **Dev Tools & Libraries** - GitHub repos, Python packages, development tools  
3. **Research Papers** - Academic papers, studies, technical documents
4. **AI Implementations** - Use cases, workflows, implementation examples
5. **Industry News** - News articles, company updates, market analysis
6. **Reference Materials** - Documentation, tutorials, how-to guides

Content to analyze:
{content}

Respond with JSON:
{
  "category": "one of the 6 categories",
  "confidence": 0.95,
  "reasoning": "brief explanation",
  "alternative_category": "second most likely category",
  "language": "en",
  "needs_manual_review": false
}
```

**Entity Extraction Prompt:**
```markdown
Extract entities from the following content. Focus on:
- Technologies (programming languages, frameworks, AI models, tools)
- People (researchers, engineers, authors)
- Companies (organizations, startups, institutions)
- Research Papers (titles, DOIs, authors)
- GitHub Repositories (repo names, owners)
- Concepts (technical concepts, methodologies)

Content:
{content}

Respond with JSON:
{
  "entities": [
    {
      "type": "technology|person|company|paper|repository|concept",
      "value": "entity name",
      "confidence": 0.95,
      "context": "surrounding text snippet"
    }
  ]
}
```

**Summary Generation Prompt:**
```markdown
Create a concise summary of the following content. Focus on:
- Main ideas or concepts
- Key technologies or tools mentioned
- Actionable insights or next steps
- Why this might be interesting for future reference

Keep summary under 200 words and make it searchable.

Content:
{content}

Summary:
```

### 5.3 Processing Quality Control

**Quality Metrics:**
- **Language Detection**: Flag non-English content for manual review
- **Confidence Thresholds**: Categories < 0.7 confidence flagged for review
- **Entity Validation**: Cross-reference extracted entities with known databases
- **Duplicate Detection**: Content similarity scoring to avoid redundant processing
- **Processing Time Limits**: Timeout protection for long-running analysis

---

## 6. Search & Query Interface

### 6.1 Search Capabilities

**Search Types:**
1. **Semantic Search**: Vector similarity using Chroma embeddings
2. **Keyword Search**: Full-text search across content and summaries  
3. **Entity Search**: Find entries containing specific technologies, people, companies
4. **Category Browsing**: List all entries in a specific category
5. **Date Range Filtering**: Search within time periods
6. **Combined Filters**: Mix of semantic + keyword + category + date

**Search API Endpoints:**
```python
# Semantic search
GET /api/search/semantic?q={query}&limit=20&category={category}

# Keyword search  
GET /api/search/keyword?q={query}&limit=20&category={category}&date_from={date}&date_to={date}

# Entity search
GET /api/search/entities?type={entity_type}&value={entity_value}

# Category browsing
GET /api/browse/category/{category_name}?sort=date&order=desc&limit=50

# Combined search
POST /api/search/advanced
{
  "semantic_query": "machine learning optimization",
  "keywords": ["python", "tensorflow"],
  "categories": ["Dev Tools & Libraries", "AI Implementations"],
  "entities": [{"type": "technology", "value": "tensorflow"}],
  "date_range": {"from": "2025-01-01", "to": "2025-06-14"},
  "limit": 50
}
```

### 6.2 Query Response Format

```json
{
  "query": {
    "type": "semantic",
    "query": "machine learning optimization",
    "filters": {"category": "AI Implementations"}
  },
  "results": [
    {
      "id": "uuid",
      "title": "Email subject or extracted title",
      "summary": "AI-generated summary",
      "category": "AI Implementations",
      "received_date": "2025-06-14T10:00:00Z",
      "priority_score": 0.85,
      "relevance_score": 0.92,
      "entities": [
        {"type": "technology", "value": "TensorFlow", "confidence": 0.95},
        {"type": "concept", "value": "neural architecture search", "confidence": 0.88}
      ],
      "urls": [
        {"url": "https://github.com/example/nas-optimization", "title": "NAS Optimization Library"}
      ],
      "attachments": [
        {"filename": "research_paper.pdf", "file_type": "pdf", "file_size": 2048576}
      ]
    }
  ],
  "pagination": {
    "total": 156,
    "page": 1,
    "per_page": 20,
    "total_pages": 8
  }
}
```

---

## 7. Web Dashboard & Reports

### 7.1 Dashboard Interface

**Main Dashboard Sections:**
1. **Quick Search**: Prominent search bar with type-ahead suggestions
2. **Category Browser**: Visual grid of 6 categories with entry counts
3. **Recent Additions**: Latest processed ideas with quick preview
4. **Top Entities**: Most mentioned technologies, people, companies
5. **Statistics**: Processing metrics, growth trends, category distribution

**Category Browse View:**
- List/grid toggle for entries in selected category
- Sort options: date, priority score, relevance
- Filter by entities, date ranges, processing status
- Bulk actions: export, tag, mark for review

**Detail View:**
- Full content display with original email context
- Extracted entities with confidence scores
- Related URLs with fetch status and archive links
- Attachments with preview capabilities
- Edit capabilities for manual corrections

### 7.2 Daily Reports

**Daily Processing Summary:**
```markdown
# Idea Database Daily Report - {date}

## Processing Summary
- **Total Emails Processed**: 12
- **New Ideas Added**: 12
- **URLs Fetched**: 23
- **Attachments Processed**: 4
- **Processing Errors**: 1

## Category Breakdown
- Personal Thoughts: 3
- Dev Tools & Libraries: 4  
- Research Papers: 2
- AI Implementations: 2
- Industry News: 1
- Reference Materials: 0

## Top Entities Discovered
- **Technologies**: PyTorch, LangChain, Cursor IDE
- **Companies**: Anthropic, OpenAI, Hugging Face
- **People**: Andrej Karpathy, Yann LeCun
- **Repositories**: microsoft/playwright, facebook/react

## High Priority Items
- [AI Implementation] "Building Multi-Agent Systems with LangGraph"
- [Research Paper] "Attention Is All You Need - Revisited" 
- [Dev Tool] "New Python package for LLM evaluation"

## Items Needing Manual Review
- [Email ID: abc123] Non-English content detected
- [Email ID: def456] Low confidence categorization (0.65)
```

**Weekly Discovery Reports:**

**"Ideas to Investigate" Report:**
```markdown
# Weekly Ideas to Investigate - {week_of}

Based on your collected ideas, here are research directions worth exploring:

## Emerging Patterns
- **Multi-Agent Systems**: 5 references this week, increasing trend
- **LLM Evaluation**: 3 new frameworks discovered
- **Code Generation**: Growing focus on specialized models

## Research Opportunities
1. **Cross-Modal AI Applications**
   - Sources: 3 research papers, 2 implementation examples
   - Gap: Limited practical tutorials for beginners
   - Suggestion: Create comprehensive guide bridging theory to practice

2. **Local LLM Optimization**
   - Sources: 4 GitHub repos, 2 technical articles  
   - Gap: Performance benchmarking across different hardware
   - Suggestion: Systematic comparison study

## Underexplored Areas
- Quantum machine learning implementations
- AI-assisted database optimization
- Privacy-preserving ML techniques
```

**"AI Innovations Report":**
```markdown
# New AI Implementations & Innovations - {week_of}

## Breakthrough Applications
1. **Real-time Code Review AI**
   - Source: GitHub repo with 2.3k stars
   - Innovation: Context-aware suggestions with diff analysis
   - Potential: Integration with existing development workflow

2. **Multi-modal Research Assistant**  
   - Source: Research paper + implementation
   - Innovation: PDF + code + documentation understanding
   - Potential: Perfect for research workflow automation

## Notable Tools & Libraries
- **LangGraph 0.2**: New multi-agent orchestration capabilities
- **Cursor AI**: Advanced code completion with codebase context
- **OpenAI o1**: New reasoning model with improved performance

## Implementation Trends
- Increased focus on local deployment and privacy
- Better integration between different AI modalities
- Emphasis on developer experience and ease of use
```

---

## 8. Implementation Roadmap

### 8.1 Phase 1: Foundation (Days 1-5)
**Core Infrastructure:**
- [ ] Database schema implementation and migration scripts
- [ ] Gmail API integration with OAuth2 setup  
- [ ] Basic email parsing and attachment handling
- [ ] Integration with existing EEA infrastructure (Chroma, MinIO)
- [ ] Simple command-line processing script

**Deliverables:**
- Functional database with initial schema
- Gmail connection and basic email fetching
- File storage with deduplication
- Basic content extraction pipeline

**Effort**: 30 hours

### 8.2 Phase 2: AI Processing (Days 6-10)
**Intelligence Layer:**
- [ ] LLM client with local/API switching
- [ ] Content categorization system with prompts
- [ ] Entity extraction pipeline
- [ ] Summary generation workflow
- [ ] Vector embedding integration with Chroma

**Deliverables:**
- Complete AI analysis pipeline
- Content categorization with 6 primary categories
- Entity extraction and storage
- Semantic search capabilities via vector embeddings

**Effort**: 25 hours

### 8.3 Phase 3: Search & Interface (Days 11-15)
**Query & Dashboard:**
- [ ] Search API with multiple search types
- [ ] Web dashboard with category browsing
- [ ] Detailed view for individual ideas
- [ ] Basic export functionality
- [ ] Admin interface for manual corrections

**Deliverables:**
- Functional web interface for searching and browsing
- API endpoints for all search capabilities
- User-friendly dashboard with category organization
- Manual review workflow for edge cases

**Effort**: 35 hours

### 8.4 Phase 4: Reports & Automation (Days 16-20)
**Automation & Intelligence:**
- [ ] Daily processing automation with scheduling
- [ ] Report generation system
- [ ] Weekly discovery reports with trend analysis
- [ ] Email cleanup and organization
- [ ] Performance monitoring and optimization

**Deliverables:**
- Fully automated daily processing
- Daily and weekly reports
- Complete email workflow automation
- Production-ready system with monitoring

**Effort**: 20 hours

### 8.5 Phase 5: Enhancement & Polish (Days 21-25)
**Production Ready:**
- [ ] Error handling and recovery procedures
- [ ] Performance optimization and caching
- [ ] Advanced search features
- [ ] Mobile-responsive dashboard
- [ ] Documentation and user guides

**Deliverables:**
- Production-quality system with comprehensive error handling
- Optimized performance for large datasets  
- Complete documentation for maintenance and extension
- Mobile-friendly interface

**Effort**: 20 hours

---

## 9. Technical Configuration

### 9.1 Docker Orchestration

```yaml
# docker-compose.yml
version: '3.8'
services:
  idea-database:
    build: .
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/idea_database
      - CHROMA_ENDPOINT=http://chroma:8000
      - LLM_ENDPOINT=http://qwen-mlx:8080/v1
      - MINIO_ENDPOINT=http://minio:9000
      - GMAIL_CLIENT_ID=${GMAIL_CLIENT_ID}
      - GMAIL_CLIENT_SECRET=${GMAIL_CLIENT_SECRET}
    volumes:
      - ./data:/app/data
      - ./attachments:/app/attachments
    depends_on:
      - postgres
      - chroma  # Inherited from EEA platform
      - qwen-mlx  # Inherited from EEA platform
      - minio  # Inherited from EEA platform
    networks:
      - idea_database_network
      - eea_platform_network  # Shared network for EEA services

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=idea_database
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    ports:
      - "5433:5432"  # Avoid conflict with EEA postgres
    networks:
      - idea_database_network

  web-dashboard:
    build: ./services/web_interface
    ports:
      - "8081:8080"  # Avoid conflict with EEA services
    environment:
      - API_ENDPOINT=http://idea-database:8000
    depends_on:
      - idea-database
    networks:
      - idea_database_network

volumes:
  postgres_data:

networks:
  idea_database_network:
    driver: bridge
  eea_platform_network:
    external: true  # Connect to existing EEA network
```

### 9.2 Environment Configuration

```bash
# .env file
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
GMAIL_REDIRECT_URI=http://localhost:8080/oauth2callback

DATABASE_URL=postgresql://postgres:password@localhost:5433/idea_database
CHROMA_ENDPOINT=http://localhost:8000
LLM_ENDPOINT=http://localhost:8080/v1
MINIO_ENDPOINT=http://localhost:9000

# Processing Configuration
DAILY_PROCESSING_TIME=09:00
MAX_EMAILS_PER_RUN=200
BATCH_SIZE=50
MAX_URL_FETCH_SIZE=10MB
SUPPORTED_ATTACHMENT_TYPES=pdf,doc,docx,txt,md,jpg,png

# LLM Configuration
USE_LOCAL_LLM=true
LLM_MODEL=qwen-3-72b
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4000
API_FALLBACK_MODEL=gpt-4o-mini
```

---

## 10. Quality Assurance & Monitoring

### 10.1 Processing Quality Metrics

**Accuracy Targets:**
- Category classification accuracy: > 85%
- Entity extraction precision: > 90%
- URL fetch success rate: > 95%
- Duplicate detection accuracy: > 99%

**Performance Targets:**
- Email processing: < 30 seconds per email
- URL content extraction: < 10 seconds per URL
- AI analysis: < 45 seconds per item
- Search response time: < 2 seconds
- Daily processing completion: < 30 minutes total

### 10.2 Monitoring Dashboard

**Key Metrics:**
- Daily processing success rate
- Category distribution trends
- Entity extraction accuracy
- Search query performance
- Storage utilization
- LLM API costs (if using external APIs)

**Alerts:**
- Processing failures > 5%
- Unusual category distribution changes
- Storage space approaching limits
- LLM response time degradation
- Gmail API quota approaching limits

---

## 11. Security & Privacy

### 11.1 Data Protection

**Email Security:**
- OAuth2 authentication with minimal scopes
- Local storage of processed emails (no cloud exposure)
- Automatic email labeling and organization
- Secure credential storage

**Content Security:**
- SHA-256 hashing for file deduplication
- Encrypted storage for sensitive attachments
- No external API calls for sensitive content (local LLM preferred)
- Complete audit trail of all processing

### 11.2 Privacy Controls

**Data Retention:**
- Configurable retention policies per content type
- Automatic cleanup of temporary processing files
- GDPR-compliant data deletion capabilities
- Export functionality for data portability

---

## 12. Future Extensions

### 12.1 Integration Opportunities

**EEA Platform Integration:**
- Cross-reference ideas with research projects
- Shared entity database for improved recognition
- Integrated search across both platforms
- Event routing for high-priority discoveries

**External Integrations:**
- Notion/Obsidian export for note-taking workflows
- Slack/Discord notifications for interesting discoveries
- GitHub integration for automatic repository tracking
- RSS feed generation for sharing insights

### 12.2 Advanced Features

**AI Enhancements:**
- Trend analysis and pattern recognition
- Automatic idea clustering and relationship mapping
- Personalized recommendation engine
- Intelligent content prioritization

**Workflow Improvements:**
- Mobile app for quick idea capture
- Browser extension for one-click saving
- Voice memo processing and transcription
- Collaborative features for team use

---

## 13. Quick-Start Context for New Sessions

> **Idea Database Project:** Personal knowledge ingestion system that processes emails containing ideas, URLs, articles, and PDFs into a searchable database. Built as sub-project of EEA AI Research Platform, inheriting Qwen-3-72B MLX, Chroma vector DB, and MinIO storage. Features: Gmail integration, 6-category classification (Personal Thoughts, Dev Tools, Research Papers, AI Implementations, Industry News, Reference Materials), semantic search, daily reports, and web dashboard. Current phase: Ready for implementation with complete specification.

*Copy this paragraph into new sessions to load complete project context.*

---

**This specification provides a complete blueprint for implementing the Idea Database as a sophisticated sub-project that leverages the EEA AI Research Platform's infrastructure while maintaining independence and focused functionality.**