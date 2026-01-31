# Twin‑Report Knowledge‑Base – **Master Technical Spec & Memory**

> **Version:** 2025‑06‑01 v2.0   > **Maintainer:** Matias Mirvois   > **Status:** *Active*

## 18. On-Premises Local LLM Infrastructure (Mac Studio Optimized)

### 18.1 Mac Studio M3 Ultra Capabilities
The Mac Studio M3 Ultra with up to 512GB unified memory can run massive LLMs with over 600 billion parameters entirely in memory, delivering superior performance compared to multi-GPU NVIDIA setups for local AI workloads. Key advantages:

- **Unified Memory Architecture:** Up to 512GB shared between CPU and GPU, allowing high-precision models that would require 16+ RTX 5090s on PC
- **Apple MLX Framework:** Dynamic memory management and optimized inference, significantly outperforming traditional CUDA setups for local LLM deployment
- **Power Efficiency:** Under 200 watts consumption versus thousands of watts for comparable multi-GPU systems
- **Cost Effectiveness:** Single $10K system versus $30K+ multi-GPU alternatives

### 18.2 Recommended Local Model Stack

**Reasoning Models (ChatGPT o1 Alternatives):**
- **DeepSeek R1**: 671B parameter reasoning model running at 20+ tokens/sec with 4-bit quantization
- **QwQ-32B**: Meta's 32B reasoning model matching larger models in performance
- **OpenR1**: Open source implementation of o1-style reasoning

**General Models (GPT-4 Class Alternatives):**
- **Llama 3.3 70B**: Meta's latest with improved efficiency and 8-language support
- **Gemma 2 27B**: Google's high-performance model optimized for local deployment
- **Mixtral 8x22B**: Mixture-of-experts architecture for specialized tasks

**Specialized Models:**
- **Code Models**: CodeLlama, DeepSeek Coder, Phind CodeLlama
- **Research Models**: Domain-specific fine-tuned variants
- **Embedding Models**: Local sentence transformers for vector search

### 18.3 MLX Inference Engine Architecture

```yaml
# Enhanced MLX service configuration
mlx_inference_engine:
  build: ./docker/mlx_inference_engine
  depends_on: [redis, model_manager]
  environment:
    - MLX_MEMORY_LIMIT=400GB          # Reserve memory for models
    - MLX_CONCURRENT_REQUESTS=4       # Parallel inference threads
    - MODEL_CACHE_SIZE=100GB          # Local model cache
  volumes:
    - ./models:/app/models
    - mlx_cache:/app/cache
  deploy:
    resources:
      reservations:
        devices:
          - driver: apple-silicon
            count: all

model_manager:
  build: ./docker/model_manager
  environment:
    - HUGGINGFACE_CACHE_DIR=/app/models
    - AUTO_QUANTIZE=true              # Automatic 4-bit quantization
    - MODEL_ROTATION=true             # Swap models based on usage
  volumes:
    - ./models:/app/models
    - huggingface_cache:/app/cache
```

### 18.4 Local Model Management Features

**Automated Model Deployment:**
- **Model Discovery**: Integration with Hugging Face, Ollama, LM Studio repositories
- **Intelligent Quantization**: Automatic 4-bit/8-bit conversion for memory optimization
- **A/B Model Testing**: Compare local vs. API model performance
- **Model Rotation**: Smart caching system to maximize available memory

**Performance Optimization:**
- **Context Length Management**: Optimize for Mac Studio's massive memory for very long contexts
- **Batch Processing**: Queue multiple research requests for efficient processing
- **Memory Monitoring**: Real-time memory usage and model swap decisions
- **Temperature Scheduling**: Dynamic parameter adjustment based on task complexity

### 18.5 Integration with Existing Workflows

**Research Pipeline Integration:**
```python
# Enhanced topic creation with local model option
researchdb new-topic "AI Ethics" --method=local --model=deepseek-r1
researchdb new-topic "Climate Change" --method=hybrid --local-model=llama-3.3 --api-model=gpt-4o

# Model performance comparison
researchdb compare-models --topic="Machine Learning" --models=local:qwq-32b,api:gpt-4o,api:gemini-2.5-pro
```

