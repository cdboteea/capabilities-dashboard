-- Migration 009: Modern Knowledge Graph Core Tables
-- Created: January 2025
--
-- Description: Creates the core tables required for the modern knowledge graph system
-- that the AI processor expects: knowledge_graph_nodes, knowledge_graph_edges, source_emails

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Source Emails Table - Modern email storage for knowledge graph
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idea_database.source_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gmail_message_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT,
    sender_email VARCHAR(255),
    sender_name VARCHAR(255),
    received_date TIMESTAMPTZ,
    processed_date TIMESTAMPTZ,
    content_type VARCHAR(50) DEFAULT 'email',
    processing_status VARCHAR(20) DEFAULT 'pending',
    original_content TEXT,
    cleaned_content TEXT,
    ai_summary TEXT,
    language VARCHAR(10) DEFAULT 'en',
    priority_score DECIMAL(3,2),
    sentiment_score DECIMAL(3,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 2. Knowledge Graph Nodes - Modern entity storage
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idea_database.knowledge_graph_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    node_type VARCHAR(100) NOT NULL, -- References taxonomy_node_types.name
    description TEXT,
    properties JSONB DEFAULT '{}',
    source_id UUID, -- References source_emails.id or other sources
    source_type VARCHAR(50) DEFAULT 'email', -- 'email', 'url', 'attachment', etc.
    extraction_confidence DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 3. Knowledge Graph Edges - Modern relationship storage
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idea_database.knowledge_graph_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id UUID NOT NULL REFERENCES idea_database.knowledge_graph_nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES idea_database.knowledge_graph_nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(100) NOT NULL, -- References taxonomy_edge_types.name
    weight DECIMAL(3,2) DEFAULT 1.0,
    context TEXT,
    source_id UUID, -- References source_emails.id or other sources
    extraction_confidence DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 4. Indexes for Performance
-- -----------------------------------------------------------------------------

-- Source emails indexes
CREATE INDEX IF NOT EXISTS idx_source_emails_message_id ON idea_database.source_emails(gmail_message_id);
CREATE INDEX IF NOT EXISTS idx_source_emails_sender ON idea_database.source_emails(sender_email);
CREATE INDEX IF NOT EXISTS idx_source_emails_received_date ON idea_database.source_emails(received_date);
CREATE INDEX IF NOT EXISTS idx_source_emails_status ON idea_database.source_emails(processing_status);

-- Knowledge graph nodes indexes
CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON idea_database.knowledge_graph_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_source ON idea_database.knowledge_graph_nodes(source_id);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_name ON idea_database.knowledge_graph_nodes(name);

-- Knowledge graph edges indexes
CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON idea_database.knowledge_graph_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON idea_database.knowledge_graph_edges(target_node_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_type ON idea_database.knowledge_graph_edges(edge_type);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_kg_nodes_name_search ON idea_database.knowledge_graph_nodes USING gin(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_source_emails_content_search ON idea_database.source_emails USING gin(to_tsvector('english', cleaned_content));

-- -----------------------------------------------------------------------------
-- 5. Foreign Key Constraints (Optional - for referential integrity)
-- -----------------------------------------------------------------------------

-- Add foreign key to link nodes to taxonomy types (soft constraint)
-- Note: We don't enforce this as FK because taxonomy is user-editable
-- ALTER TABLE idea_database.knowledge_graph_nodes
--     ADD CONSTRAINT fk_kg_nodes_taxonomy 
--     FOREIGN KEY (node_type) REFERENCES idea_database.taxonomy_node_types(name);

-- Add foreign key to link edges to taxonomy types (soft constraint)
-- ALTER TABLE idea_database.knowledge_graph_edges
--     ADD CONSTRAINT fk_kg_edges_taxonomy 
--     FOREIGN KEY (edge_type) REFERENCES idea_database.taxonomy_edge_types(name);

-- -----------------------------------------------------------------------------
-- 6. Comments for Documentation
-- -----------------------------------------------------------------------------

COMMENT ON TABLE idea_database.source_emails IS 'Modern email storage for knowledge graph processing pipeline';
COMMENT ON TABLE idea_database.knowledge_graph_nodes IS 'Core entities extracted from sources using modern taxonomy';
COMMENT ON TABLE idea_database.knowledge_graph_edges IS 'Semantic relationships between knowledge graph nodes';

COMMENT ON COLUMN idea_database.knowledge_graph_nodes.node_type IS 'References taxonomy_node_types.name (idea, evidence, method, etc.)';
COMMENT ON COLUMN idea_database.knowledge_graph_edges.edge_type IS 'References taxonomy_edge_types.name (supports, contradicts, etc.)';

COMMIT; 