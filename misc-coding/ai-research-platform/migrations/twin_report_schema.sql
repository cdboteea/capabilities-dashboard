-- Twin-Report Knowledge Base Schema
-- Supports twin reports, quality control, and vector similarity search

-- Enable pgvector extension for similarity search
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Topics table - hierarchical research topics
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    parent_topic_id UUID REFERENCES topics(id),
    twin_set_id UUID NOT NULL, -- Groups related twin reports
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'covered', 'stale')),
    generation_method VARCHAR(20) DEFAULT 'api' CHECK (generation_method IN ('api', 'chat', 'local', 'hybrid')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Source documents (Google Docs, PDFs, chat exports)
CREATE TABLE source_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_type VARCHAR(20) NOT NULL CHECK (document_type IN ('google_doc', 'pdf', 'chat_export', 'manual')),
    external_id VARCHAR(255), -- Google Docs ID, file path, etc.
    url TEXT,
    title VARCHAR(500),
    raw_content TEXT,
    parsed_content TEXT,
    content_hash VARCHAR(64),
    parsed_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Articles table - each twin report or derived article
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic_id UUID NOT NULL REFERENCES topics(id),
    model_origin VARCHAR(50) NOT NULL, -- 'chatgpt-4o', 'gemini-2.0-ultra', 'deepseek-r1', etc.
    version INTEGER DEFAULT 1,
    title VARCHAR(500),
    body_md TEXT NOT NULL,
    embedding vector(1536), -- OpenAI embedding dimension
    source_type VARCHAR(20) DEFAULT 'api' CHECK (source_type IN ('api', 'chat_export', 'manual')),
    source_document_id UUID REFERENCES source_documents(id),
    word_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Article versions - immutable history
CREATE TABLE article_versions (
    id SERIAL PRIMARY KEY,
    article_id UUID NOT NULL REFERENCES articles(id),
    version INTEGER NOT NULL,
    title VARCHAR(500),
    body_md TEXT NOT NULL,
    source_document_id UUID REFERENCES source_documents(id),
    created_at TIMESTAMP DEFAULT NOW(),
    change_reason TEXT,
    UNIQUE(article_id, version)
);

-- Web archives - all referenced web content
CREATE TABLE web_archives (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL UNIQUE,
    title VARCHAR(500),
    content_markdown TEXT,
    content_html TEXT,
    archive_date TIMESTAMP DEFAULT NOW(),
    content_hash VARCHAR(64),
    source_service VARCHAR(50) DEFAULT 'direct', -- 'wayback', 'archive.today', etc.
    file_path TEXT, -- MinIO storage path
    metadata JSONB DEFAULT '{}'
);

-- Links between articles and web content
CREATE TABLE article_web_refs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID NOT NULL REFERENCES articles(id),
    web_archive_id UUID NOT NULL REFERENCES web_archives(id),
    reference_type VARCHAR(20) DEFAULT 'citation' CHECK (reference_type IN ('source', 'citation', 'background')),
    relevance_score FLOAT DEFAULT 0.5,
    context_snippet TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Twin diff results - JSON comparison output
CREATE TABLE twin_diff (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    twin_set_id UUID NOT NULL,
    article_1_id UUID NOT NULL REFERENCES articles(id),
    article_2_id UUID NOT NULL REFERENCES articles(id),
    diff_jsonb JSONB NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    summary TEXT
);

-- Gap scan results - AI suggestions for missing content
CREATE TABLE gap_scan_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    twin_set_id UUID NOT NULL,
    result_jsonb JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    human_reviewed BOOLEAN DEFAULT FALSE,
    priority_score FLOAT DEFAULT 0.5
);

-- Quality control checks
CREATE TABLE quality_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID NOT NULL REFERENCES articles(id),
    check_type VARCHAR(20) NOT NULL CHECK (check_type IN ('citation', 'fact', 'coherence', 'grammar')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pass', 'fail', 'needs_review', 'pending')),
    details_jsonb JSONB DEFAULT '{}',
    checked_at TIMESTAMP DEFAULT NOW(),
    checked_by VARCHAR(100),
    confidence_score FLOAT DEFAULT 0.0
);

-- Citation registry - extracted and verified citations
CREATE TABLE citation_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID NOT NULL REFERENCES articles(id),
    citation_text TEXT NOT NULL,
    source_url TEXT,
    web_archive_id UUID REFERENCES web_archives(id),
    verification_status VARCHAR(20) DEFAULT 'pending' CHECK (verification_status IN ('verified', 'broken', 'suspicious', 'pending')),
    last_checked TIMESTAMP DEFAULT NOW(),
    citation_type VARCHAR(20) DEFAULT 'general' CHECK (citation_type IN ('academic', 'news', 'official', 'general')),
    metadata JSONB DEFAULT '{}'
);

-- Subtopic suggestions - AI-generated research expansion
CREATE TABLE subtopic_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_topic_id UUID NOT NULL REFERENCES topics(id),
    suggested_title VARCHAR(500) NOT NULL,
    rationale TEXT,
    priority_score FLOAT DEFAULT 0.5,
    human_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    approved_by VARCHAR(100),
    approved_at TIMESTAMP
);

-- Events log - track system activities
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID REFERENCES articles(id),
    topic_id UUID REFERENCES topics(id),
    event_type VARCHAR(50) NOT NULL,
    details_jsonb JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT NOW(),
    user_id VARCHAR(100),
    source_service VARCHAR(50)
);

-- Workflow states - human-in-the-loop progress tracking
CREATE TABLE workflow_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic_id UUID NOT NULL REFERENCES topics(id),
    current_step VARCHAR(50) NOT NULL,
    assigned_to VARCHAR(100),
    due_date TIMESTAMP,
    metadata_jsonb JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused', 'cancelled'))
);

-- Indexes for performance
CREATE INDEX idx_topics_parent ON topics(parent_topic_id);
CREATE INDEX idx_topics_twin_set ON topics(twin_set_id);
CREATE INDEX idx_articles_topic ON articles(topic_id);
CREATE INDEX idx_articles_model ON articles(model_origin);
CREATE INDEX idx_articles_embedding ON articles USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_web_archives_url ON web_archives(url);
CREATE INDEX idx_web_archives_hash ON web_archives(content_hash);
CREATE INDEX idx_quality_checks_article ON quality_checks(article_id);
CREATE INDEX idx_quality_checks_status ON quality_checks(status);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_citation_registry_article ON citation_registry(article_id);

-- Full-text search indexes
CREATE INDEX idx_articles_fts ON articles USING gin(to_tsvector('english', body_md));
CREATE INDEX idx_web_archives_fts ON web_archives USING gin(to_tsvector('english', content_markdown));

-- Initial configuration data
INSERT INTO topics (id, title, description, twin_set_id, status) VALUES 
    ('00000000-0000-0000-0000-000000000001', 'Root Topic', 'System root for hierarchical topics', '00000000-0000-0000-0000-000000000001', 'covered');

COMMENT ON TABLE topics IS 'Hierarchical research topics with twin report tracking';
COMMENT ON TABLE articles IS 'Twin reports and derived articles with vector embeddings';
COMMENT ON TABLE web_archives IS 'Archived web content referenced in research';
COMMENT ON TABLE quality_checks IS 'Automated and manual quality control results';
COMMENT ON TABLE citation_registry IS 'Extracted citations with verification status'; 