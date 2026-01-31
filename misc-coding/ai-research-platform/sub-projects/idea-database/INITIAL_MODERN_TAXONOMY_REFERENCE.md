# Initial Modern Taxonomy Reference
## Reset to Default Taxonomy Configuration

**Purpose:** This document serves as the authoritative reference for the "default" modern taxonomy that was established in July 2025. Use this document to reset the taxonomy to its initial state if needed.

**Status:** ✅ **ACTIVE** - This is the default taxonomy configuration  
**Last Updated:** July 2025  
**Database Implementation:** Database-driven via `taxonomy_node_types` and `taxonomy_edge_types` tables

---

## 🎯 Overview

This taxonomy represents the modern, semantically-rich node and edge types designed for comprehensive knowledge graph representation. It replaces the legacy 4-type system (idea, entity, category, sender) with a sophisticated 9-node, 10-edge taxonomy.

### Design Principles
- **Semantic Richness**: Each type has clear, distinct meaning
- **Academic Foundation**: Based on knowledge representation best practices
- **LLM-Friendly**: Optimized for AI-powered content extraction
- **User-Editable**: Fully dynamic through web interface
- **Future-Proof**: Extensible for additional domain-specific types

---

## 📊 Node Types (9 Types)

### Core Knowledge Nodes

| **Type** | **Definition** | **Example** | **Use Cases** | **Attributes** |
|----------|----------------|-------------|---------------|----------------|
| **idea** | A distinct concept, proposal, or insight | "Federated Learning for Privacy" | Main concepts, hypotheses, theories | label, summary, source |
| **evidence** | Data, citation, or claim supporting/refuting an idea | "2023 Stanford study on FL efficacy" | Research findings, citations, data points | label, source, confidence |
| **method** | A process, technique, or approach | "Gradient Descent Optimization" | Algorithms, methodologies, processes | label, description, steps |
| **metric** | A quantitative or qualitative measure | "Accuracy: 94.5%", "Customer Satisfaction" | Performance indicators, measurements | label, value, units |

### Entity Nodes

| **Type** | **Definition** | **Example** | **Use Cases** | **Attributes** |
|----------|----------------|-------------|---------------|----------------|
| **person** | An individual human actor | "Geoffrey Hinton", "Ada Lovelace" | Researchers, authors, contributors | name, role, affiliation |
| **organization** | A group, company, or institution | "OpenAI", "MIT", "Google DeepMind" | Companies, universities, institutions | name, type, location |
| **technology** | A tool, platform, or system | "PyTorch", "Neo4j", "Kubernetes" | Software, platforms, technical tools | name, version, vendor |
| **event** | A notable occurrence or milestone | "NeurIPS 2023", "ChatGPT Launch" | Conferences, releases, milestones | name, date, location |

### Abstract Nodes

| **Type** | **Definition** | **Example** | **Use Cases** | **Attributes** |
|----------|----------------|-------------|---------------|----------------|
| **concept** | An abstract or domain-specific concept | "Machine Learning", "Quantum Computing" | High-level categories, domains | label, domain, scope |

---

## 🔗 Edge Types (10 Types)

### Structural Relationships

| **Type** | **Definition** | **Example** | **Directionality** | **Use Cases** |
|----------|----------------|-------------|-------------------|---------------|
| **is-a** | Class/subclass or type hierarchy | "Deep Learning is-a Machine Learning" | A → B | Taxonomic relationships, categorization |
| **part-of** | Whole/segment or membership | "Neural Network part-of AI System" | A → B | Component relationships, composition |

### Evidential Relationships

| **Type** | **Definition** | **Example** | **Directionality** | **Use Cases** |
|----------|----------------|-------------|-------------------|---------------|
| **supports** | Evidence or claim supports an idea/claim | "Study supports Hypothesis" | A → B | Research validation, proof |
| **contradicts** | Evidence or claim contradicts an idea/claim | "Data contradicts Previous Theory" | A → B | Refutation, counter-evidence |
| **inconclusive** | Evidence is inconclusive for an idea/claim | "Results inconclusive for Approach" | A → B | Uncertain findings, limitations |

### Process Relationships

| **Type** | **Definition** | **Example** | **Directionality** | **Use Cases** |
|----------|----------------|-------------|-------------------|---------------|
| **leads-to** | Causal or process flow | "Training leads-to Model Performance" | A → B | Causality, workflow, consequences |
| **precedes** | Temporal or sequential relationship | "Data Collection precedes Analysis" | A → B | Temporal order, prerequisites |

### Social Relationships

| **Type** | **Definition** | **Example** | **Directionality** | **Use Cases** |
|----------|----------------|-------------|-------------------|---------------|
| **task-for** | Workflow or responsibility assignment | "Researcher task-for Data Analysis" | A → B | Work assignments, responsibilities |
| **approved-by** | Approval or validation relationship | "Paper approved-by Review Committee" | A → B | Endorsements, validations |

### General Relationships

| **Type** | **Definition** | **Example** | **Directionality** | **Use Cases** |
|----------|----------------|-------------|-------------------|---------------|
| **related-to** | Semantic or similarity-based connection | "AI related-to Machine Learning" | A ↔ B | General associations, similarity |

---

## 🗃️ Database Schema Reference

### Node Types Table Structure
```sql
CREATE TABLE idea_database.taxonomy_node_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    color VARCHAR(20) NOT NULL,
    definition TEXT NOT NULL,
    example TEXT,
    attributes JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Edge Types Table Structure
```sql
CREATE TABLE idea_database.taxonomy_edge_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    color VARCHAR(20) NOT NULL,
    definition TEXT NOT NULL,
    example TEXT,
    directionality VARCHAR(20) NOT NULL DEFAULT 'A→B',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 🎨 Default Color Scheme

