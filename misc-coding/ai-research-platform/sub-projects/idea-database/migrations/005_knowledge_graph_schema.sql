-- Migration 005: Knowledge Graph Foundational Schema
-- Created: July 2025
--
-- Description: Sets up the core tables required for the knowledge graph feature,
-- including links for relationships, and placeholders for insights, gaps, and provenance.

BEGIN;

-- -----------------------------------------------------------------------------
-- 0. Helper Function for Timestamps
-- Ensure the 'updated_at' timestamp function exists before we use it.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- -----------------------------------------------------------------------------
-- 1. Links Table (Edges of the Graph)
-- This table stores the typed relationships between different nodes (ideas,
-- entities, etc.), forming the core of the knowledge graph.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idea_database.links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id UUID NOT NULL,
    target_node_id UUID NOT NULL,
    type VARCHAR(50) NOT NULL, -- e.g., 'supports', 'refutes', 'contains', 'sent_by'
    context TEXT, -- Optional: user-provided reason for the link
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add unique constraint to support ON CONFLICT in edge insertion
ALTER TABLE idea_database.links
    ADD CONSTRAINT unique_link_source_target_type UNIQUE (source_node_id, target_node_id, type);

CREATE INDEX IF NOT EXISTS idx_links_source_node_id ON idea_database.links(source_node_id);
CREATE INDEX IF NOT EXISTS idx_links_target_node_id ON idea_database.links(target_node_id);
CREATE INDEX IF NOT EXISTS idx_links_type ON idea_database.links(type);

-- Trigger to automatically update 'updated_at' timestamp
CREATE OR REPLACE TRIGGER set_timestamp
BEFORE UPDATE ON idea_database.links
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();


-- -----------------------------------------------------------------------------
-- 2. Insights Table
-- A placeholder for validated, non-obvious conclusions or syntheses that
-- emerge from connecting multiple ideas.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idea_database.insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    is_validated BOOLEAN DEFAULT FALSE,
    created_by_user_id UUID, -- Or link to a user table if you have one
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insights_is_validated ON idea_database.insights(is_validated);

-- Trigger to automatically update 'updated_at' timestamp
CREATE OR REPLACE TRIGGER set_timestamp
BEFORE UPDATE ON idea_database.insights
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();


-- -----------------------------------------------------------------------------
-- 3. Knowledge Gaps Table
-- A register for identified gaps in knowledge, unanswered questions, or
-- contradictions that require further investigation.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idea_database.knowledge_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'open', -- e.g., 'open', 'under_review', 'resolved'
    priority VARCHAR(50) DEFAULT 'medium',
    created_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_status ON idea_database.knowledge_gaps(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_priority ON idea_database.knowledge_gaps(priority);

-- Trigger to automatically update 'updated_at' timestamp
CREATE OR REPLACE TRIGGER set_timestamp
BEFORE UPDATE ON idea_database.knowledge_gaps
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();


-- -----------------------------------------------------------------------------
-- 4. Idea Source Provenance Table
-- Links an idea to a specific piece of evidence from a source document
-- or URL, providing a clear audit trail.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idea_database.idea_source_provenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID NOT NULL REFERENCES idea_database.ideas(id) ON DELETE CASCADE,
    -- We can't directly link to a source table if it's distributed (urls, attachments),
    -- so we store the source type and ID.
    source_type VARCHAR(50) NOT NULL, -- 'url', 'attachment', etc.
    source_id UUID NOT NULL,
    snippet TEXT, -- The specific highlighted text or excerpt
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_idea_source_provenance_idea_id ON idea_database.idea_source_provenance(idea_id);
CREATE INDEX IF NOT EXISTS idx_idea_source_provenance_source_id ON idea_database.idea_source_provenance(source_id);


COMMENT ON TABLE idea_database.links IS 'Stores the typed relationships (edges) between nodes in the knowledge graph.';
COMMENT ON TABLE idea_database.insights IS 'Stores validated conclusions and syntheses derived from the knowledge graph.';
COMMENT ON TABLE idea_database.knowledge_gaps IS 'A register for identified gaps in knowledge, serving as a catalyst for research.';
COMMENT ON TABLE idea_database.idea_source_provenance IS 'Links ideas to their specific evidentiary sources and excerpts.';

COMMIT; 