**Cost-Performance Optimization:**
- **Intelligent Routing**: Route simple tasks to local models, complex reasoning to APIs
- **Budget Management**: Track API spend vs. local compute costs
- **Quality Benchmarking**: Automated comparison of local vs. API model outputs
- **Escalation Logic**: Fallback to API models when local models underperform

### 18.6 Local Model Tools Integration

**LM Studio Integration:**
- Direct integration with LM Studio for model management and GUI-based model testing
- GGUF model format support for optimized inference
- OpenAI-compatible API endpoints for seamless integration

**Ollama Integration:**
- Command-line model management with simple deployment commands
- Automatic model updates and version management
- RESTful API for programmatic model access

**Jan.ai Integration:**
- Open-source ChatGPT alternative with 100% offline operation
- Local document processing capabilities
- Team collaboration features for research workflows

### 18.7 Privacy and Security Advantages

**Data Sovereignty:**
- **Zero External Data Transfer**: All research content remains on Mac Studio
- **GDPR/HIPAA Compliance**: Meet strictest data protection requirements
- **Intellectual Property Protection**: Prevent data leakage to external LLM providers
- **Audit Trail**: Complete logging of all model interactions

**Security Features:**
- **Network Isolation**: Optional air-gapped operation for sensitive research
- **Encrypted Storage**: All models and research data encrypted at rest
- **Access Control**: Role-based permissions for model access
- **Version Control**: Immutable audit logs for model predictions

### 18.8 Fine-tuning and Customization

**Domain-Specific Adaptation:**
- MLX-native fine-tuning capabilities for custom research domains
- **InstructLab Integration**: Easy fine-tuning workflow for specialized knowledge
- **LoRA Adapters**: Memory-efficient model customization
- **Synthetic Data Generation**: Create training data for niche research areas

**Research Optimization:**
- **Citation Style Learning**: Train models on specific academic citation formats
- **Domain Vocabulary**: Fine-tune for specialized terminology
- **Quality Calibration**: Adjust model confidence based on research domain
- **Bias Reduction**: Custom training to reduce model biases in research output

---

## 0. Executive Snapshot

A self‑hosted research platform that stores **twin anchor reports**—one authored by **ChatGPT o1 Pro Deep Research** and one by **Gemini 2.0 Ultra Deep Research**—for every topic. The system supports both **API-driven automation** and **human-in-the-loop workflows** via chat interface exports. It detects gaps, overlaps, contradictions, and new developments, then triggers automated tasks (drafts, deltas, merges, quality control) so the knowledge base stays evergreen with verified integrity.

```
Sources → Ingestion → Postgres + pgvector / Chroma
    ↓                    ↙                ↘
Human Chat UI Export   Twin‑Report Workers    Gap / News Agents
    ↓                          ↓                     ↓
Google Docs/PDF       Diff & Merge Workers    QC Verification
    ↓                          ↓                     ↓
Document Parser  →    Knowledge Base    ←   Citation Checker
```

*All components run in Docker on the Mac Studio M3 Ultra but can be lifted to cloud with minimal env‑var edits.*

---

## 1. Directory & File Map (Repo root)

```
├─ docker/
│   ├─ author_chatgpt/         # Dockerfile + entrypoint (API mode)
│   ├─ author_gemini/          # Dockerfile + entrypoint (API mode)
│   ├─ author_local_reasoning/ # DeepSeek R1, QwQ-32B reasoning models
│   ├─ author_local_general/   # Llama 3.3, Gemma 2, Mistral models
│   ├─ mlx_inference_engine/   # Apple MLX model serving
│   ├─ model_manager/          # Local model deployment & management
│   ├─ document_parser/        # Google Docs + PDF ingestion
│   ├─ diff_worker/
│   ├─ gap_finder/
│   ├─ delta_writer/
│   ├─ quality_controller/     # Citation & fact verification
│   ├─ topic_manager/          # Sub-topic generation & management
│   └─ frontend/
├─ migrations/                 # Alembic + raw SQL
├─ services/                   # Re‑usable libs & utils
│   ├─ document_ingestion/     # Google Docs API, PDF parsing
│   ├─ quality_control/        # Random QC, citation verification
│   ├─ local_models/           # MLX model management, quantization
│   └─ prompt_management/      # Versioned prompt templates
├─ models/                     # Local LLM storage & cache
│   ├─ reasoning/              # DeepSeek R1, QwQ-32B, o1-style models
│   ├─ general/                # Llama 3.3, Gemma 2, Mistral variants
│   ├─ specialized/            # Domain-specific fine-tuned models
│   └─ embeddings/             # Local embedding models
├─ scripts/
│   ├─ cli.py                  # Typer CLI – "researchdb"
│   ├─ model_setup.py          # Local model installation & optimization
│   └─ browser_automation/     # Future: automated chat UI interaction
├─ twin_report_kb/             # Python package root
│   ├─ __init__.py
│   └─ config.py
├─ docs/
│   ├─ TECH_SPEC.md            # deep detail (this file mirrored)
│   ├─ PROMPTS.md              # LLM prompts (JSON‑locked + alternatives)
│   ├─ WORKFLOWS.md            # Human workflow documentation
│   └─ LOCAL_MODELS.md         # On-premises model setup & optimization
├─ pyproject.toml              # Poetry
└─ docker‑compose.yml
```

