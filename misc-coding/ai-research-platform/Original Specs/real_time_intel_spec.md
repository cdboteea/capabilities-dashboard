# Real-Time Intel Module – **Technical Specification**

> **Version:** 2025‑06‑01 v1.0   > **Maintainer:** Matias Mirvois   > **Status:** *Active Sub-Project*   
> **Parent Project:** AI-Enabled Research & Decision-Support Platform

---

## 0. Executive Snapshot

A comprehensive real-time intelligence gathering system that dynamically manages global information sources, processes events through portfolio-aware routing, and delivers customizable alerts with historical context and sentiment analysis. The module features dynamic source discovery and evaluation, multi-language capabilities, comprehensive price data integration, and intelligent connections to the Twin-Report KB and Decision Support modules.

```
Dynamic Sources → Multi-Language Crawler → Event Processor → Holdings Router → Alert Engine
      ↓                    ↓                    ↓              ↓             ↓
Source Evaluator      Web Archiver       Sentiment Analysis  Impact Tracker  Dashboard
      ↓                    ↓                    ↓              ↓             ↓
Quality Database     Vector Storage      Historical Context  Price Database  Notifications
```

*Inherits master platform infrastructure: Mac Studio M3 Ultra, Qwen-3-72B MLX, Chroma vector DB, MinIO WORM storage.*

---

## 1. Directory & File Map (Sub-Project Root)

```
real-time-intel/
├─ docker/
│   ├─ news_crawler/              # Multi-source web crawling service
│   ├─ macro_watcher/             # Economic calendar monitoring
│   ├─ source_manager/            # Dynamic source discovery & evaluation
│   ├─ event_processor/           # Content analysis & sentiment scoring
│   ├─ holdings_router/           # Portfolio-aware event routing
│   ├─ alert_engine/              # Notification generation & delivery
│   ├─ price_fetcher/             # Historical price data management
│   └─ sentiment_analyzer/        # Local sentiment analysis service
├─ services/
│   ├─ source_evaluation/         # LLM-based source quality assessment
│   ├─ historical_analysis/       # Impact tracking and pattern recognition
│   ├─ multi_language/            # Translation and local source processing
│   └─ portfolio_integration/     # Holdings data processing utilities
├─ data/
│   ├─ sources/                   # Dynamic source configurations
│   ├─ price_history/             # 10-year price database
│   ├─ sentiment_models/          # Local sentiment analysis models
│   └─ evaluation_criteria/       # Source rating methodology
├─ docs/
│   ├─ SOURCE_EVALUATION.md       # Comprehensive source rating process
│   ├─ INTEGRATION_GUIDE.md       # Connection to other modules
│   └─ ALERT_CONFIGURATION.md     # Customizable alert system guide
├─ scripts/
│   ├─ source_discovery.py        # Manual/scheduled source research
│   ├─ price_data_sync.py         # Historical data synchronization
│   └─ evaluation_scheduler.py    # Source quality monitoring
└─ real_time_intel/               # Python package root
    ├─ __init__.py
    └─ config.py
```

---

