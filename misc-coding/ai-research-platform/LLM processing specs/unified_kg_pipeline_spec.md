# Unified Knowledge‑Graph Processing Pipeline – **LLM‑Friendly Master Spec**

> **Audience**  Autonomous coding agents (Cursor, OpenAI Dev Tools) & platform dev‑ops team\
> **Purpose**  Bind **pre‑processing**, **LLM extraction**, and **graph visualisation** into a single executable blueprint.  Every contract (Docker image, API spec, event, schema) is crystal‑clear so an agent can scaffold or refactor services without human guesswork.

---

## 1  Mission & Context

Our platform converts *any* idea — X posts, lab memos, 40‑page papers — into **living insights**.

| Step | Objective                                             | Primary Service                    |
| ---- | ----------------------------------------------------- | ---------------------------------- |
|  1   |  Normalize artefacts → Markdown + YAML                | **content\_extractor** (existing)  |
|  2   |  Clean, enrich, **chunk** (< 1 500 tokens)            | **pre\_processor**                 |
|  3   |  Call local or hosted **LLM** → JSON (nodes + edges)  | **llm\_extractor**                 |
|  4   |  Persist with versioning, embeddings                  | **graph\_service**                 |
|  5   |  Render graphs, timelines, reports                    | **viz\_dashboard**                 |

> *Design creed*  “LLM calls see only tidy Markdown chunks; dashboards see only typed nodes & edges.”

---

## 2  End‑to‑End Flow

```mermaid
graph TD
A[Intake\n(email / URL / upload)] --> B[content_extractor]
B --> C[pre_processor]:::svc
C -->|Markdown\n+ Chunks| D[llm_extractor]:::svc
D -->|JSON\n(nodes+edges)| E[graph_service]:::svc
E --> F[viz_dashboard]
classDef svc fill:#f0f8ff,stroke:#036,stroke-width:1.5px;
```

---

## 3  Micro‑Service Catalogue

| Name                   | Image / Lang                               | Ports       | Key deps                                                        | Contracts                      |
| ---------------------- | ------------------------------------------ | ----------- | --------------------------------------------------------------- | ------------------------------ |
| **content\_extractor** | `python:3.12-slim`                         | 8000        | BeautifulSoup, PyMuPDF                                          | REST `/extract` → raw Markdown |
| **pre\_processor**     | `python:3.12-slim`                         | 8001        | `spacy`, `fasttext`, `markdown-it-py`, `pgvector` client, Redis | described §4                   |
| **llm\_extractor**     | `ghcr.io/llama.cpp:metal` **or** API proxy | 8002        | llama.cpp / anthropic / gemini SDK                              | described §5                   |
| **graph\_service**     | `neo4j:5` **or** Postgres + pg\_graph      | 7474 / 5432 | pgvector, Timescale                                             | Nodes/Edges tables §6          |
| **viz\_dashboard**     | `node:18` (React)                          | 3000        | cytoscape.js, d3, recharts                                      | pulls `/api/graph`             |

Docker‑Compose glue:

```yaml
services:
  content_extractor:
    build: ./services/content_extractor
  pre_processor:
    build: ./services/pre_processor
    depends_on: [content_extractor, redis]
  llm_extractor:
    build: ./services/llm_extractor
    environment:
      - LLM_ENDPOINT=http://localhost:11434      # llama.cpp
  graph_service:
    image: postgres:16                              # variant with pgvector & bitemporal ext
  viz_dashboard:
    build: ./services/viz_dashboard
  redis:
    image: redis:7
```

---

## 4  **pre\_processor** – Detailed Spec

### 4.1  API

| Verb   | Path         | Body → Returns                               |
| ------ | ------------ | -------------------------------------------- |
| `POST` | `/normalize` | `{raw, mime}` → `markdown`                   |
| `POST` | `/chunk`     | `{markdown}` → `[ {chunk_id, text, order} ]` |
| `GET`  | `/health`    | *ping*                                       |

### 4.2  Processing Pipeline

1. **De‑HTML / OCR** (PDF → text via PyMuPDF).
2. **Encode fix** → `ftfy`.
3. **Insert YAML front‑matter** with `idea_id`, `lang`, `source`, timestamps.
4. **Sentence‑split & lang‑detect** (`spacy`, `fasttext`).
5. **Chunking rules**
   - Prefer heading depth (`##`, `###`).
   - If chunk > 800 tokens, split by paragraphs (\~350 tok) with one‑paragraph overlap.
   - Final fallback: sliding 200‑tok window with 40‑tok overlap.
6. **Deduplicate** – skip chunk if cosine‑sim > 0.97 to stored embeddings.
7. **Emit event** `idea.preprocessed` with payload:

```jsonc
{
  "idea_id": "123e4567",
  "chunks": [
    {"chunk_id": "123e4567_a1b2c3d4", "order": 0, "text": "..."},
    ...
  ]
}
```

---

## 5  **llm\_extractor** – Node & Edge Generator

### 5.1  Prompt Contract (tool‑calling style)

