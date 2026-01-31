# Pre‑Processor Micro‑Service – Docker Canvas

> **Objective**  Provide an LLM‑readable blueprint that Cursor (or another coding agent) can use to scaffold, implement, and register a standalone `pre_processor` service that normalises, cleans, and chunks incoming ideas before they reach the LLM extraction layer.
>
> **Scope**  Markdown normalisation · metadata injection · chunking rules · similarity de‑duplication · API/queue contracts · Docker/K8s hints · integration hooks.

---

## 1  High‑level responsibilities

1. **Normalise** raw artefacts (HTML, PDF, plain text, X post, email, image OCR output) → **clean Markdown + YAML front‑matter**.
2. **Chunk** long Markdown into context‑bounded slices (< ≈1 500 tokens) with optional semantic overlap.
3. **Enrich** each chunk with deterministic IDs, language tag, SHA‑1 hash, token count, and embeddings (optional – controlled by flag).
4. **Publish** `idea.preprocessed` (original) & `idea.chunked` (list of slices) events on Redis/AMQP for downstream LLM workers.
5. **Expose** REST endpoints for ad‑hoc processing and health checks.

---

## 2  Supported input artefacts & handling rules

| `source` value       | Ingress channel                                                    | Library stack                             | Normalisation steps                                                                                                                  | Notes                                                                                                  |
| -------------------- | ------------------------------------------------------------------ | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `email`              | Existing Gmail API fetch → **content\_extractor** pipes MIME to us | `mailparser`, `beautifulsoup4`            | Strip quoted replies ➜ convert HTML to Markdown (CommonMark) ➜ YAML front‑matter (`source: email`, `subject`, `from`, `received_at`) | Keep embedded images as `[image:n]` placeholders; attachments routed through existing attachments flow |
| `x-post`             | X API webhook → JSON                                               | `markdownify`, custom short‑link expander | Expand URLs ➜ Markdown blockquote for original tweet ➜ add tweet metadata                                                            | 280 chars ➜ skip chunking unless thread > 1 000 tokens                                                 |
| `url` (article/blog) | Link push from UI                                                  | `trafilatura`, `readability-lxml`         | Boilerplate removal ➜ Markdown ➜ Title = `#` H1                                                                                      | If paywalled snapshot exists, use cached HTML                                                          |
| `upload` (PDF, DOCX) | Multipart upload → S3 presigned URL                                | `pymupdf`, `python-docx`, `pandoc`        | OCR (Tesseract) for scanned PDFs ➜ structural Markdown headings                                                                      | Extract abstract & keywords when present                                                               |
| `research_paper_api` | arXiv/semantic‑scholar ID                                          | same as PDF + metadata fetch              | Merge BibTeX YAML into front‑matter                                                                                                  | Provides canonical DOI                                                                                 |

---

## 3  Chunking strategy

```mermaid
flowchart TB
  A[Markdown] -->|H2/H3 split| B[Sections]
  B -->|>800 tokens| C[Paragraph splitter]
  C -->|>400 tokens| D[Sentence window (200, overlap 40)]
  B -->|≤800 tokens| E[Emit chunk]
```

### Constants

```yaml
MAX_TOKENS_PROMPT: 1500      # hard cap per LLM call
MAX_TOKENS_SECTION: 800      # target for heading‑based slices
MAX_TOKENS_PARAGRAPH: 400    # fallback threshold
WINDOW_TOKENS: 200           # sliding window size
WINDOW_OVERLAP: 40           # context carry‑over
```

### Chunk object schema (JSON)

```jsonc
{
  "chunk_id"    : "<idea_id>_<sha1-8>",
  "idea_id"     : "uuid",
  "order"       : 0,
  "text"        : "md string",
  "token_count" : 532,
  "lang"        : "en",
  "hash"        : "sha1",
  "created_at"  : "2025-07-13T15:00:04Z",
  "embedding"   : [0.123, ...],        // optional
  "source_meta" : { ... front‑matter }
}
```

### De‑duplication

- Compute cosine similarity on **MiniLM** embeddings (via `sentence‑transformers`).
- Drop any chunk whose similarity to an existing chunk (`idea_id` scoped) > 0.97.

---

## 4  Container layout

```
pre_processor/
├── Dockerfile
├── requirements.txt
├── app/
│   ├── main.py        # FastAPI entrypoint
│   ├── routers/
│   │   ├── normalize.py
│   │   └── chunk.py
│   ├── workers/
│   │   └── tasks.py   # Celery heavy jobs (PDF, OCR)
│   ├── core/
│   │   ├── converters.py  # html→md, pdf→md
│   │   ├── chunker.py
│   │   ├── utils.py
│   │   └── config.py
│   └── events.py      # Redis pub/sub helpers
└── tests/
    └── ... pytest ...
```