---

## 2. Enhanced Data Model (PostgreSQL + pgvector)

| Table                     | Purpose                                  | Key Fields                                                                                                                           |
| ------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **topics**                | hierarchical research topics            | `id UUID PK`, `title`, `parent_topic_id FK`, `twin_set_id UUID`, `status ENUM(pending/covered/stale)`, `generation_method ENUM`     |
| **articles**              | each anchor or derived article           | `id`, `topic_id FK`, `model_origin ENUM`, `version INT`, `body_md`, `embedding VECTOR`, `source_type ENUM(api/chat_export)`         |
| **article\_versions**     | immutable copy per version               | `id SERIAL PK`, `article_id`, `version`, `body_md`, `source_document_id`, `created_at`                                              |
| **source\_documents**     | Google Docs, PDFs, exports               | `id`, `document_type ENUM(google_doc/pdf/chat_export)`, `external_id`, `url`, `raw_content`, `parsed_at`                           |
| **web\_archives**         | all web content referenced in research  | `id`, `url`, `title`, `content_markdown`, `content_html`, `archive_date`, `content_hash`, `source_service`, `file_path`            |
| **article\_web\_refs**    | links articles to archived web content  | `id`, `article_id FK`, `web_archive_id FK`, `reference_type ENUM(source/citation/background)`, `relevance_score`                   |
| **twin\_diff**            | JSON diff output                         | `id`, `twin_set_id`, `diff_jsonb`, `confidence_score FLOAT`                                                                         |
| **gap\_scan\_results**    | Gemini gap & subtopic suggestions       | `id`, `twin_set_id`, `result_jsonb`, `created_at`, `human_reviewed BOOLEAN`                                                         |
| **quality\_checks**       | random verification results              | `id`, `article_id`, `check_type ENUM(citation/fact/coherence)`, `status ENUM(pass/fail/needs_review)`, `details_jsonb`, `checked_at` |
| **citation\_registry**    | extracted and verified citations         | `id`, `article_id`, `citation_text`, `source_url`, `web_archive_id FK`, `verification_status ENUM`, `last_checked`                 |
| **subtopic\_suggestions** | AI-generated subtopic recommendations    | `id`, `parent_topic_id`, `suggested_title`, `rationale`, `priority_score`, `human_approved BOOLEAN`                                 |
| **events**                | every delta, merge, or refresh action    | `id`, `article_id`, `event_type`, `details_jsonb`, `timestamp`                                                                      |
| **workflow\_states**      | track human-in-the-loop progress        | `id`, `topic_id`, `current_step ENUM`, `assigned_to`, `due_date`, `metadata_jsonb`                                                  |

pgvector extension installed → enables similarity search on `articles.embedding`.

---

## 3. Triple-Mode Research Workflows

### 3.1 API-Driven Automation (Original)
- Direct API calls to ChatGPT o1 Pro & Gemini 2.0 Ultra
- Fully automated pipeline
- Higher cost but zero human intervention

### 3.2 Human-in-the-Loop Chat Export
- Researcher uses ChatGPT Pro/Gemini Ultra chat interfaces
- Export results to Google Docs or PDF
- System ingests and processes exported documents
- Significant cost reduction while maintaining functionality