## 2. Enhanced Data Model (PostgreSQL + Shared Infrastructure)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| **news\_sources** | Dynamic source management | `id`, `name`, `url`, `source_type`, `language`, `evaluation_score`, `status`, `last_evaluated` |
| **source\_evaluations** | LLM-based source quality assessments | `id`, `source_id FK`, `accuracy_score`, `relevance_score`, `paywall_status`, `update_frequency`, `evaluation_date` |
| **source\_retirement** | Retired source documentation | `id`, `source_id FK`, `retirement_reason`, `retirement_date`, `archive_status`, `article_count` |
| **macro\_data\_sources** | Economic calendar and data feeds | `id`, `source_name`, `data_type`, `geographic_scope`, `update_frequency`, `api_endpoint`, `evaluation_score` |
| **raw\_events** | All ingested content before processing | `id`, `source_id FK`, `content`, `url`, `fetch_timestamp`, `language`, `content_hash` |
| **processed\_events** | Analyzed and classified events | `id`, `raw_event_id FK`, `event_type`, `sentiment_scores`, `entities`, `geographic_tags`, `sector_tags` |
| **holdings\_data** | Portfolio positions from CSV | `id`, `ticker`, `cusip`, `isin`, `position_size`, `sector`, `geographic_exposure`, `last_updated` |
| **event\_holdings\_relevance** | Portfolio-aware event routing | `id`, `event_id FK`, `holding_id FK`, `relevance_score`, `impact_assessment`, `routing_reason` |
| **price\_history** | 10-year historical price database | `id`, `ticker`, `date`, `open`, `close`, `high`, `low`, `volume`, `dividend`, `adjusted_close` |
| **historical\_impact** | Event impact tracking and analysis | `id`, `event_id FK`, `ticker`, `price_impact_1h`, `price_impact_1d`, `price_impact_1w`, `volatility_change` |
| **sentiment\_scores** | Multi-level sentiment analysis | `id`, `event_id FK`, `company_sentiment`, `sector_sentiment`, `market_sentiment`, `confidence_score` |
| **alerts** | Generated notifications and delivery | `id`, `event_id FK`, `alert_type`, `severity`, `delivery_methods`, `acknowledged`, `created_at` |
| **alert\_delivery\_log** | Alert delivery tracking | `id`, `alert_id FK`, `delivery_method`, `delivery_status`, `delivery_timestamp`, `recipient` |

---

## 3. Dynamic Source Management System

### 3.1 Source Discovery & Evaluation Pipeline

**Manual Source Research Process**:
```python
# CLI command for source discovery
researchdb sources discover --region="North America" --language="en" --sector="financial"
researchdb sources evaluate --source-id=123 --full-analysis
researchdb sources schedule-review --frequency="monthly"
```

**LLM-Based Source Evaluation**:
- **Accuracy Assessment**: Cross-reference articles with known facts and other sources
- **Relevance Scoring**: Analyze content alignment with financial/macro topics
- **Paywall Detection**: Automated testing for access limitations
- **Update Frequency**: Monitor posting patterns and timeliness
- **Geographic Coverage**: Assess regional focus and scope
- **API Availability**: Check for structured data access options
- **Language Capabilities**: Leverage Qwen-3-72B multi-language support

### 3.2 Source Quality Database Schema

**Evaluation Criteria** (Documented in SOURCE_EVALUATION.md):
```json
{
  "source_evaluation": {
    "accuracy_score": 0.85,        # 0-1 scale based on fact-checking
    "relevance_score": 0.92,       # 0-1 scale for financial content
    "timeliness_score": 0.78,      # Speed of breaking news coverage
    "paywall_restrictions": {
      "free_articles_per_month": 10,
      "full_access": false,
      "api_available": false
    },
    "geographic_coverage": ["US", "EU", "ASIA"],
    "languages": ["en", "es", "de"],
    "update_frequency": "hourly",
    "source_type": "news|macro|research|regulatory"
  }
}
```

### 3.3 Source Retirement Process

**Retirement Triggers**:
- Quality scores drop below threshold (accuracy < 0.6)
- Paywall restrictions increase significantly
- Update frequency decreases substantially
- Manual decision based on editorial changes

**Retention Protocol**:
- Archive all historical articles in MinIO WORM storage
- Document retirement reason with LLM analysis
- Maintain source metadata for historical reference
- Preserve article-to-event mappings for continuity

---

## 4. Multi-Language Content Processing

### 4.1 Language Detection & Translation
- **Automatic Language Detection**: Qwen-3-72B native multi-language capabilities
- **Supported Languages**: English, Spanish, French, German, Italian, Portuguese, Japanese, Chinese, Korean, Russian
- **Translation Pipeline**: Local translation for non-English sources when needed
- **Cultural Context**: Preserve regional financial terminology and context

### 4.2 Local Source Integration
- **Regional Financial News**: Integration with local financial newspapers and websites
- **Central Bank Communications**: Native language processing of ECB, BoJ, PBoC communications
- **Regulatory Announcements**: Local language regulatory body monitoring
- **Economic Data**: Native language macro data source integration

---

## 5. Event Processing & Sentiment Analysis

### 5.1 Event Classification System

