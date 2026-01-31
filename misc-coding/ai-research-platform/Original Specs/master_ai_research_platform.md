# AI-Enabled Research & Decision-Support Platform – **Master Technical Specification**

> **Version:** 2025‑06‑01 v1.0   > **Maintainer:** Matias Mirvois   > **Status:** *Active Master Project*

---

## 0. Executive Snapshot

A comprehensive self-hosted "intel fabric" that ingests global information, maintains vectorized knowledge-bases, links events to client positions, and provides automated decision support. The platform combines real-time news crawling, deep research capabilities, portfolio-aware event routing, and automated trade suggestions in a fully compliant, audit-ready system optimized for Mac Studio M3 Ultra deployment.

```
Public Web Sources → Browser-Use Crawler → Event Mapper → Decision Agent
         ↓                    ↓              ↓            ↓
    MinIO WORM Storage    Chroma Vector     Holdings     Dashboard
         ↓                    ↓              ↓            ↓
    Compliance Audit    Knowledge Graph   Risk Pulse    Trade Suggestions
```

*Primary deployment: Mac Studio M3 Ultra with cloud migration readiness via endpoint switching.*

---

## 1. Strategic Architecture & Sub-Project Hierarchy

### 1.1 Master Project Structure

```
AI-Research-Platform/                    # Master project root
├─ docs/
│   ├─ MASTER_SPEC.md                   # This document - master specification
│   ├─ ARCHITECTURE.md                  # Overall system architecture
│   ├─ COMPLIANCE.md                    # SEC 17a-4 and regulatory requirements
│   └─ sub-projects/                    # Sub-project specifications
│       ├─ twin-report-kb/              # Research knowledge base sub-project
│       ├─ real-time-intel/             # News crawling and event processing
│       ├─ decision-support/            # Trading decision automation
│       └─ risk-dashboard/              # UI and visualization layer
├─ services/                            # Shared infrastructure services
│   ├─ chroma_service/                  # Vector database management
│   ├─ qwen_mlx_service/               # Local LLM inference engine
│   ├─ compliance_service/              # Audit and regulatory compliance
│   ├─ web_archiver/                    # Universal web content archival service
│   └─ event_router/                    # Cross-project event routing
├─ sub-projects/                        # Individual sub-project implementations
│   ├─ twin-report-kb/                  # → Links to Twin-Report KB spec
│   ├─ real-time-intel/
│   ├─ decision-support/
│   └─ risk-dashboard/
├─ shared/                              # Common utilities and libraries
│   ├─ models/                          # Shared data models
│   ├─ auth/                            # Authentication and authorization
│   ├─ archival/                        # Web content archival utilities
│   └─ monitoring/                      # Cross-platform observability
├─ archives/                            # Centralized web content archive
│   ├─ markdown/                        # All web content as markdown
│   ├─ raw_html/                        # Original HTML for reference
│   ├─ assets/                          # Images, PDFs, and media files
│   └─ metadata/                        # Archive metadata and indexing
├─ docker-compose.master.yml            # Master orchestration
└─ docker-compose.override.yml          # Environment-specific overrides
```

### 1.2 Sub-Project Classification

| Sub-Project | Purpose | Dependencies | Status |
|-------------|---------|--------------|--------|
| **Twin-Report KB** | Deep research & knowledge management | Chroma, MLX, Compliance | ✅ Specified |
| **Real-Time Intel** | News crawling & event processing | Browser-Use, NATS, Event Router | 🔄 In Planning |
| **Decision Support** | Trading suggestions & risk analysis | Holdings data, Event Router, MLX | 📋 Planned |
| **Risk Dashboard** | UI, widgets, and visualization | All sub-projects via APIs | 📋 Planned |

---

## 2. Master System Architecture (Mac Studio M3 Ultra Optimized)

### 2.1 Hardware Target Specification
- **Mac Studio M3 Ultra**: 76-core GPU, 512GB unified memory, macOS 14.4+
- **Storage**: Encrypted APFS with automated snapshots
- **Network**: 10GbE for high-speed data ingestion
- **Backup**: Time Machine + MinIO object-lock for compliance

### 2.2 Core Infrastructure Stack