### 3.3 On-Premises Open Source Models (New)
- **Local LLM Infrastructure:** MLX-optimized models running on Mac Studio M3 Ultra
- **Zero External Costs:** No API fees after initial setup
- **Maximum Privacy:** All research data stays on-premises
- **Custom Fine-tuning:** Domain-specific model adaptation capabilities
- **Offline Operation:** Complete functionality without internet dependency

### 3.4 Intelligent Hybrid Approach
- **Critical/Confidential:** On-premises models for sensitive research
- **Complex Reasoning:** API models for advanced analytical tasks
- **Exploratory/Draft:** Chat export workflow for cost optimization
- **Bulk Processing:** Local models for high-volume research tasks

---

## 4. Enhanced Micro‑service Architecture

| Service                       | Image Tag                    | Role                                      | Trigger                    |
| ----------------------------- | ---------------------------- | ----------------------------------------- | -------------------------- |
| **author\_chatgpt**           | `chatgpt-worker:latest`      | Draft anchor report with ChatGPT API     | `new-topic` queue msg      |
| **author\_gemini**            | `gemini-worker:latest`       | Draft anchor with Gemini API             | same                       |
| **author\_local\_reasoning**  | `local-reasoning:latest`     | DeepSeek R1, QwQ-32B reasoning models     | `new-topic-local` queue    |
| **author\_local\_general**    | `local-general:latest`       | Llama 3.3, Gemma 2, Mistral local models | same                       |
| **mlx\_inference\_engine**    | `mlx-engine:latest`          | Apple MLX model serving & management     | local model requests       |
| **model\_manager**            | `model-mgr:latest`           | Download, quantize, fine-tune local LLMs | model deployment tasks     |
| **document\_parser**          | `doc-parser:latest`          | Ingest Google Docs/PDFs from chat exports | `document-uploaded` event  |
| **web\_archiver**             | `web-archiver:latest`        | Archive all web content as markdown      | every web request          |
| **topic\_manager**            | `topic-mgr:latest`           | Generate & manage subtopics               | gap scan results           |
| **diff\_worker**              | `diff-worker:latest`         | Compare twin anchors, store diff          | both anchors complete      |
| **gap\_finder**               | `gap-finder:latest`          | Nightly gap scan + subtopic suggestions   | cron 02:00                 |
| **quality\_controller**       | `qc-worker:latest`           | Random citation & fact verification       | cron + manual triggers     |
| **delta\_writer**             | `delta-writer:latest`        | Summarise external news & bump versions   | RSS/arXiv watcher          |
| **frontend**                  | `kb-frontend:latest`         | React UI (Topics, Diff, QC Dashboard)    | —                          |
| **scheduler**                 | `celery-beat:latest`         | Enhanced queue & cron orchestration       | —                          |
| **queue\_workers**            | `celery-worker:latest`       | Distributed task processing               | —                          |
| **db**, **chroma**, **redis** | upstream images              | persistence & messaging                   | —                          |

---

## 5. Enhanced Container Orchestration

```yaml
# Enhanced docker-compose.yml excerpt
document_parser:
  build: ./docker/document_parser
  depends_on: [db, redis, chroma]
  environment:
    - GOOGLE_DOCS_API_KEY=${GOOGLE_DOCS_API_KEY}
    - PG_URL=postgresql://...
    - CHROMA_URL=http://chroma:8000
  volumes:
    - ./uploads:/app/uploads
    - google_creds:/app/credentials

quality_controller:
  build: ./docker/quality_controller
  depends_on: [db, redis]
  environment:
    - FACT_CHECK_API_KEY=${FACT_CHECK_API_KEY}
    - CITATION_VERIFY_API_KEY=${CITATION_VERIFY_API_KEY}
    - QC_SCHEDULE=0 */6 * * *  # Every 6 hours

topic_manager:
  build: ./docker/topic_manager
  depends_on: [db, redis, chroma]
  environment:
    - SUBTOPIC_GENERATION_MODEL=gpt-4
    - MAX_SUBTOPIC_DEPTH=3

# Celery for enhanced queue management
celery_worker:
  build: ./docker/celery_worker
  depends_on: [db, redis]
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
    - CELERY_RESULT_BACKEND=redis://redis:6379/0
  deploy:
    replicas: 3

celery_beat:
  build: ./docker/celery_beat
  depends_on: [redis]
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
```

