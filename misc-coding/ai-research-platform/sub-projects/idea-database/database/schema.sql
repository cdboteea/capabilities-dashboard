-- Idea Database Schema
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