| Service | Image Tag | Purpose | Resource Allocation |
|---------|-----------|---------|-------------------|
| **qwen3-mlx** | `qwen-mlx:arm64` | Local LLM inference (72B 4-bit) | 400GB RAM, 76-core GPU |
| **chroma** | `chroma:arm64` | Vector database & embeddings | 50GB RAM, 8 cores |
| **mongodb** | `mongo:arm64` | Alternative vector search | 32GB RAM, 4 cores |
| **nats** | `nats:arm64` | Message bus & event routing | 4GB RAM, 2 cores |
| **minio** | `minio:arm64` | S3-compatible WORM storage | 16GB RAM, 4 cores |
| **airflow** | `airflow:arm64` | Workflow orchestration | 8GB RAM, 4 cores |
| **browser-use** | `browser-use:arm64` | Web crawling & automation | 8GB RAM, 4 cores |
| **web-archiver** | `web-archiver:arm64` | Universal web content archival | 4GB RAM, 2 cores |
| **agents-api** | `agents-api:arm64` | FastAPI + LangChain coordination | 4GB RAM, 2 cores |
| **dashboard-frontend** | `dashboard:arm64` | React UI & widgets | 2GB RAM, 2 cores |

### 2.3 Inter-Service Communication

```yaml
# Master docker-compose.yml excerpt
networks:
  ai_platform:
    driver: bridge
    internal: false
  compliance_network:
    driver: bridge
    internal: true
  sub_project_network:
    driver: bridge
    internal: false

volumes:
  shared_models:
    driver: local
  compliance_logs:
    driver: local
  vector_storage:
    driver: local
```

---

## 3. Use-Case Matrix & Performance Targets

| ID | Capability | Impact Target | Cadence | Input → Output | Success KPI |
|----|------------|---------------|---------|----------------|-------------|
| **N-1** | News Crawler | Remove manual triage | 5 min cycle | HTML/RSS → tagged JSON | Recall@10 > 95% |
| **N-2** | Macro Calendar | 15 min earlier alerts | Real-time | Stats pages → events | Alert latency < 2 min |
| **R-1** | Knowledge Graph Q&A | 30% faster memos | Ad-hoc | NL query → cited answer | Answer accuracy > 90% |
| **R-2** | Auto Topic Refinement | Corpus stays current | Nightly | New docs → updated tags | Topic precision > 85% |
| **H-1** | Holdings Event Router | Surface relevant events | < 5 min | News + positions → alerts | Routing precision > 80% |
| **D-1** | Decision Suggestions | 50% less manual screening | Hourly | Events + factors → trades | PM acceptance > 60% |
| **D-2** | On-Demand Analysis | Instant bespoke analytics | Ad-hoc | NL prompt → chart + prose | Turnaround < 30s |
| **S-1** | Risk Pulse Widgets | Zero stale dashboards | Continuous | Events + trades → UI | Ops tickets < 5/month |

---

## 4. Hot-Swap Technology Matrix

| Layer | Mac Studio Default | Cloud Alternative | Switch Mechanism |
|-------|-------------------|-------------------|------------------|
| **Web Crawling** | Browser-Use + Playwright | Diffbot API | Airflow operator config |
| **Vector DB** | Chroma local | MongoDB Atlas/Pinecone | `VECTOR_ENDPOINT` env var |
| **Embeddings** | e5-mistral-8B (llama.cpp) | OpenAI ada-002 | `EMBED_ENGINE` setting |
| **LLM Inference** | Qwen-3-72B 4-bit MLX | GPT-4o/Claude 3.5 | `LLM_ENDPOINTS` config |
| **Object Storage** | MinIO WORM local | S3 Object-Lock | URL & credentials |
| **Orchestration** | Airflow + LangChain | CrewAI cloud | pip dependencies + DAG |
| **Code Sandbox** | Docker Python local | ChatGPT Code Interpreter | Agent configuration flag |

---

## 5. Cross-Platform Service Specifications

### 5.1 Event Router (Shared Infrastructure)

**Purpose**: Route events between sub-projects and external systems
**Technology**: Rust microservice for performance
**Message Format**:
```json
{
  "event_id": "uuid",
  "source_project": "twin-report-kb|real-time-intel|decision-support",
  "event_type": "research_complete|news_alert|decision_required",
  "severity": 0.82,
  "metadata": {
    "region": "EMEA|AMER|APAC",
    "topic_tags": ["AI", "regulation"],
    "holdings_relevance": ["AAPL", "MSFT"]
  },
  "payload": "base64_encoded_data",
  "timestamp": "2025-06-01T10:00:00Z"
}
```

### 5.2 Compliance Service (SEC 17a-4 Ready)