---

## 6. Enhanced Workflows

### 6.1 Topic Creation & Research
1. **`researchdb new-topic "TITLE" [--method=api|chat|hybrid]`**
2. **API Mode:** Enqueue twin author tasks → automated processing
3. **Chat Mode:** Generate workflow state → notify human → await document upload
4. **Hybrid Mode:** Critical aspects via API, exploratory via chat

### 6.2 Document Ingestion Pipeline
1. **Upload Detection:** Google Drive webhook or manual upload
2. **Document Parsing:** Extract markdown, metadata, citations
3. **Web Content Archival:** All referenced URLs automatically archived as markdown
4. **Quality Preprocessing:** Initial citation extraction & validation
5. **Vector Embedding:** Store in Chroma + Postgres
6. **Twin Matching:** Link to corresponding twin report if available
7. **Archive Linking:** Connect articles to archived web references

### 6.3 Subtopic Generation & Management
1. **Gap Analysis:** Identify missing coverage areas
2. **Subtopic Suggestion:** AI-generated recommendations with priority scores
3. **Human Review:** Approve/reject/modify suggestions via frontend
4. **Recursive Research:** Approved subtopics enter research pipeline
5. **Hierarchy Management:** Maintain topic tree with max depth limits

### 6.4 Quality Control & Verification
1. **Random Sampling:** Select articles for QC based on configurable criteria
2. **Citation Verification:** Check source URLs, extract metadata, auto-archive
3. **Fact Checking:** Cross-reference claims against authoritative sources
4. **Coherence Analysis:** Detect contradictions within and between articles
5. **Archive Integrity:** Verify all web references are properly archived
6. **Human Review Queue:** Flag issues requiring manual intervention

---

## 7. Enhanced LLM Prompt Management

### 7.1 Versioned Prompt Templates

```json
{
  "prompts": {
    "deep_research_v1": {
      "system": "You are a domain expert researcher...",
      "user": "Produce an exhaustive report on \"{topic}\" covering...",
      "parameters": {"temperature": 0.3, "max_tokens": 8000},
      "active": true
    },
    "deep_research_v2": {
      "system": "As a meticulous academic researcher with 20+ years experience...",
      "user": "Create a comprehensive analysis of \"{topic}\" including...",
      "parameters": {"temperature": 0.2, "max_tokens": 12000},
      "active": false,
      "ab_test_weight": 0.1
    },
    "subtopic_generation": {
      "system": "You are an expert at breaking down complex topics...",
      "user": "Given this research on \"{topic}\", identify 3-7 important subtopics...",
      "output_schema": "json"
    },
    "quality_check_citation": {
      "system": "You are a fact-checking specialist...",
      "user": "Verify these citations and flag any issues: {citations}",
      "output_schema": "json"
    }
  }
}
```

### 7.2 A/B Testing Framework
- Weighted prompt selection for quality comparison
- Performance metrics tracking per prompt version
- Automated promotion of high-performing prompts

---

## 8. Frontend Architecture & Features

### 8.1 Enhanced Features
- **Topics Dashboard:** Hierarchical topic tree with status indicators
- **Research Workflow:** Human task queue and progress tracking
- **Twin Diff Viewer:** Side-by-side comparison with highlighting
- **Gap Radar:** Visual representation of knowledge gaps
- **Quality Control Dashboard:** QC results and review queue
- **Export Hub:** PDF, Word, citation export functionality
- **Archive Browser:** Search and browse all archived web content
- **Citation Tracker:** Visual map of source-to-article relationships

### 8.2 Enhanced Features
- **Real-time Updates:** WebSocket connections for long-running tasks
- **Advanced Diff Visualization:** Monaco Editor-style diff viewer
- **Citation Management:** Interactive citation browser and validator
- **Subtopic Explorer:** Interactive topic hierarchy navigation
- **Quality Metrics:** Article quality scores and trending analysis
- **Archive Search:** Full-text search across all archived web content
- **Source Timeline:** Chronological view of research source evolution