### Node Type Colors
```css
idea: #3B82F6         /* Blue - Primary concepts */
evidence: #10B981     /* Green - Supporting data */
method: #F59E0B       /* Amber - Processes */
metric: #F472B6       /* Pink - Measurements */
person: #8B5CF6       /* Purple - Individuals */
organization: #6366F1 /* Indigo - Institutions */
concept: #6B7280      /* Gray - Abstract concepts */
technology: #14B8A6   /* Teal - Technical tools */
event: #EF4444        /* Red - Notable occurrences */
```

### Edge Type Colors
```css
is-a: #6B7280         /* Gray - Hierarchical */
part-of: #A3A3A3      /* Light Gray - Compositional */
supports: #10B981     /* Green - Positive evidence */
contradicts: #EF4444  /* Red - Negative evidence */
inconclusive: #F59E0B /* Amber - Uncertain evidence */
leads-to: #3B82F6     /* Blue - Causal flow */
precedes: #6366F1     /* Indigo - Temporal order */
related-to: #14B8A6   /* Teal - General association */
task-for: #8B5CF6     /* Purple - Work assignment */
approved-by: #F472B6  /* Pink - Validation */
```

---

## 🔄 Reset Instructions

### To Reset Taxonomy to Default:

1. **Via Web Interface (Recommended):**
   - Go to Settings > Taxonomy tab
   - Delete all existing node and edge types
   - Add each type from this reference using the "Add" buttons
   - Use the exact names, definitions, examples, and colors listed above

2. **Via Database (Advanced Users):**
   ```sql
   -- Clear existing taxonomy
   DELETE FROM idea_database.taxonomy_edge_types;
   DELETE FROM idea_database.taxonomy_node_types;
   
   -- Insert default node types
   INSERT INTO idea_database.taxonomy_node_types (name, color, definition, example, attributes) VALUES
   ('idea', '#3B82F6', 'A distinct concept, proposal, or insight.', 'Federated Learning for Privacy', '{"label": "string"}'),
   ('evidence', '#10B981', 'Data, citation, or claim supporting or refuting an idea.', '2023 Stanford study on FL efficacy', '{"label": "string"}'),
   ('method', '#F59E0B', 'A process, technique, or approach.', 'Gradient Descent Optimization', '{"label": "string"}'),
   ('metric', '#F472B6', 'A quantitative or qualitative measure.', 'Accuracy: 94.5%', '{"label": "string"}'),
   ('person', '#8B5CF6', 'An individual human actor.', 'Geoffrey Hinton', '{"label": "string"}'),
   ('organization', '#6366F1', 'A group, company, or institution.', 'OpenAI', '{"label": "string"}'),
   ('concept', '#6B7280', 'An abstract or domain-specific concept.', 'Machine Learning', '{"label": "string"}'),
   ('technology', '#14B8A6', 'A tool, platform, or system.', 'PyTorch', '{"label": "string"}'),
   ('event', '#EF4444', 'A notable occurrence or milestone.', 'NeurIPS 2023', '{"label": "string"}');
   
   -- Insert default edge types
   INSERT INTO idea_database.taxonomy_edge_types (name, color, definition, example, directionality) VALUES
   ('is-a', '#6B7280', 'Class/subclass or type hierarchy.', 'Deep Learning is-a Machine Learning', 'directed'),
   ('part-of', '#A3A3A3', 'Whole/segment or membership.', 'Neural Network part-of AI System', 'directed'),
   ('supports', '#10B981', 'Evidence or claim supports an idea/claim.', 'Study supports Hypothesis', 'directed'),
   ('contradicts', '#EF4444', 'Evidence or claim contradicts an idea/claim.', 'Data contradicts Previous Theory', 'directed'),
   ('inconclusive', '#F59E0B', 'Evidence is inconclusive for an idea/claim.', 'Results inconclusive for Approach', 'directed'),
   ('leads-to', '#3B82F6', 'Causal or process flow.', 'Training leads-to Model Performance', 'directed'),
   ('precedes', '#6366F1', 'Temporal or sequential relationship.', 'Data Collection precedes Analysis', 'directed'),
   ('related-to', '#14B8A6', 'Semantic or similarity-based connection.', 'AI related-to Machine Learning', 'undirected'),
   ('task-for', '#8B5CF6', 'Workflow or responsibility assignment.', 'Researcher task-for Data Analysis', 'directed'),
   ('approved-by', '#F472B6', 'Approval or validation relationship.', 'Paper approved-by Review Committee', 'directed');
   ```

3. **Restart Services:**
   ```bash
   docker-compose restart ai_processor email_processor
   ```

---

## 📚 Related Documentation

- **Live Taxonomy Management**: Settings > Taxonomy tab in web interface
- **Knowledge Graph Taxonomy Reference**: `KNOWLEDGE_GRAPH_TAXONOMY_REFERENCE.md`
- **Implementation Details**: `KNOWLEDGE_GRAPH_IMPLEMENTATION_PLAN.md`
- **Complete System Reference**: `IDEA_DATABASE_COMPLETE_REFERENCE.md`

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | July 2025 | Initial modern taxonomy established |
| 1.1 | July 2025 | Database-driven implementation completed |

---

**Note:** This taxonomy is the foundation for all AI-powered content extraction, categorization, and knowledge graph visualization in the Idea Database platform. Changes to this taxonomy should be carefully considered and tested. 