**Audit Trail Features**:
- **Immutable Logging**: All decisions, data sources, and reasoning chains
- **WORM Storage**: MinIO object-lock for tamper-proof records
- **PII Protection**: Hash account IDs before LLM processing
- **Access Controls**: Role-based permissions with full audit logs
- **Data Retention**: Configurable retention policies per data type

**Monitoring Endpoints**:
```yaml
GET /compliance/audit-trail/{date_range}
GET /compliance/pii-scan/{project}
POST /compliance/quarantine/{document_id}
GET /compliance/retention-status
```

### 5.4 Universal Web Archiver (Shared Infrastructure)

**Purpose**: Automatically archive all web content accessed by any service across all sub-projects
**Technology**: Python service with markdown conversion capabilities
**Storage**: MinIO WORM storage for compliance and PostgreSQL metadata

**Archival Pipeline**:
```python
# Automatic archival for all web requests
@web_request_interceptor
def archive_web_content(url: str, content: str, source_service: str):
    """
    Intercepts all web requests across the platform and archives content
    """
    archive_record = {
        "url": url,
        "content_html": content,
        "content_markdown": html_to_markdown(content),
        "source_service": source_service,  # twin-report-kb, real-time-intel, etc.
        "source_project": get_project_from_service(source_service),
        "timestamp": datetime.utcnow(),
        "content_hash": sha256(content),
        "archive_path": f"archives/{date}/{hash}.md"
    }
    store_to_minio(archive_record)
    index_in_postgres(archive_record)
```

**Archive Organization**:
```
archives/
├─ 2025/
│   ├─ 06/
│   │   ├─ 01/
│   │   │   ├─ reuters_article_abc123.md
│   │   │   ├─ imf_report_def456.md
│   │   │   └─ research_paper_ghi789.md
│   │   └─ metadata.json
├─ raw_html/                    # Original HTML preserved
├─ assets/                      # Images, PDFs, videos
└─ search_index/               # Full-text search capabilities
```

**Metadata Schema**:
```json
{
  "archive_id": "uuid",
  "url": "https://example.com/article",
  "title": "extracted_title",
  "content_type": "article|report|webpage|pdf",
  "source_service": "twin-report-kb",
  "source_project": "master|twin-report-kb|real-time-intel",
  "language": "en",
  "word_count": 1500,
  "extracted_entities": ["Apple", "AI", "regulation"],
  "archive_date": "2025-06-01T10:00:00Z",
  "content_hash": "sha256_hash",
  "file_paths": {
    "markdown": "archives/2025/06/01/article_abc123.md",
    "html": "raw_html/2025/06/01/article_abc123.html",
    "assets": ["assets/2025/06/01/image_123.jpg"]
  }
}
```

### 5.5 Qwen MLX Inference Engine (Shared LLM)
- **Base Model**: Qwen-3-72B-Instruct
- **Quantization**: 4-bit MLX for memory efficiency
- **Context Window**: 32K tokens with sliding window
- **Concurrent Requests**: 4 parallel inference threads
- **Memory Allocation**: 400GB reserved for model + context

**API Compatibility**:
```python
# OpenAI-compatible endpoint
POST /v1/chat/completions
{
  "model": "qwen-3-72b",
  "messages": [...],
  "temperature": 0.1,
  "max_tokens": 4000,
  "project_context": "twin-report-kb|decision-support"
}
```

---

## 6. Sub-Project Integration Points

### 6.1 Twin-Report Knowledge Base Integration
- **Shared Vector Store**: Chroma database with project namespaces
- **LLM Access**: Qwen-3-72B for local inference, API fallback
- **Event Publishing**: Research completion triggers to event router
- **Compliance**: All research activities logged for audit

### 6.2 Real-Time Intel Integration (Planned)
- **Data Ingestion**: Browser-Use crawler feeds vector database
- **Event Generation**: News alerts via NATS message bus
- **Holdings Awareness**: Cross-reference news with portfolio positions
- **Severity Scoring**: Automated impact assessment for client relevance

### 6.3 Decision Support Integration (Planned)
- **Data Sources**: Twin-Report KB + Real-Time Intel events
- **LLM Processing**: Qwen-3-72B for trade suggestions and risk analysis
- **Output Format**: Structured JSON with confidence scores
- **Human Review**: UI for PM approval/rejection tracking

### 6.4 Risk Dashboard Integration (Planned)
- **Widget Framework**: React components consuming all sub-project APIs
- **Real-Time Updates**: WebSocket connections for live data
- **Export Capabilities**: PDF reports, Excel exports, API access
- **Access Controls**: Role-based dashboards per user type