```jsonc
{
  "model": "llama4-scout-8k",
  "temperature": 0.2,
  "tools": [
    {
      "name": "emit_graph_objects",
      "description": "Return extracted nodes and edges as JSON",
      "parameters": {
        "type": "object",
        "properties": {
          "nodes": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "tmp_id": {"type": "string"},
                "label": {"type": "string"},
                "kind": {"enum": ["Idea","Evidence","Method","Metric"]},
                "attrs": {"type": "object"}
              },
              "required": ["tmp_id","label","kind"]
            }
          },
          "edges": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "source_tmp": {"type": "string"},
                "target_tmp": {"type": "string"},
                "relation": {"enum": ["is-a","part-of","supports","contradicts","leads-to","related-to"]},
                "confidence": {"type": "number"}
              },
              "required": ["source_tmp","target_tmp","relation"]
            }
          }
        },
        "required": ["nodes","edges"]
      }
    }
  ],
  "messages": [
    {"role": "system", "content": "You are a knowledge‑graph extraction agent. Think silently; respond ONLY via tool."},
    {"role": "user", "content": "# CHUNK\n... markdown snippet ...\n# CONTEXT\n1. node_id: n123 title: ..."}
  ]
}
```

### 5.2  Post‑Processing

- Run **3‑way self‑consistency**; accept edge if ≥ 2 models agree.
- Map `tmp_id` → real IDs, bulk insert into `nodes` & `edges` with `valid_from = now()`.
- Low‑confidence (< 0.8) edges → `review_queue`.

---

## 6  Knowledge‑Graph Data Model

### 6.1  Tables / Collections

| Table          | Selected fields                                                                       |
| -------------- | ------------------------------------------------------------------------------------- |
| `nodes`        | `id PK`, `label`, `kind`, `attrs JSONB`, `lifecycle_stage`, `valid_from`, `valid_to`  |
| `edges`        | `id PK`, `source_id`, `target_id`, `relation`, `confidence`, `valid_from`, `valid_to` |
| `embeddings`   | `node_id`, `vector` (pgvector)                                                        |
| `review_queue` | `edge_id`, `reason`, `created_at`                                                     |

### 6.2  Edge Taxonomy (core set)

| Layer      | Relation                                  | When visible      | Visual encoding           |
| ---------- | ----------------------------------------- | ----------------- | ------------------------- |
| Structural | `is-a`, `part-of`                         | Always at zoom ≤2 | Light‑gray straight lines |
| Argument   | `supports`, `contradicts`, `inconclusive` | Show on demand    | Green / red arrows        |
| Causal     | `leads-to`, `precedes`                    | Process view      | Arrowheads                |
| Semantic   | `related-to` (sim ≥ τ)                    | Hidden by default | Dashed, faded             |

---

## 7  Visualisation & Reporting Layer

- **Semantic zoom** – hide non‑structural edges when zoomed out.
- **Edge bundling** – aggregate parallel `supports` into weighted splines.
- **Complementary views**
  - *Timeline heatmap* for lifecycle drift.
  - *Sankey* for idea lineage.
  - *UMAP scatter* for similarity landscape.
- **Reports** (auto‑generate as CSV & dashboard widgets)  Insight Health, Concept Drift Alerts, Coverage Gap Matrix, Time‑to‑Insight SLA.

---

## 8  Scaling & Performance Targets (Mac Studio M3 Ultra)

| Batch (ideas) | Sequential wall‑clock | 4‑worker parallel |
| ------------- | --------------------- | ----------------- |
| 10            | \~51 s                | **≤ 15 s**        |
| 100           | \~8.5 min             | **≤ 2.5 min**     |

LLM throughput: \~60 tok/s via `llama.cpp -m metal`; chunk cap = 1 500 tok.

---

## 9  Integration Events & Messaging

| Event                 | Publisher      | Payload                               | Subscriber action      |
| --------------------- | -------------- | ------------------------------------- | ---------------------- |
| `idea.preprocessed`   | pre\_processor | `{idea_id, chunks[]}`                 | llm\_extractor enqueue |
| `graph.new_objects`   | llm\_extractor | `{idea_id, new_nodes[], new_edges[]}` | viz\_dashboard refresh |
| `edge.low_confidence` | llm\_extractor | `{edge_id, reason}`                   | review UI badge        |

Redis Streams or Rabbit MQ acceptable; fallback to Postgres NOTIFY if messaging stack omitted.

---

## 10  Plain‑English Narrative (for non‑tech stakeholders)

> 1. **Inbox** – Ideas arrive by email, web clip, or upload.
> 2. The **Librarian bot** rewrites each into tidy Markdown pages and, if a page is long, snips it into bite‑sized notes.
> 3. The **Researcher bot** (LLM) reads each note plus a few related notes, fills in index cards (nodes) and draws arrows (edges).
> 4. A **Historian bot** stores the cards, dates them, and redraws our knowledge atlas.
> 5. Dashboards show maps, timelines, and confidence gauges so humans see what’s solid, what clashes, and what’s missing.

---

## 11  Open Questions for the Product Owner

1. **Graph DB choice** – Neo4j vs. Postgres + pg\_graph: any prior constraints?
2. **Auth & PII** – Should YAML front‑matter drop or hash personal emails?
3. **Languages** – Is non‑English content out of scope or must we translate?
4. **Review workflow** – Who triages low‑confidence edges? SLA?
5. **Real‑time vs. batch** – Are sub‑10‑second latencies vital, or is nightly OK for large drops?

> *Please clarify before generator agents scaffold production infrastructure.*