**Event Categories**:
- **Earnings**: Announcements, guidance, surprises
- **Regulatory**: New rules, investigations, approvals
- **Corporate Actions**: M&A, spin-offs, buybacks, splits
- **Management**: Executive changes, board updates
- **Product**: Launches, recalls, approvals, partnerships
- **Economic**: GDP, inflation, employment, central bank decisions
- **Geopolitical**: Trade wars, sanctions, elections, conflicts
- **Market Structure**: Exchange changes, new instruments, rule changes

### 5.2 Multi-Level Sentiment Analysis

**Local Sentiment Models** (MLX-optimized):
- **Company-Specific**: Direct impact on individual stocks
- **Sector-Specific**: Industry-wide implications
- **Market-General**: Broad market sentiment shifts

**Integration with Financial Lexicons**:
- **Loughran-McDonald Financial Dictionary**: Financial sentiment classification
- **Harvard General Inquirer**: Psychological and sociological sentiment
- **Custom Financial Terms**: Domain-specific sentiment indicators
- **Multi-Language Sentiment**: Translated sentiment preservation

**Sentiment Scoring Output**:
```json
{
  "sentiment_analysis": {
    "company_sentiment": {"AAPL": 0.75, "confidence": 0.89},
    "sector_sentiment": {"technology": 0.68, "confidence": 0.82},
    "market_sentiment": {"overall": 0.45, "confidence": 0.91},
    "sentiment_drivers": ["product launch", "revenue beat", "guidance raise"],
    "sentiment_timeline": "short_term_positive|long_term_neutral"
  }
}
```

---

## 6. Historical Context & Impact Tracking

### 6.1 Historical Analysis Capabilities

**Event Similarity Matching**:
- **Pattern Recognition**: Identify similar events in historical data
- **Context Generation**: "Similar earnings misses in tech sector historically led to 3-5% drops"
- **Company-Specific History**: "Last 3 times AAPL had supply chain issues, stock recovered within 2 weeks"
- **Market Regime Context**: "During high-inflation periods, Fed rate hints typically cause 2x normal volatility"
- **Sector Correlation**: "Banking sector typically drops 1.2x when tech falls on regulatory news"

**Signal/Noise Evaluation**:
- **Relevance Scoring**: Rank historical contexts by predictive value
- **Statistical Significance**: Filter out coincidental patterns
- **Confidence Intervals**: Provide uncertainty bounds for historical predictions
- **Event Type Specificity**: Different analysis frameworks for different event categories

### 6.2 Price Data Integration

**10-Year Historical Database**:
- **Data Sources**: Yahoo Finance, Alpha Vantage, other free APIs
- **Data Points**: Open, Close, High, Low, Volume, Dividends, Adjusted Close
- **Update Strategy**: Full history for new tickers, incremental updates for existing
- **Total Return Calculations**: Dividend-adjusted performance tracking

**Impact Tracking Framework**:
```python
# Example impact analysis
{
  "price_impact_analysis": {
    "ticker": "AAPL",
    "event_type": "earnings_miss",
    "impact_windows": {
      "1_hour": {"change": -2.3, "volatility": 1.8},
      "1_day": {"change": -3.7, "volatility": 2.1},
      "1_week": {"change": -1.2, "volatility": 1.4}
    },
    "historical_comparisons": [
      {"date": "2023-01-01", "similar_event": true, "impact": -2.8},
      {"date": "2022-07-15", "similar_event": true, "impact": -4.1}
    ],
    "sector_spillover": {"XLK": -1.8, "QQQ": -1.5},
    "recovery_pattern": "typically_recovers_within_5_days"
  }
}
```

---

## 7. Portfolio Integration & Holdings Router

### 7.1 Holdings Data Processing

**CSV Integration**:
- **Automatic CSV Parsing**: Compatible with existing Python dashboard code
- **Data Validation**: Ticker symbol verification and normalization
- **Position Tracking**: Size, sector, geographic exposure mapping
- **Update Frequency**: Configurable refresh schedule

**Relevance Scoring Algorithm**:
```python
def calculate_relevance_score(event, holding):
    scores = {
        'direct_mention': check_company_mention(event.content, holding.ticker),
        'sector_impact': assess_sector_relevance(event.sector_tags, holding.sector),
        'geographic_overlap': geographic_relevance(event.geo_tags, holding.geo_exposure),
        'supply_chain': analyze_supply_chain_connections(event.entities, holding.ticker),
        'regulatory_impact': regulatory_scope_analysis(event.type, holding.sector)
    }
    return weighted_average(scores, relevance_weights)
```

