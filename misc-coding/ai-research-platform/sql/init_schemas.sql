-- AI Research Platform Database Initialization
-- Creates schemas for all sub-projects and shared services

-- Create schemas for each sub-project
CREATE SCHEMA IF NOT EXISTS idea_database;
CREATE SCHEMA IF NOT EXISTS twin_report;
CREATE SCHEMA IF NOT EXISTS real_time_intel;
CREATE SCHEMA IF NOT EXISTS browser_agent;
CREATE SCHEMA IF NOT EXISTS shared_services;

-- Create shared web archives table (used by all modules)
CREATE TABLE IF NOT EXISTS shared_services.web_archives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    domain VARCHAR(255),
    title TEXT,
    content_hash VARCHAR(64) UNIQUE,
    markdown_content TEXT,
    raw_html TEXT,
    archive_path TEXT,
    source_module VARCHAR(50), -- idea_database, twin_report, etc.
    content_type VARCHAR(50), -- article, paper, documentation, etc.
    language VARCHAR(10) DEFAULT 'en',
    word_count INTEGER,
    extracted_entities JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create shared LLM interactions log
CREATE TABLE IF NOT EXISTS shared_services.llm_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(50) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    prompt_hash VARCHAR(64),
    prompt_text TEXT,
    response_text TEXT,
    token_count_input INTEGER,
    token_count_output INTEGER,
    processing_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create shared event log for cross-module communication
CREATE TABLE IF NOT EXISTS shared_services.event_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    source_module VARCHAR(50) NOT NULL,
    target_module VARCHAR(50),
    payload JSONB,
    processing_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_web_archives_url ON shared_services.web_archives(url);
CREATE INDEX IF NOT EXISTS idx_web_archives_content_hash ON shared_services.web_archives(content_hash);
CREATE INDEX IF NOT EXISTS idx_web_archives_source_module ON shared_services.web_archives(source_module);
CREATE INDEX IF NOT EXISTS idx_web_archives_created_at ON shared_services.web_archives(created_at);

CREATE INDEX IF NOT EXISTS idx_llm_interactions_service ON shared_services.llm_interactions(service_name);
CREATE INDEX IF NOT EXISTS idx_llm_interactions_model ON shared_services.llm_interactions(model_name);
CREATE INDEX IF NOT EXISTS idx_llm_interactions_created_at ON shared_services.llm_interactions(created_at);

CREATE INDEX IF NOT EXISTS idx_event_log_type ON shared_services.event_log(event_type);
CREATE INDEX IF NOT EXISTS idx_event_log_source ON shared_services.event_log(source_module);
CREATE INDEX IF NOT EXISTS idx_event_log_status ON shared_services.event_log(processing_status);

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA idea_database TO ai_user;
GRANT ALL PRIVILEGES ON SCHEMA twin_report TO ai_user;
GRANT ALL PRIVILEGES ON SCHEMA real_time_intel TO ai_user;
GRANT ALL PRIVILEGES ON SCHEMA browser_agent TO ai_user;
GRANT ALL PRIVILEGES ON SCHEMA shared_services TO ai_user;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA shared_services TO ai_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA shared_services TO ai_user; -- Idea Database Schema
-- Based on specification with 6 core categories and comprehensive entity extraction

