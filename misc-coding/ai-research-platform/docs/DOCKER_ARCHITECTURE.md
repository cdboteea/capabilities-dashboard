# AI Research Platform - Docker Architecture

## Overview
Complete containerization strategy for self-hosted AI Research Platform on Mac Studio M3 Ultra. Each sub-project implements microservices with shared infrastructure for seamless integration and deployment.

## Master Infrastructure (docker-compose.master.yml)

### Core Services
```yaml
# Shared infrastructure running on dedicated ports
- PostgreSQL: 5432 (primary database)
- Chroma Vector DB: 8000 (embeddings and semantic search)
- MinIO Object Storage: 9000/9001 (WORM compliance, document storage)
- NATS Message Broker: 4222 (inter-service communication)
```

### Resource Allocation
- **Total RAM**: 32GB allocated across all services
- **CPU Cores**: 20 cores distributed with priority scheduling
- **Storage**: MinIO with object lock for compliance
- **Network**: Shared Docker network for internal communication

## Sub-Project Docker Implementation

### 1. Idea Database (Port Range: 8100-8109)
**Status: ✅ Complete**

#### Services Architecture
```
├── email_processor (8100) - FastAPI Gmail ingestion
├── ai_processor (8101) - Content categorization  
├── content_extractor (8102) - URL and attachment processing
├── database_service (8103) - PostgreSQL interface
└── web_interface (8104) - Management dashboard
```

#### Features
- Async PostgreSQL with connection pooling
- Graceful Gmail credential fallback
- Content categorization with keyword scoring
- Docker health checks and auto-restart

### 2. Twin-Report KB (Port Range: 8200-8209)
**Status: ✅ Complete (100%)**

#### Services Architecture
```
├── topic_manager (8200) - Research topic coordination
├── diff_worker (8201) - AI-powered analysis comparison
├── quality_controller (8202) - Content quality assessment
├── document_parser (8203) - Multi-format document processing
├── frontend (8204) - Complete web interface
└── author_local_reasoning (8205) - LLM integration service
```

#### Advanced Features
- **Frontend Interface**: 5-phase complete web UI
  - Document upload and batch processing
  - Real-time results viewer with analytics
  - Health monitoring with auto-refresh
  - Comprehensive settings management
- **AI Integration**: Mac Studio LLM endpoint integration
- **Multi-format Support**: PDF, Office, Web, Google Docs, Chat exports
- **Quality Scoring**: Comprehensive analysis with actionable feedback

### 3. Real-Time Intel (Port Range: 8300-8309)
**Status: 📋 Ready for Implementation**

#### Planned Services Architecture
```
├── news_crawler (8300) - Browser-Use + Playwright web scraping
├── macro_watcher (8301) - Economic indicators monitoring
├── source_manager (8302) - LLM-based source evaluation
├── event_processor (8303) - Content classification and routing
├── sentiment_analyzer (8304) - MLX local sentiment analysis
├── holdings_router (8305) - Portfolio-aware event routing
├── price_fetcher (8306) - Financial data integration
├── alert_engine (8307) - Multi-channel notification system
└── historical_analyzer (8308) - 10-year context database
```

#### Advanced Capabilities
- **Portfolio Integration**: Relevance scoring for holdings-based routing
- **Multi-language Processing**: 10+ language support with local models
- **Dynamic Source Management**: LLM-powered source discovery and evaluation
- **Historical Context**: 10-year price database for market context
- **Alert System**: Web dashboard, macOS notifications, webhooks, APIs

### 4. AI Browser Agent (Port Range: 8400-8409)
**Status: 📋 Future Implementation**

#### Planned Architecture
```
├── browser_controller (8400) - Premium AI automation
├── task_manager (8401) - Multi-step workflow coordination
├── vision_processor (8402) - Screenshot analysis with vision models
├── form_filler (8403) - Intelligent form completion
└── session_manager (8404) - Browser state management
```

## Docker Implementation Features

### Security & Compliance
- **Non-root Containers**: All services run as dedicated users
- **Network Segmentation**: Isolated service networks with controlled access
- **WORM Storage**: MinIO object lock for compliance requirements
- **Secret Management**: Environment-based credential handling

### Operational Excellence
- **Health Checks**: Comprehensive monitoring for all services
- **Auto-restart**: Failure recovery with exponential backoff
- **Resource Limits**: Memory and CPU constraints per service
- **Logging**: Centralized log aggregation with rotation
- **Monitoring**: Built-in metrics collection and dashboards

### Development & Production
- **Multi-stage Builds**: Optimized container images
- **Environment Overrides**: Development vs production configurations
- **Hot Reload**: Development mode with code mounting
- **Scale Configuration**: Horizontal scaling capabilities

## Integration Points

### Cross-Service Communication
```
Twin-Report KB ←→ Real-Time Intel
├── Breaking news → Research topic suggestions
└── Analysis reports → Intelligence context

Real-Time Intel ←→ Decision Support (Future)
├── High-severity alerts → Trade analysis triggers
└── Portfolio events → Risk assessment automation

All Services ←→ MinIO Archive
├── Document storage with versioning
└── Compliance audit trails
```

### Service Discovery
- **Internal DNS**: Service-to-service communication via Docker networks
- **Health Endpoints**: `/health` endpoints for service monitoring
- **API Gateway**: Centralized routing and authentication (Future)

## Deployment Strategy

### Local Development
```bash
# Start master infrastructure
docker-compose -f docker-compose.master.yml up -d

# Start individual sub-projects
cd sub-projects/idea-database && docker-compose up -d
cd sub-projects/twin-report-kb && docker-compose up -d
cd sub-projects/real-time-intel && docker-compose up -d  # (When ready)
```

### Production Deployment
- **Orchestration**: Docker Swarm or standalone compose
- **Backup Strategy**: PostgreSQL dumps + MinIO replication
- **Update Strategy**: Rolling updates with health checks
- **Monitoring**: Prometheus + Grafana integration ready

## Resource Requirements

### Mac Studio M3 Ultra Capacity
- **Total RAM**: 128GB available → 32GB Docker allocation (25%)
- **CPU Cores**: 24 cores → 20 cores Docker allocation (83%)
- **Storage**: 8TB SSD → 2TB Docker allocation (25%)
- **Network**: 10Gb Ethernet for external integrations

### Per-Service Allocation
```yaml
# High-priority services (Real-Time Intel)
news_crawler: 4GB RAM, 2 cores
sentiment_analyzer: 6GB RAM, 3 cores (MLX models)
event_processor: 3GB RAM, 2 cores

# Medium-priority services (Twin-Report KB)
diff_worker: 4GB RAM, 2 cores (LLM integration)
document_parser: 2GB RAM, 1 core
frontend: 1GB RAM, 1 core

# Low-priority services (Infrastructure)
PostgreSQL: 8GB RAM, 4 cores
Chroma: 2GB RAM, 2 cores
MinIO: 2GB RAM, 1 core
```

## Future Enhancements

### Scalability
- **Kubernetes Migration**: For multi-node deployment
- **Load Balancing**: HAProxy or Traefik integration
- **Cache Layer**: Redis for session and temporary data
- **CDN Integration**: For static asset delivery

### Monitoring & Observability
- **Distributed Tracing**: Jaeger integration
- **Metrics Collection**: Prometheus + custom metrics
- **Log Aggregation**: ELK stack or Grafana Loki
- **Alerting**: PagerDuty integration for critical failures

---

**Status**: Master infrastructure ✅ Complete | Idea Database ✅ Complete | Twin-Report KB ✅ Complete | Real-Time Intel �� Ready for Sprint 0 