### 7.2 Holdings-Aware Event Routing

**Routing Decision Matrix**:
- **High Relevance** (>0.8): Immediate alert + auto-generate trade analysis
- **Medium Relevance** (0.5-0.8): Standard alert + historical context
- **Low Relevance** (0.2-0.5): Log for review + batch summary
- **No Relevance** (<0.2): Archive only, no alert

**Position Size Considerations**:
- **Large Positions** (>5% portfolio): Lower alert threshold
- **Concentrated Holdings**: Cross-reference with related positions
- **Small Positions** (<1% portfolio): Higher alert threshold to reduce noise

---

## 8. Integration with Other Modules

### 8.1 Twin-Report KB Integration

**Breaking News → Research Suggestions**:
```python
# Automated research topic suggestions
def suggest_research_topics(breaking_news_event):
    suggestions = {
        "immediate_research": [
            f"Impact analysis: {event.company} {event.event_type}",
            f"Sector implications: {event.sector} {event.topic}",
            f"Historical precedents: {event.similar_events}"
        ],
        "deep_dive_topics": [
            f"Regulatory landscape: {event.regulatory_context}",
            f"Competitive analysis: {event.affected_companies}",
            f"Market dynamics: {event.broader_implications}"
        ],
        "priority_score": calculate_research_priority(event),
        "human_decision_required": True
    }
    return suggestions
```

**Knowledge Base Context Feeding**:
- **Real-time Events → Context Enhancement**: Current events provide context for ongoing research
- **Trending Topics → Research Priorities**: Event frequency influences research topic prioritization  
- **Source Quality → Research Reliability**: High-quality sources boost research confidence scores

### 8.2 Decision Support Integration

**High-Severity Alert → Trade Analysis**:
```python
# Auto-triggered trade suggestion pipeline
@high_severity_alert_handler
def generate_trade_suggestions(alert):
    analysis_request = {
        "event_context": alert.event_data,
        "affected_holdings": alert.portfolio_impact,
        "historical_patterns": get_historical_context(alert.event_type),
        "sentiment_analysis": alert.sentiment_scores,
        "suggested_actions": ["reduce", "hedge", "monitor", "opportunistic_add"],
        "confidence_threshold": 0.7,
        "human_review_required": True
    }
    return route_to_decision_support(analysis_request)
```

**Integration Touch Points**:
- **Event Severity** → **Trade Urgency**: High-impact events trigger immediate analysis
- **Portfolio Exposure** → **Risk Assessment**: Position-specific risk calculations
- **Historical Context** → **Strategy Suggestions**: Past patterns inform trade recommendations

---

## 9. Customizable Alert System

### 9.1 Local Machine Alert Options

**Web Dashboard Alerts**:
- **Real-time WebSocket Updates**: Instant alert display with audio/visual notifications
- **Alert Acknowledgment**: Track which alerts have been reviewed
- **Alert Dismissal**: Remove non-actionable alerts from active queue
- **Alert History**: Searchable archive of all past alerts
- **Customizable Severity Levels**: User-defined thresholds and categories

**Desktop Notifications** (macOS):
- **Native Notification Center**: System-level alerts with action buttons
- **Severity-Based Styling**: Different alert styles for different priorities
- **Do Not Disturb Integration**: Respect system quiet hours
- **Quick Actions**: "View Details", "Acknowledge", "Generate Research"

**Log File System**:
- **Structured JSON Logs**: Machine-readable alert archive
- **Rotation Policy**: Automatic log file management
- **Integration Ready**: Standard format for external system consumption
- **Audit Trail**: Complete alert generation and delivery history

### 9.2 Cloud-Ready Alert Options

**Webhook Endpoints**:
- **Configurable URLs**: POST alerts to external systems
- **Custom Payloads**: Flexible alert data formatting
- **Retry Logic**: Ensure delivery reliability
- **Authentication**: Secure webhook delivery