### Dockerfile (sketch)

```dockerfile
FROM python:3.12-slim

# base libs for PDF, OCR, pandoc
RUN apt-get update && apt-get install -y \
    poppler-utils tesseract-ocr pandoc && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

ENV PYTHONUNBUFFERED=1
CMD [ "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001" ]
```

### `requirements.txt` (excerpt)

```
fastapi==0.111.*
uvicorn[standard]==0.29.*
markdown-it-py==3.*
beautifulsoup4==4.*
trafilatura==1.*
readability-lxml==0.9.*
ftfy==6.*
spacy==3.*
sentence-transformers==2.*
redis==5.*
celery==5.*
python-frontmatter==1.*
python-dotenv==1.*
```

---

## 5  Service API

| Verb   | Path         | Body                                               | Returns             | Notes                              |                                             |
| ------ | ------------ | -------------------------------------------------- | ------------------- | ---------------------------------- | ------------------------------------------- |
| `POST` | `/normalize` | \`{ "idea\_id": str, "source": str, "payload": str | url }\`             | `{ "markdown": str }`              | Heavy types (PDF) processed async ➜ job\_id |
| `POST` | `/chunk`     | `{ "idea_id": str, "markdown": str }`              | `[ ChunkSchema ]`   | Optionally `store=true` to persist |                                             |
| `GET`  | `/health`    | —                                                  | `{ status: "ok" }`  | Liveness probe                     |                                             |
| `GET`  | `/job/{id}`  | —                                                  | `{ state, result }` | Celery status                      |                                             |

**Event contract** (Redis channel `idea.events`):

```jsonc
// after normalization
action: "idea.preprocessed"
data: { "idea_id": "...", "markdown_url": "s3://..." }

// after chunking
action: "idea.chunked"
data: { "idea_id": "...", "chunks": ["chunk_id1", ...] }
```

---

## 6  Integration hooks

| Needed detail                               | Assumed placeholder          | Action for dev agent                     |
| ------------------------------------------- | ---------------------------- | ---------------------------------------- |
| **S3 bucket** for Markdown & chunk uploads  | `${IDEA_BUCKET}`             | Update `.env` & boto config              |
| **Database URL** for storing chunk metadata | `${POSTGRES_URL}`            | Add Alembic migration for `chunks` table |
| **Redis** host/port                         | `redis://redis:6379/0`       | Ensure network in `docker-compose.yml`   |
| **Embedding service** (optional)            | `http://embedder:8002/embed` | If absent, skip embeddings & warn        |

---

## 7  Scaling & deployment hints

- **Horizontal scale** via `--workers N`; CPU‑bound tasks (HTML→MD) benefit, GPU/Neural not required.
- **Heavy conversions** (PDF OCR) sit behind Celery & shared `tesseract` – allocate a dedicated worker class.
- **K8s**: add `HorizontalPodAutoscaler` triggered by Celery queue length.
- **Metrics**: expose `/metrics` Prometheus endpoint (FastAPI middleware) – use histograms for `normalize_latency_seconds` & `chunk_tokens`.

---

## 8  Testing checklist

| Test                 | Description                                                     |
| -------------------- | --------------------------------------------------------------- |
| **unit‑html2md**     | HTML with nested tags → valid GFM, headings preserved           |
| **unit‑chunk‑sizes** | 5 000‑token doc splits into ≤ 10 chunks each ≤ 1 500 tokens     |
| **e2e‑email**        | Sample `.eml` → `/normalize` → `/chunk` →  `idea.chunked` event |
| **sim‑dup**          | Duplicate paragraph similarity > 0.97 filtered                  |
| **api‑schema**       | OpenAPI generated matches spec (CI fail if diff)                |

---

## 9  Future hooks

- **Language translation** queue for non‑English chunks (DeepL/local model).  Place behind feature flag.
- **Image‑to‑text** (diagram OCR) via `paddle‑ocr` when markdown placeholder detected.
- **Source maps** link chunk sentence offsets back to PDF page for citation pop‑overs in UI.

---

> **Hand‑off note for Cursor / LLM agent**: Embed this canvas at `/docs/pre_processor_spec.md` in the repo.  Generate the Dockerfile, FastAPI scaffolding, and Alembic migration in a new feature branch `feat/pre-processor-service`.  Ensure existing `docker-compose.override.yml` includes the service with proper dependency on `content_extractor`.

