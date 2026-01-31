-- Migration 007: Taxonomy Node and Edge Types for Knowledge Graph
-- Created: July 2025

BEGIN;

-- Table for node types (e.g., Idea, Evidence, Method, etc.)
CREATE TABLE IF NOT EXISTS idea_database.taxonomy_node_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL, -- e.g., 'Idea', 'Evidence'
    color VARCHAR(20) NOT NULL,        -- e.g., '#3B82F6'
    definition TEXT NOT NULL,
    example TEXT,
    attributes JSONB,                  -- e.g., {"label": "string", "summary": "string"}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table for edge types (e.g., supports, contradicts, etc.)
CREATE TABLE IF NOT EXISTS idea_database.taxonomy_edge_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL, -- e.g., 'supports', 'contradicts'
    color VARCHAR(20) NOT NULL,        -- e.g., '#6B7280'
    definition TEXT NOT NULL,
    example TEXT,
    directionality VARCHAR(20) NOT NULL DEFAULT 'A→B', -- e.g., 'A→B', 'A↔B'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Pre-populate node types
INSERT INTO idea_database.taxonomy_node_types (name, color, definition, example, attributes)
VALUES
  ('idea', '#3B82F6', 'A distinct concept, proposal, or insight.', 'Federated Learning', '{"label": "string"}'),
  ('entity', '#10B981', 'A real-world object, person, or organization.', 'Ada Lovelace', '{"label": "string"}'),
  ('category', '#F59E0B', 'A grouping or classification for ideas/entities.', 'Machine Learning', '{"label": "string"}'),
  ('sender', '#8B5CF6', 'A person or system that sends information.', 'OpenAI', '{"label": "string"}');

-- Pre-populate edge types
INSERT INTO idea_database.taxonomy_edge_types (name, color, definition, example, directionality)
VALUES
  ('contains', '#6B7280', 'Indicates that one node contains another.', 'Idea contains Entity', 'directed'),
  ('related_to', '#EF4444', 'Semantic or similarity-based connection.', 'Concept related-to Concept', 'undirected'),
  ('sent_by', '#8B5CF6', 'Indicates the sender of an idea or entity.', 'Idea sent_by Sender', 'directed'),
  ('categorized_as', '#F59E0B', 'Indicates the category of a node.', 'Idea categorized_as Category', 'directed');

COMMIT; 