-- Main ideas/entries table
CREATE TABLE IF NOT EXISTS idea_database.ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id VARCHAR(255) UNIQUE NOT NULL,
    message_id VARCHAR(255) NOT NULL,
    subject TEXT,
    sender_email VARCHAR(255),
    sender_name VARCHAR(255),
    received_date TIMESTAMP WITH TIME ZONE,
    processed_date TIMESTAMP WITH TIME ZONE,
    content_type VARCHAR(50), -- 'email', 'url', 'attachment', 'mixed'
    category VARCHAR(50), -- One of the 6 primary categories
    processing_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    ai_summary TEXT,
    original_content TEXT,
    cleaned_content TEXT,
    language VARCHAR(10) DEFAULT 'en',
    needs_manual_review BOOLEAN DEFAULT FALSE,
    priority_score DECIMAL(3,2), -- 0.00 to 1.00
    sentiment_score DECIMAL(3,2), -- -1.00 to 1.00
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- URLs and links extracted from content
CREATE TABLE IF NOT EXISTS idea_database.urls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID NOT NULL REFERENCES idea_database.ideas(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    domain VARCHAR(255),
    title TEXT,
    description TEXT,
    content_type VARCHAR(50), -- 'article', 'github', 'paper', 'documentation', etc.
    fetch_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'fetched', 'failed', 'blocked'
    archive_path TEXT, -- Path to archived markdown content
    word_count INTEGER,
    fetch_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- File attachments
CREATE TABLE IF NOT EXISTS idea_database.attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID NOT NULL REFERENCES idea_database.ideas(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_type VARCHAR(50), -- 'pdf', 'image', 'document', etc.
    file_size BIGINT,
    file_path TEXT NOT NULL, -- Path to stored file
    content_hash VARCHAR(64) UNIQUE, -- SHA-256 for deduplication
    extracted_text TEXT, -- For PDFs and documents
    processing_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Extracted entities
CREATE TABLE IF NOT EXISTS idea_database.entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID NOT NULL REFERENCES idea_database.ideas(id) ON DELETE CASCADE,
    entity_type VARCHAR(50), -- 'technology', 'person', 'company', 'repository', etc.
    entity_value TEXT NOT NULL,
    normalized_value TEXT, -- Cleaned/standardized version
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    context_snippet TEXT, -- Surrounding text for context
    source_type VARCHAR(20), -- 'content', 'url', 'attachment'
    source_id UUID, -- Reference to URL or attachment
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily processing summary
CREATE TABLE IF NOT EXISTS idea_database.processing_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    processing_date DATE NOT NULL,
    emails_processed INTEGER DEFAULT 0,
    urls_extracted INTEGER DEFAULT 0,
    entities_found INTEGER DEFAULT 0,
    categories_distribution JSONB,
    processing_time_minutes INTEGER,
    errors_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Search queries log
CREATE TABLE IF NOT EXISTS idea_database.search_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text TEXT NOT NULL,
    query_type VARCHAR(20), -- 'semantic', 'keyword', 'entity'
    results_count INTEGER,
    response_time_ms INTEGER,
    user_satisfaction INTEGER, -- 1-5 rating if provided
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ideas_category ON idea_database.ideas(category);
CREATE INDEX IF NOT EXISTS idx_ideas_status ON idea_database.ideas(processing_status);
CREATE INDEX IF NOT EXISTS idx_ideas_received_date ON idea_database.ideas(received_date);
CREATE INDEX IF NOT EXISTS idx_ideas_sender_email ON idea_database.ideas(sender_email);

CREATE INDEX IF NOT EXISTS idx_urls_domain ON idea_database.urls(domain);
CREATE INDEX IF NOT EXISTS idx_urls_content_type ON idea_database.urls(content_type);
CREATE INDEX IF NOT EXISTS idx_urls_fetch_status ON idea_database.urls(fetch_status);

CREATE INDEX IF NOT EXISTS idx_entities_type ON idea_database.entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_value ON idea_database.entities(entity_value);
CREATE INDEX IF NOT EXISTS idx_entities_confidence ON idea_database.entities(confidence_score);

CREATE INDEX IF NOT EXISTS idx_attachments_file_type ON idea_database.attachments(file_type);
CREATE INDEX IF NOT EXISTS idx_attachments_content_hash ON idea_database.attachments(content_hash);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_ideas_content_search ON idea_database.ideas USING gin(to_tsvector('english', cleaned_content));
CREATE INDEX IF NOT EXISTS idx_ideas_summary_search ON idea_database.ideas USING gin(to_tsvector('english', ai_summary));

-- =======================
-- Twin-Report KB Schema
-- =======================

-- Enable pgvector extension for similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Topics table - hierarchical research topics
CREATE TABLE IF NOT EXISTS twin_report.topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    parent_topic_id UUID REFERENCES twin_report.topics(id),
    twin_set_id UUID NOT NULL, -- Groups related twin reports
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'covered', 'stale')),
    generation_method VARCHAR(20) DEFAULT 'api' CHECK (generation_method IN ('api', 'chat', 'local', 'hybrid')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Articles table - each twin report or derived article
CREATE TABLE IF NOT EXISTS twin_report.articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID NOT NULL REFERENCES twin_report.topics(id),
    model_origin VARCHAR(50) NOT NULL, -- 'chatgpt-4o', 'gemini-2.0-ultra', 'deepseek-r1', etc.
    version INTEGER DEFAULT 1,
    title VARCHAR(500),
    body_md TEXT NOT NULL,
    embedding vector(1536), -- OpenAI embedding dimension
    source_type VARCHAR(20) DEFAULT 'api' CHECK (source_type IN ('api', 'chat_export', 'manual')),
    word_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Source documents (Google Docs, PDFs, chat exports)
CREATE TABLE IF NOT EXISTS twin_report.source_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type VARCHAR(20) NOT NULL CHECK (document_type IN ('google_doc', 'pdf', 'chat_export', 'manual')),
    external_id VARCHAR(255), -- Google Docs ID, file path, etc.
    url TEXT,
    title VARCHAR(500),
    raw_content TEXT,
    parsed_content TEXT,
    content_hash VARCHAR(64),
    parsed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Twin diff results - JSON comparison output
CREATE TABLE IF NOT EXISTS twin_report.twin_diff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    twin_set_id UUID NOT NULL,
    article_1_id UUID NOT NULL REFERENCES twin_report.articles(id),
    article_2_id UUID NOT NULL REFERENCES twin_report.articles(id),
    diff_jsonb JSONB NOT NULL,
    confidence_score DECIMAL(3,2) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    summary TEXT
);

