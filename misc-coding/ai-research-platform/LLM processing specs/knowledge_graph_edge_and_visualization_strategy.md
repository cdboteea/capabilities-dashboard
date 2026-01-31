# Knowledge‑Graph Edge Taxonomy & Visualization Strategy

## 1  Purpose
Offer a concise, implementation‑ready reference for structuring edges, keeping large graphs legible, and complementing them with alternative visualisations & reports.

---

## 2  Minimal—but Expressive—Edge Taxonomy
| Layer | Edge types you almost always want | When to add | Why it pays off | Typical visual encoding |
|-------|-----------------------------------|-------------|-----------------|-------------------------|
| **Structural** | `is‑a` (class/subclass), `part‑of` (whole/segment) | All domains | Enables hierarchy views & roll‑ups | Thin, light‑gray tree edges |
| **Argumentative / Evidential** | `supports`, `contradicts`, `inconclusive` | Only where evidence logged | Fuels claim–evidence dashboards & conflict maps | Green / red / amber arrows |
| **Causal / Temporal** | `leads‑to`, `precedes` | Process flows, time‑series work | Makes causal chains & timelines explorable | Arrow‑heads + timeline overlay |
| **Similarity / Semantic** | `related‑to` (vector‑sim ≥ τ) | *Sparingly*—e.g. top‑k neighbours | Recommender pane without “hairball” | Dashed, faded edges |
| **Workflow / Status** | `task‑for`, `approved‑by` | Provenance & responsibility | Supports audit & Kanban reports | Coloured badges near node |

> **Rule of thumb:** expose no more than **three edge types** at any one zoom level; keep the full taxonomy in the data layer.

---

## 3  Techniques to Keep the Graph Legible
1. **Semantic zoom** – hide low‑priority edge types when zoomed out; reveal details on focus.
2. **Edge bundling** – group parallel edges into single splines with weight labels.
3. **Node aggregation** – cluster dense sub‑graphs into expandable meta‑nodes (Louvain / Leiden).
4. **Dynamic filtering** – side‑panel toggles by edge category, confidence, stage, or time window.
5. **Focus+context lenses** – fisheye/spotlight around cursor, dim rest by ~70 %.

---

## 4  Complementary Visualisations (Low‑Clutter, High‑Value)
| Need | View | Why it helps | Suggested lib / pattern |
|------|------|-------------|-------------------------|
| Lifecycle drift | **Timeline heat‑map** of concept frequency & edge churn | Shows topic birth, growth, decay | ECharts calendar, GitHub‑style sparklines |
| Evidence strength | **Stacked bar / radial gauge** per insight | Quick signal on confidence | Recharts `BarChart` |
| Flow of ideas | **Sankey** (origin → derivatives → insights) | Highlights bottlenecks & prolific sources | d3‑sankey |
| Responsibility | **Swim‑lane (Kanban)** board via `task‑for` edges | Focuses on action, not topology | React‑Beautiful‑DND |
| Similarity landscape | **UMAP / t‑SNE scatter** of node embeddings | Spot thematic clusters without edges | Plotly `scattergl` |
| Centrality spotlight | **Ranked list** + sparklines for degree / betweenness | Lists beat overcrowded labels | Plain HTML + charts.js |
| Conflict detection | **Chord diagram** of contradicting edges | Surfaces knowledge gaps immediately | d3‑chord |

---

## 5  Reports & Dashboards That Scale Better Than Raw Graphs
| Report | Key metrics | Refresh cadence | Audience |
|--------|-------------|-----------------|----------|
| **Insight Health** | Confidence, last‑verified, supports : contradicts | Weekly | Decision‑makers |
| **Concept Drift Alert** | Embedding shift %, edge churn, new contradictions | Nightly | Analysts |
| **Coverage Gap Matrix** | Domain × stage heat‑map (idea & insight counts) | Monthly | Research leads |
| **Top Influencers** | Nodes with highest weighted betweenness | Rolling | Community managers |
| **Time‑to‑Insight SLA** | Avg. hours from intake → insight | Per sprint | Ops / PMO |

---

## 6  Implementation Tips
* **Layered edge maps** – API param `edge_tier=[core|argument|semantic]` delivers only needed edges.
* **Graph‑in‑tile** – pre‑render large sub‑graphs as PNG thumbnails at low zoom; swap to SVG/Canvas on zoom‑in.
* **Edge importance score** – `importance = type_weight × relation_confidence × node_pagerank`; fade/drop edges below threshold.
* **Saved views / stories** – bookmark filtered graph states (e.g. *Risk hotspots Q3 2025*) via permalink.
* **Accessibility** – colour‑blind‑safe palettes; textual summaries in side panel.

---

### Bottom line
A trimmed, layered edge palette paired with faceted timelines, Sankeys, and metric dashboards transforms an ever‑growing knowledge base into actionable insight—without overwhelming users.

