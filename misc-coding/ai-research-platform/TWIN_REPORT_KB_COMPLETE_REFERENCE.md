# Twin-Report KB – Complete Architecture & Implementation Reference

**Date:** June 25, 2025  
**Status:** 90 % COMPLETE – Frontend final phases in progress; all backend services operational.

---

## 1. Project Overview
Twin-Report KB is an end-to-end knowledge-base builder that ingests research documents, extracts structured insights with local LLM reasoning on a Mac Studio, scores quality, detects gaps versus existing knowledge, and serves results through a modern dashboard.

Key design goals:
• Research-grade document support (PDF, Office, web, Google Docs).  
• Full explainability: topic taxonomy, quality metrics, diff/gap analysis.  
• 100 % local processing – data never leaves the Mac Studio.  
• Micro-service isolation for scale & independent iteration.

---

## 2. Micro-services & Ports
| # | Service | Purpose | Docker Context | Container | Internal Port | Host Port |
|---|---------|---------|---------------|-----------|---------------|-----------|
| 1 | **PostgreSQL** | Central DB | `postgres:15-alpine` | `twin_report_kb_postgres` | 5432 | **5434** |
| 2 | **Document Parser** | Multi-format extraction & normalization | `docker/document_parser` | `twin_report_kb_document_parser` | 8000 | **8100** |
| 3 | **Topic Manager** | Topic extraction & classification | `docker/topic_manager` | `twin_report_kb_topic_manager` | 8101 | **8101** |
| 4 | **Quality Controller** | Fact-checking & credibility scoring | `docker/quality_controller` | `twin_report_kb_quality_controller` | 8000 | **8102** |
| 5 | **Diff Worker** | Gap detection / version comparison | `docker/diff_worker` | `twin_report_kb_diff_worker` | 8000 | **8103** |
| 6 | **Author Local Reasoning** | Deep reasoning & summarisation | `docker/author_local_reasoning` | `twin_report_kb_author_reasoning` | 8000 | **8104** |
| 7 | **Frontend** | FastAPI + Jinja2 Dashboard | `docker/frontend` | `twin_report_kb_frontend` | 8000 | **3100** |

All services share the Docker network `twin_report_kb_network`.

---

## 3. Processing Pipeline
1. **Upload** → `POST /parse/upload` (Document Parser) extracts text, metadata, & embeds file in DB.  
2. **Topic Taxonomy** → `POST /categorize` (Topic Manager) produces up to 20 topics with confidence scores.  
3. **Quality Assessment** → `POST /quality-check` (Quality Controller) runs fact & citation checks, returns A–F grade + JSON report.  
4. **Gap Analysis** → `POST /analyze-diff` (Diff Worker) compares against reference corpus, highlights missing perspectives.  
5. **Author Reasoning** → `POST /reason` (Author Local Reasoning) generates insights / summaries using local Llama 4:Scout.

Data and status are persisted in PostgreSQL; binary assets live under `data/` volumes (uploads, processed, diffs, versions, cache, etc.).

---

## 4. Database Schema (Init scripts in `migrations/`)
• `documents` – id, title, mime_type, path, parsed_at, checksum  
• `topics` – id, document_id FK, name, confidence  
• `quality_reports` – id, document_id FK, grade, detail_json, created_at  
• `diffs` – id, original_doc_id FK, compared_doc_id FK, similarity, diff_json  
• `versions` – id, document_id FK, version_tag, notes, created_at  
• `reasoning_cache` – id, doc_id FK, prompt_hash, completion_text

> NOTE: schema auto-runs via `docker-entrypoint-initdb.d` on first PostgreSQL boot.

---