-- Quality control checks
CREATE TABLE IF NOT EXISTS twin_report.quality_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES twin_report.articles(id),
    check_type VARCHAR(20) NOT NULL CHECK (check_type IN ('citation', 'fact', 'coherence', 'grammar')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pass', 'fail', 'needs_review', 'pending')),
    details_jsonb JSONB DEFAULT '{}',
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confidence_score DECIMAL(3,2) DEFAULT 0.0
);

-- Citation registry - extracted and verified citations
CREATE TABLE IF NOT EXISTS twin_report.citation_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES twin_report.articles(id),
    citation_text TEXT NOT NULL,
    source_url TEXT,
    verification_status VARCHAR(20) DEFAULT 'pending' CHECK (verification_status IN ('verified', 'broken', 'suspicious', 'pending')),
    last_checked TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    citation_type VARCHAR(20) DEFAULT 'general' CHECK (citation_type IN ('academic', 'news', 'official', 'general')),
    metadata JSONB DEFAULT '{}'
);

-- Workflow states - human-in-the-loop progress tracking
CREATE TABLE IF NOT EXISTS twin_report.workflow_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID NOT NULL REFERENCES twin_report.topics(id),
    current_step VARCHAR(50) NOT NULL,
    assigned_to VARCHAR(100),
    due_date TIMESTAMP WITH TIME ZONE,
    metadata_jsonb JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused', 'cancelled'))
);

-- Indexes for Twin-Report performance
CREATE INDEX IF NOT EXISTS idx_twin_topics_parent ON twin_report.topics(parent_topic_id);
CREATE INDEX IF NOT EXISTS idx_twin_topics_twin_set ON twin_report.topics(twin_set_id);
CREATE INDEX IF NOT EXISTS idx_twin_topics_status ON twin_report.topics(status);

CREATE INDEX IF NOT EXISTS idx_twin_articles_topic ON twin_report.articles(topic_id);
CREATE INDEX IF NOT EXISTS idx_twin_articles_model ON twin_report.articles(model_origin);
CREATE INDEX IF NOT EXISTS idx_twin_articles_source_type ON twin_report.articles(source_type);
CREATE INDEX IF NOT EXISTS idx_twin_articles_embedding ON twin_report.articles USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_twin_quality_checks_article ON twin_report.quality_checks(article_id);
CREATE INDEX IF NOT EXISTS idx_twin_quality_checks_status ON twin_report.quality_checks(status);

CREATE INDEX IF NOT EXISTS idx_twin_citation_registry_article ON twin_report.citation_registry(article_id);
CREATE INDEX IF NOT EXISTS idx_twin_citation_registry_status ON twin_report.citation_registry(verification_status);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_twin_articles_fts ON twin_report.articles USING gin(to_tsvector('english', body_md));
CREATE INDEX IF NOT EXISTS idx_twin_articles_title_fts ON twin_report.articles USING gin(to_tsvector('english', title));

-- Initial configuration data
INSERT INTO twin_report.topics (id, title, description, twin_set_id, status) VALUES 
    ('00000000-0000-0000-0000-000000000001', 'Root Topic', 'System root for hierarchical topics', '00000000-0000-0000-0000-000000000001', 'covered')
ON CONFLICT (id) DO NOTHING; 