---

## 7. Implementation Roadmap (Master Project)

### 7.1 Phase 1: Foundation (Days 0-15)
**Deliverables**:
- Master Docker orchestration setup
- MinIO WORM storage with compliance features
- Qwen-3-72B MLX deployment and optimization
- Basic Browser-Use crawler (Reuters & IMF)
- Twin-Report KB integration (existing sub-project)

**Effort**: 60 hours

### 7.2 Phase 2: Intelligence Layer (Days 16-30)
**Deliverables**:
- Qwen-3-14B development server for testing
- Ingest 50K documents across all sources
- Basic Q&A CLI for knowledge base testing
- Event router implementation and testing
- Cross-project message bus (NATS)

**Effort**: 40 hours

### 7.3 Phase 3: Automation (Days 31-60)
**Deliverables**:
- Complete Airflow DAG orchestration
- Event mapper with severity scoring
- ISO-3166 country/region taxonomy
- Real-Time Intel sub-project alpha
- Holdings-aware event routing

**Effort**: 80 hours

### 7.4 Phase 4: Production Ready (Days 61-90)
**Deliverables**:
- Upgrade to Qwen-3-72B production deployment
- Decision Support agent alpha version
- Analysis sandbox with code execution
- Risk dashboard widgets implementation
- Complete security audit and compliance validation

**Effort**: 80 hours

---

## 8. Compliance & Risk Controls (Master Level)

### 8.1 Data Governance & Universal Archival
- **Complete Web Archival**: Every website, article, and document accessed by any service automatically archived as markdown
- **Robots.txt Compliance**: Respectful crawling with rate limits
- **Quality Gates**: RAGAS relevance score < 0.15 triggers quarantine
- **Content Filtering**: Regex-based promissory note detection
- **PII Protection**: Account ID hashing before LLM processing
- **Access Logging**: Complete audit trail for all data access
- **Archive Integrity**: SHA256 content hashing and duplicate detection
- **Retention Management**: Configurable archive retention policies per content type

### 8.2 Security Framework
- **Physical Security**: FileVault encryption, locked office access
- **Network Security**: Isolated Docker networks, no external access for compliance data
- **Backup Strategy**: Automated snapshots + MinIO object-lock
- **Incident Response**: Automated quarantine and alert procedures
- **Penetration Testing**: Quarterly security assessments

### 8.3 Regulatory Compliance (SEC 17a-4)
- **Immutable Records**: All decisions and reasoning chains preserved
- **Audit Trail**: Complete lineage from data source to final decision
- **Retention Policies**: Configurable per data type and regulatory requirement
- **Export Capabilities**: SEC-compliant data export formats
- **Validation Testing**: Nightly compliance verification procedures

---

## 9. Prompt Engineering & Quality Assurance

### 9.1 Centralized Prompt Library
**Repository Structure**:
```
prompts/
├─ shared/                     # Cross-project prompts
│   ├─ decision_agent_v001.md
│   ├─ analysis_agent_v002.md
│   └─ compliance_check_v001.md
├─ twin-report-kb/            # Project-specific prompts
├─ real-time-intel/
├─ decision-support/
└─ risk-dashboard/
```

**Prompt Metadata** (YAML frontmatter):
```yaml
---
model: qwen-3-72b
temperature: 0.1
max_tokens: 4000
latency_target: 3s
citation_accuracy: 0.95
project_scope: [twin-report-kb, decision-support]
compliance_reviewed: true
last_updated: 2025-06-01
---
```

### 9.2 Quality Assurance Pipeline
- **Nightly Testing**: Airflow replay of 50 gold standard Q&As
- **Performance Gates**: Citation accuracy > 95%, latency < 3s
- **Regression Detection**: Automated comparison with baseline responses
- **Metrics Storage**: Time-series performance data in MinIO
- **Alert System**: Slack notifications for quality degradation

---

## 10. Monitoring & Observability

### 10.1 Master Dashboard Metrics
- **System Health**: CPU, memory, GPU utilization across all services
- **LLM Performance**: Token generation speed, queue depth, error rates
- **Compliance Status**: Audit trail completeness, quarantine actions
- **Business Metrics**: Research velocity, decision accuracy, user engagement
- **Cost Tracking**: Local compute vs. API usage optimization

### 10.2 Cross-Project Event Tracking
- **Event Volume**: Messages per minute across all sub-projects
- **Processing Latency**: End-to-end timing for critical workflows
- **Error Rates**: Failed processing by service and error type
- **Data Quality**: Vector similarity scores, content relevance metrics
- **User Activity**: Dashboard usage, query patterns, export frequency