**Message Queue Integration**:
- **Pub/Sub System**: Redis/NATS message publishing
- **Topic-Based Routing**: Route alerts by type, severity, or portfolio relevance
- **Multiple Subscribers**: Support for multiple alert consumers
- **Message Persistence**: Ensure no alerts are lost

**RESTful API Endpoints**:
- **Alert Retrieval**: GET /alerts with filtering and pagination
- **Real-time Subscriptions**: WebSocket connections for live updates
- **Alert Management**: Update alert status via API
- **Integration Documentation**: OpenAPI specification for external systems

### 9.3 Alert Configuration Management

**Customizable Settings**:
```yaml
alert_configuration:
  delivery_methods:
    web_dashboard: true
    desktop_notifications: true
    log_files: true
    webhooks: false
    message_queue: false
    api_endpoints: true
  
  severity_thresholds:
    high: 0.8      # Holdings relevance score
    medium: 0.5
    low: 0.2
  
  frequency_limits:
    max_alerts_per_hour: 50
    similar_event_bundling: true
    quiet_hours: "22:00-06:00"
  
  content_filters:
    minimum_confidence: 0.7
    exclude_sectors: []
    include_only_languages: ["en", "es"]
```

---

## 10. Service Architecture & Implementation

### 10.1 Core Services

| Service | Image Tag | Purpose | Technology Stack | Resource Allocation |
|---------|-----------|---------|------------------|-------------------|
| **news-crawler** | `news-crawler:latest` | Multi-source web crawling | Browser-Use + Playwright | 4GB RAM, 2 cores |
| **macro-watcher** | `macro-watcher:latest` | Economic calendar monitoring | Python + requests | 2GB RAM, 1 core |
| **source-manager** | `source-mgr:latest` | Dynamic source discovery | Qwen-3-72B MLX + Python | 2GB RAM, 1 core |
| **event-processor** | `event-processor:latest` | Content analysis & classification | Qwen-3-72B MLX + Python | 4GB RAM, 2 cores |
| **sentiment-analyzer** | `sentiment-analyzer:latest` | Multi-level sentiment analysis | Local models + MLX | 8GB RAM, 4 cores |
| **holdings-router** | `holdings-router:latest` | Portfolio-aware event routing | Python + ML models | 2GB RAM, 1 core |
| **price-fetcher** | `price-fetcher:latest` | Historical price data sync | Python + APIs | 2GB RAM, 1 core |
| **alert-engine** | `alert-engine:latest` | Notification generation & delivery | FastAPI + WebSocket | 2GB RAM, 1 core |
| **historical-analyzer** | `historical-analyzer:latest` | Impact tracking & pattern recognition | Python + statistical analysis | 4GB RAM, 2 cores |

### 10.2 Enhanced Container Orchestration

```yaml
# real-time-intel docker-compose.yml excerpt
news-crawler:
  build: ./docker/news_crawler
  depends_on: [db, redis, chroma, web-archiver]
  environment:
    - CRAWLER_SOURCES_CONFIG=/app/data/sources/active_sources.json
    - MULTI_LANGUAGE_ENABLED=true
    - RATE_LIMIT_DELAY=2
    - ARCHIVE_ALL_CONTENT=true
  volumes:
    - ./data/sources:/app/data/sources
    - shared_web_archive:/app/archive

sentiment-analyzer:
  build: ./docker/sentiment_analyzer
  depends_on: [mlx-inference-engine]
  environment:
    - SENTIMENT_MODELS_PATH=/app/data/sentiment_models
    - MLX_ENABLED=true
    - FINANCIAL_LEXICON_PATH=/app/data/lexicons
  volumes:
    - ./data/sentiment_models:/app/data/sentiment_models
    - ./data/lexicons:/app/data/lexicons
    - shared_models:/app/shared_models

holdings-router:
  build: ./docker/holdings_router
  depends_on: [db, event-processor]
  environment:
    - HOLDINGS_CSV_PATH=/app/data/holdings.csv
    - RELEVANCE_THRESHOLD_HIGH=0.8
    - RELEVANCE_THRESHOLD_MEDIUM=0.5
    - AUTO_TRADE_ANALYSIS_TRIGGER=true
  volumes:
    - ./data/holdings:/app/data
```