### 8.3 Export Capabilities
- PDF reports with custom formatting and archived source appendices
- Word documents with proper citations and source links
- BibTeX/EndNote citation exports with archived content references
- Markdown bundles with embedded archived sources
- JSON data exports with complete archive metadata
- Source archive packages for offline reference

---

## 9. Enhanced Scheduling Matrix

| Job                      | Schedule           | Owner               | Duration | Priority |
| ------------------------ | ------------------ | ------------------- | -------- | -------- |
| RSS / Paper fetch        | \*/15 \* \* \* \*  | ingest‑worker       | <30 s    | High     |
| Document parsing queue   | \*/5 \* \* \* \*   | document\_parser    | 1-2 min  | High     |
| Embedding generation     | @hourly            | embedder            | 2–3 min  | Medium   |
| Gap scan & subtopics     | 02:00 daily        | gap\_finder         | 5–8 min  | Medium   |
| Quality control sampling | 04:00 daily        | quality\_controller | 10-15 min| Medium   |
| Citation verification    | 0 */6 * * *        | quality\_controller | 5-10 min | Low      |
| Staleness audit          | Sun 03:00          | refresh\_manager    | <1 min   | Low      |
| Workflow cleanup         | @daily             | topic\_manager      | <30 s    | Low      |

---

## 10. Quality Control & Verification System

### 10.1 Random Sampling Strategy
- **Frequency:** 5% of new articles, 1% of existing articles monthly
- **Selection Criteria:** Weighted by topic importance, recency, citation count
- **Coverage:** Ensure all research areas receive QC attention

### 10.2 Verification Types
- **Citation Verification:** URL accessibility, metadata accuracy, content relevance
- **Fact Checking:** Cross-reference claims with authoritative databases
- **Coherence Analysis:** Detect internal contradictions and logical gaps
- **Source Quality:** Evaluate source credibility and bias indicators

### 10.3 Quality Metrics
- **Citation Accuracy Score:** Percentage of verified citations
- **Fact Reliability Index:** Claims verified against multiple sources
- **Coherence Rating:** Logical consistency within article
- **Source Diversity Score:** Range of source types and perspectives

---

## 11. Security & Secrets Management

### 11.1 Enhanced Security
- API keys stored in 1Password; pulled via `op inject` into `.env`
- Google Cloud Service Account for Docs API access
- JWT-based authentication for frontend access
- Rate limiting on all API endpoints
- Document upload validation and sanitization

### 11.2 Backup & Recovery
- DB backed up nightly via `pg_dump` → `restic` encrypted snapshots
- Google Docs integration with versioning
- Vector embeddings backup to cloud storage
- Disaster recovery procedures documented

### 11.3 Network Security
- Docker networks isolated (`internal: true`) for workers
- Only `frontend` and `api_gateway` expose external ports
- SSL/TLS encryption for all external communications
- VPN access for administrative functions

---

## 12. Cost Optimization Strategies

### 12.1 API Cost Management
- **Chat Export Priority:** Default to human workflow for cost reduction
- **API Budget Limits:** Configurable monthly spending caps
- **Intelligent Routing:** Route complex topics to API, simple to chat export
- **Batch Processing:** Group similar requests to reduce API calls

### 12.2 Resource Optimization
- **Embedding Caching:** Reuse embeddings for similar content
- **Vector Compression:** Use quantized embeddings where appropriate
- **Storage Tiering:** Archive old versions to cheaper storage
- **Compute Scaling:** Auto-scale worker containers based on queue depth

---

## 13. Developer Workflow & Testing

### 13.1 Development Setup
1. `poetry install ‑n` – create virtual environment
2. `docker compose up ‑d db chroma redis` – start core services
3. `pytest tests/` – run comprehensive test suite
4. `docker compose up --build` – run full stack
5. `researchdb new-topic "Test Topic" --method=chat` – validate workflows

### 13.2 Testing Strategy
- **Unit Tests:** Individual service components
- **Integration Tests:** Service-to-service communication
- **End-to-End Tests:** Complete workflow validation
- **Performance Tests:** Load testing for queue processing
- **Quality Tests:** Verify QC system accuracy

---

## 14. Implementation Roadmap

