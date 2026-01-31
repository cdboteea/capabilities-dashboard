# Knowledge Graph Taxonomy Reference

## Introduction
This document defines the core taxonomy for the Idea Database knowledge graph. It serves as the authoritative reference for all node (entity) and edge (relationship) types, their definitions, criteria for inclusion, and extraction guidelines. 

**🚀 ACTIVE STATUS:** Database-driven taxonomy system with LLM-based categorization  
**Last Updated:** July 2025

> **✅ IMPLEMENTED:** The taxonomy is now fully database-driven and user-editable via the Settings > Taxonomy tab. All services (AI processor, email processor) dynamically fetch taxonomy from the database. The static YAML file system has been deprecated.

### 🔄 System Architecture
- **Database-Driven**: All taxonomy stored in `taxonomy_node_types` and `taxonomy_edge_types` tables
- **LLM-Powered**: Email categorization uses Mac Studio endpoint with dynamic taxonomy
- **Real-Time Updates**: Changes via web interface instantly reflected across all services
- **Reset Available**: Use `INITIAL_MODERN_TAXONOMY_REFERENCE.md` to restore defaults

---

## Node Types

| Kind         | Definition                                      | Example(s)                | Criteria for Inclusion                | Typical Attributes           |
|--------------|-------------------------------------------------|---------------------------|---------------------------------------|------------------------------|
| Idea         | A distinct concept, proposal, or insight        | "Federated Learning"      | Clearly stated, self-contained idea   | label, summary, source       |
| Evidence     | Data, citation, or claim supporting/refuting    | "2023 study on X"         | Cited as support or contradiction     | label, source, confidence    |
| Method       | A process, technique, or approach               | "Gradient Descent"        | Described as a repeatable process     | label, description           |
| Metric       | Quantitative or qualitative measure             | "Accuracy", "F1 Score"    | Used to evaluate or compare           | label, value, units          |
| Person       | Individual human actor                          | "Ada Lovelace"            | Named in text, relevant to context    | name, role, affiliation      |
| Organization | Group, company, or institution                  | "OpenAI", "MIT"           | Named as an entity in the text        | name, type, location         |
| Concept      | Abstract or domain-specific concept             | "Machine Learning"        | Central to the topic or discussion    | label, domain                |
| Technology   | Tool, platform, or system                       | "PyTorch", "Neo4j"        | Used or referenced in the text        | name, version, vendor        |
| Event        | Notable occurrence or milestone                 | "NeurIPS 2023"            | Dated or described as an event        | name, date, location         |

---

## Edge Types

| Relation        | Definition                                         | Example(s)                                 | Criteria for Establishment                | Directionality         |
|-----------------|----------------------------------------------------|--------------------------------------------|-------------------------------------------|------------------------|
| is-a            | Class/subclass or type hierarchy                   | "Metric is-a Concept"                     | Follows domain hierarchy                  | A → B                  |
| part-of         | Whole/segment or membership                        | "Method part-of Idea"                     | Describes composition or membership       | A → B                  |
| supports        | Evidence or claim supports an idea/claim           | "Evidence supports Idea"                   | Cited as support in text                  | A → B                  |
| contradicts     | Evidence or claim contradicts an idea/claim        | "Evidence contradicts Idea"                | Cited as contradiction in text            | A → B                  |
| inconclusive    | Evidence is inconclusive for an idea/claim         | "Evidence inconclusive for Idea"           | Cited as inconclusive in text             | A → B                  |
| leads-to        | Causal or process flow                             | "Method leads-to Metric"                   | Describes a causal/process relationship   | A → B                  |
| precedes        | Temporal or sequential relationship                | "Event precedes Event"                     | Describes time/order                      | A → B                  |
| related-to      | Semantic or similarity-based connection            | "Concept related-to Concept"               | Similarity above threshold, contextually  | A ↔ B (bidirectional)  |
| task-for        | Workflow or responsibility assignment              | "Person task-for Method"                   | Assigned responsibility in context        | A → B                  |
| approved-by     | Approval or validation relationship                | "Metric approved-by Organization"          | Explicit approval/validation in text      | A → B                  |

---

## Extraction Criteria
- **Nodes:** Extract when the entity is explicitly named, central to the discussion, or referenced as a key actor/concept.
- **Edges:** Extract when the relationship is clearly stated, implied by context, or matches the taxonomy definitions above.
- **Confidence:** Assign a confidence score to each edge based on LLM certainty; edges below 0.8 go to review queue.
- **Directionality:** Follow the direction as defined above; bidirectional for `related-to`.
- **Attributes:** Include all available attributes (e.g., source, date, value) for each node/edge.

---

## Prompt Guidance for LLM Extraction
- Always use this taxonomy as the schema for extraction.
- Output JSON with two arrays: `nodes` and `edges`.
- For each node: include `tmp_id`, `label`, `kind`, and `attrs`.
- For each edge: include `source_tmp`, `target_tmp`, `relation`, and `confidence`.
- Example prompt:
  > Extract all nodes and edges from the following text according to the taxonomy below. Respond ONLY with a JSON object containing `nodes` and `edges` arrays. Use the definitions and criteria provided.

---

## Versioning & Change Log
- **v1.2 (2025-07-15):** Taxonomy is now dynamic, user-editable, and always in sync with the UI and database.
- **v1.1 (2025-07-15):** UI help modal now fully taxonomy-aligned and accessible in the dashboard.
- **v1.0 (2024-06-15):** Initial taxonomy established from LLM processing specs and unified pipeline documents.

---

**This document is the single source of truth for all knowledge graph extraction, storage, and visualization in the Idea Database platform.** 