---

## 11. Implementation Roadmap

### 11.1 Sprint 0: Foundation (Days 0-15)
**Deliverables**:
- Enhanced schema migration with real-time intel tables
- Basic news crawler with Browser-Use integration
- Source management database and initial source seeding
- Web archiver integration for all crawled content
- Basic alert system with web dashboard

**Effort**: 60 hours

### 11.2 Sprint 1: Intelligence Layer (Days 16-30)
**Deliverables**:
- Multi-language content processing capabilities
- Sentiment analysis service with local MLX models
- Event classification and processing pipeline
- Holdings data integration and relevance scoring
- Basic historical impact tracking

**Effort**: 50 hours

### 11.3 Sprint 2: Advanced Features (Days 31-45)
**Deliverables**:
- Dynamic source discovery and evaluation system
- 10-year price history database and synchronization
- Advanced historical context and pattern recognition
- Twin-Report KB integration with research suggestions
- Customizable alert delivery system

**Effort**: 45 hours

### 11.4 Sprint 3: Production Ready (Days 46-60)
**Deliverables**:
- Decision Support integration with auto-trade analysis
- Complete alert configuration and management system
- Source quality monitoring and retirement process
- Performance optimization and monitoring setup
- Comprehensive documentation and deployment guides

**Effort**: 40 hours

---

## 12. Monitoring & Quality Assurance

### 12.1 System Health Monitoring

**Key Metrics**:
- **Source Availability**: Real-time monitoring of all active sources
- **Content Processing Speed**: Events per minute through the pipeline
- **Alert Generation Rate**: Alerts per hour by severity level
- **Sentiment Analysis Accuracy**: Confidence score distributions
- **Holdings Relevance Precision**: Manual validation of routing decisions

**Performance Dashboards**:
- **Source Performance**: Response times, success rates, content quality trends
- **Event Processing**: Pipeline latency, queue depths, error rates
- **Alert Effectiveness**: Alert-to-action ratios, false positive rates
- **Integration Health**: Twin-Report KB and Decision Support connectivity

### 12.2 Quality Control Framework

**Source Quality Validation**:
- **Weekly Evaluation Runs**: Automated LLM-based source assessment
- **Content Verification**: Cross-referencing with authoritative sources
- **Timeliness Tracking**: Compare event timestamps with other sources
- **Accuracy Scoring**: Track prediction success rates over time

**Alert Quality Metrics**:
- **Relevance Accuracy**: Manual review of high-severity alerts
- **False Positive Tracking**: User feedback on non-actionable alerts
- **Response Time Analysis**: Alert-to-decision time tracking
- **Portfolio Impact Correlation**: Alert severity vs. actual price movements

---

## 13. Security & Compliance

### 13.1 Data Protection
- **Source Credential Management**: Secure storage of API keys and authentication
- **Content Archival**: WORM storage compliance for all ingested content
- **PII Handling**: Portfolio data anonymization for LLM processing
- **Access Controls**: Role-based permissions for alert management

### 13.2 Operational Security
- **Rate Limiting**: Respectful crawling to avoid source blocking
- **IP Rotation**: Multiple egress points for high-volume sources
- **Error Handling**: Graceful degradation during source outages
- **Audit Logging**: Complete trail of all system decisions and actions

---

## 14. Quick-Start Context for New Chats

> **Real-Time Intel Module:** Comprehensive intelligence gathering system with dynamic source management, multi-language processing, portfolio-aware event routing, and customizable alerts. Features: LLM-based source evaluation, 10-year price history integration, multi-level sentiment analysis, historical impact tracking, and seamless integration with Twin-Report KB and Decision Support modules. Tech stack: Browser-Use crawling, Qwen-3-72B MLX processing, local sentiment models, and flexible alert delivery (web dashboard, desktop notifications, webhooks, APIs). Deployment: Mac Studio M3 Ultra with cloud migration readiness.

*Copy this paragraph into new sessions to load complete Real-Time Intel context.*

---

*This specification serves as the definitive technical blueprint for the Real-Time Intel module, designed for seamless integration with the AI-Enabled Research & Decision-Support Platform master project.*