### 14.1 Sprint 0 (Foundation) - 2 weeks
1. **Enhanced schema migration** – Alembic revision with new tables ✔︎
2. **CLI Typer scaffold** – Enhanced with local model commands ✔︎
3. **MLX inference engine** – Core Apple Silicon model serving
4. **Model manager service** – Local model deployment pipeline
5. **Basic local model integration** – DeepSeek R1 + Llama 3.3 setup

### 14.2 Sprint 1 (Core Functionality) - 3 weeks
1. **Local reasoning worker** – DeepSeek R1 research generation
2. **Document ingestion pipeline** – End-to-end chat export processing
3. **Enhanced diff worker** – Local vs. API model comparison
4. **Model management UI** – Local model status dashboard
5. **Celery integration** – Enhanced queue system with model routing

### 14.3 Sprint 2 (Intelligence Layer) - 3 weeks
1. **Triple-mode research system** – API + Chat Export + Local models
2. **Intelligent model routing** – Cost-performance optimization
3. **Quality control system** – Local model verification pipeline
4. **Advanced frontend** – Model comparison viewer and performance metrics
5. **Fine-tuning pipeline** – Domain-specific model adaptation

### 14.4 Sprint 3 (Production Ready) - 2 weeks
1. **Local model optimization** – Memory management and performance tuning
2. **Monitoring & alerting** – Model performance and system health
3. **Security hardening** – Data sovereignty and access controls
4. **Export functionality** – Multi-format output with model attribution
5. **Documentation** – Local model setup and optimization guides

---

## 15. Long‑Term Vision & Backlog

### 15.1 Advanced Features
- **Browser Automation:** Selenium-based chat UI interaction
- **Multi-language Support:** Research in multiple languages
- **Collaborative Features:** Team-based research workflows
- **API Marketplace:** Third-party integrations and plugins

### 15.2 Infrastructure Evolution
- **Kubernetes Migration:** Container orchestration at scale
- **Multi-cloud Deployment:** AWS, GCP, Azure support
- **Edge Computing:** Regional research processing
- **Machine Learning Pipeline:** Custom models for domain-specific research

### 15.3 Research Intelligence
- **Predictive Gap Analysis:** ML-powered gap prediction
- **Automated Literature Reviews:** Systematic review generation
- **Research Trend Analysis:** Topic popularity and evolution tracking
- **Citation Network Analysis:** Research connection mapping

---

## 16. Quick‑Start Context for New Chats

> **Twin‑Report KB Project Summary:** Self-hosted research platform creating twin anchor reports from ChatGPT o1 Pro, Gemini 2.0 Ultra, AND local LLMs (DeepSeek R1, Llama 3.3). Triple-mode operation: API automation + human chat export + on-premises MLX models. Core features: gap detection, subtopic generation, quality control, citation verification. Stack: Docker, PostgreSQL+pgvector, Chroma, Python (Poetry), React, Celery, Apple MLX. Key services: local model engine, model manager, document parser, quality controller. Human-in-the-loop design with cost optimization and complete data sovereignty via Mac Studio M3 Ultra. Current phase: Sprint 0 with local LLM integration.

*Copy this paragraph into new sessions to load complete project context without overwhelming the prompt window.*

---

## 17. Monitoring & Observability

### 17.1 Key Metrics
- **Research Velocity:** Topics completed per day/week
- **Quality Scores:** Average citation accuracy, fact reliability
- **Cost Efficiency:** API costs vs. chat export usage
- **Human Productivity:** Tasks completed per researcher
- **System Performance:** Queue processing times, embedding generation speed

### 17.2 Alerting Thresholds
- Queue depth > 50 items for > 15 minutes
- Quality control failure rate > 10%
- API cost exceeding 120% of monthly budget
- Citation verification failures > 5% daily
- Document parsing errors > 2% of uploads

### 17.3 Dashboards
- **Operations Dashboard:** System health, queue status, error rates
- **Research Dashboard:** Topic completion, quality trends, gap analysis
- **Cost Dashboard:** API usage, cost per topic, efficiency metrics
- **Quality Dashboard:** QC results, citation health, fact-check status

---

*This specification serves as the definitive memory and reference for the Twin-Report Knowledge-Base project, designed for sharing across different LLM conversations and maintaining consistent project understanding.*