## 5. Environment Variables
| Variable | Default / Example | Used By |
|----------|------------------|---------|
| `DATABASE_URL` | `postgresql://twin_report:secure_password@postgres:5432/twin_report_kb` | All backend svcs |
| `MAC_STUDIO_LLM_ENDPOINT` | `http://192.168.1.50:9000/v1/chat/completions` | All LLM powered svcs |
| `MAX_FILE_SIZE` | `100MB` | Document Parser |
| `SUPPORTED_FORMATS` | `pdf,docx,xlsx,pptx,txt,html,md` | Document Parser |
| `QUALITY_THRESHOLD` | `0.7` | Quality Controller |
| `SIMILARITY_THRESHOLD` | `0.8` | Diff Worker |
| _etc._ | See individual Dockerfiles for full list |

> Secrets (passwords, endpoints) are injected via env-vars or Docker secrets – **never committed to Git**.

---

## 6. Quick Start
```bash
cd sub-projects/twin-report-kb
# Build & start all services
docker-compose up -d
# Check health
curl http://localhost:8100/health            # Document Parser
curl http://localhost:8101/health            # Topic Manager
curl http://localhost:8102/health            # Quality Controller
curl http://localhost:8103/health            # Diff Worker
curl http://localhost:8104/health            # Author Reasoning
open http://localhost:3100                   # Dashboard
```

---

## 7. API Cheat-Sheet
### Document Parser (`8100`)
```
GET  /health
POST /parse/upload             multipart/form-data file=<file>
POST /parse/url                {"url": "https://..."}
GET  /document/{id}
```
### Topic Manager (`8101`)
```
GET  /health
POST /categorize               {"doc_id": 123}
```
### Quality Controller (`8102`)
```
GET  /health
POST /quality-check            {"doc_id": 123}
```
### Diff Worker (`8103`)
```
GET  /health
POST /analyze-diff             {"doc_id":123, "against_doc_id":456}
```
### Author Local Reasoning (`8104`)
```
GET  /health
POST /reason                   {"doc_id":123, "query":"Summarize key gaps"}
```

---

## 8. Frontend Dashboard Routes (`3100`)
| Path | Function |
|------|----------|
| `/` | System overview & recent activity |
| `/upload` | Upload documents / URLs |
| `/analysis/{task_id}` | Live pipeline progress |
| `/results/{doc_id}` | Full results viewer |
| `/batch` | Batch processing queue |
| `/settings` | Configuration UI |
| `/health` | Integrated service health board |

Frontend is a FastAPI server serving Jinja2 templates + static assets under `docker/frontend`.

---

## 9. Resource Allocation
| Service | CPU Limit | Mem Limit |
|---------|-----------|-----------|
| Document Parser | 2 cores | 4 GB |
| Topic Manager | 1.5 cores | 3 GB |
| Quality Controller | 2 cores | 4 GB |
| Diff Worker | 1.5 cores | 3 GB |
| Author Reasoning | 3 cores (6 GB limit / 2 GB reserve) | 6 GB |

---

## 10. Security & Compliance
• All secrets via env-vars; `.gitignore` excludes `*_credentials.json`, `drive_service_account.json`, and any LLM model keys.  
• Database access limited to Docker network.  
• Uploaded files stored in local volumes, enforce `MAX_FILE_SIZE`.  
• Audit logs captured via `structlog` across services.

---

## 11. Current Completion Matrix
| Component | Status |
|-----------|--------|
| Backend micro-services (5) | ✅ 100 % |
| Frontend Phases 1-2 | ✅ Done |
| Frontend Phases 3-5 | 🔄 In progress (Results, Health, Settings) |
| Database migrations | ✅ Applied |
| Mac Studio LLM integration | ✅ Configured |
| End-to-End tests | ⚠️ Pending after frontend completion |

---

## 12. Roadmap (Q3 2025)
1. Finish dashboard phases 3-5 (≈6 hrs).  
2. Add export to Obsidian vault.  
3. Implement citation graph view using Mermaid.  
4. Performance tuning with PgBouncer & async streaming.  
5. Optional: switch Diff Worker to async-LLM chunk processing for >50 MB docs.

---

**Twin-Report KB is nearly production-ready – only dashboard polish remains.** 