### 10.3 Alerting Framework
**Critical Alerts**:
- LLM inference failure or severe performance degradation
- Compliance violation or audit trail corruption
- Data ingestion failure affecting multiple sub-projects
- Security breach or unauthorized access attempt

**Warning Alerts**:
- Queue depth exceeding thresholds
- API cost approaching budget limits
- Quality metrics trending downward
- Storage approaching capacity limits

---

## 11. Cloud Migration Readiness

### 11.1 Endpoint Abstraction
All services use environment variables for external dependencies:
```bash
# Local Mac Studio deployment
VECTOR_ENDPOINT=http://chroma:8000
STORAGE_ENDPOINT=http://minio:9000
LLM_ENDPOINT=http://qwen-mlx:8080

# Cloud deployment
VECTOR_ENDPOINT=https://pinecone-api-key@api.pinecone.io
STORAGE_ENDPOINT=https://s3.amazonaws.com/bucket
LLM_ENDPOINT=https://api.openai.com/v1
```

### 11.2 Migration Strategy
1. **Data Export**: Automated backup to cloud storage
2. **Service Migration**: Docker images rebuild for cloud platforms
3. **Configuration Switch**: Environment variables update
4. **Validation Testing**: Full system verification in cloud environment
5. **Traffic Routing**: Gradual migration with rollback capability

---

## 12. Future Extensions & Blue-Sky Features

### 12.1 Advanced Analytics
- **Regime Shift Detection**: Embeddings time-series analysis for narrative pivots
- **Sentiment Analysis**: Market sentiment tracking across news sources
- **Correlation Discovery**: Automated pattern recognition in market data
- **Predictive Modeling**: ML models for trend forecasting

### 12.2 Enhanced Automation
- **Browser Agents**: Automated interaction with financial platforms
- **Document Generation**: Automated report creation with compliance approval
- **Real-Time Trading**: Direct integration with trading platforms (with human oversight)
- **Multi-Language Support**: Global news sources and analysis capabilities

---

## 13. Development Workflow & Standards

### 13.1 Master Project Setup
```bash
# Initial environment setup
git clone https://github.com/company/ai-research-platform
cd ai-research-platform
./scripts/mac-studio-setup.sh  # macOS optimization script
docker-compose -f docker-compose.master.yml up -d

# Sub-project development
cd sub-projects/twin-report-kb
docker-compose up -d  # Inherits master services
```

### 13.2 Code Standards
- **Python**: Black formatting, type hints, comprehensive docstrings
- **TypeScript**: ESLint configuration, strict typing
- **Docker**: Multi-stage builds, security scanning
- **Documentation**: Comprehensive README per sub-project
- **Testing**: 80%+ coverage requirement across all services

### 13.3 Release Management
- **Semantic Versioning**: Master project and sub-project versioning
- **Feature Flags**: Gradual rollout of new capabilities
- **Automated Testing**: CI/CD pipeline with compliance validation
- **Backup Procedures**: Automated rollback capability
- **Change Documentation**: Detailed change logs for audit purposes

---

## 14. Quick-Start Context for New Chats

> **AI Research Platform Master Project:** Comprehensive self-hosted intelligence fabric combining real-time news ingestion, deep research capabilities (Twin-Report KB sub-project), automated decision support, and compliance-ready audit trails. Deployment target: Mac Studio M3 Ultra with Qwen-3-72B MLX, Chroma vector DB, Browser-Use crawling, and SEC 17a-4 compliant storage. Architecture: Modular sub-projects with shared infrastructure, hot-swappable cloud migration, and comprehensive monitoring. Current status: Twin-Report KB specified, implementing foundation phase.

*Copy this paragraph into new sessions to load complete master project context.*

---

## 15. Sub-Project Reference Links

- **[Twin-Report Knowledge Base](link-to-twin-report-spec)**: Deep research platform with twin LLM reports, quality control, and citation verification
- **Real-Time Intel** (Specification Pending): Browser-Use news crawling, event processing, and holdings-aware routing
- **Decision Support** (Specification Pending): Automated trading suggestions with confidence scoring and risk analysis
- **Risk Dashboard** (Specification Pending): React UI with real-time widgets, export capabilities, and user management

---

*This master specification serves as the definitive architectural blueprint for the AI-Enabled Research & Decision-Support Platform, designed for consistent sub-project development and seamless scaling.*