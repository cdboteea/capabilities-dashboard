-- Phase 1 Migration: Enhanced Attachment Storage
-- Adds Google Drive integration and markdown content storage capabilities

-- Add Google Drive integration columns to attachments table
ALTER TABLE idea_database.attachments 
ADD COLUMN IF NOT EXISTS drive_file_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS drive_file_url TEXT,
ADD COLUMN IF NOT EXISTS markdown_content TEXT,
ADD COLUMN IF NOT EXISTS conversion_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS conversion_error TEXT,
ADD COLUMN IF NOT EXISTS storage_type VARCHAR(20) DEFAULT 'local';

-- Add Google Drive integration columns to URLs table
ALTER TABLE idea_database.urls
ADD COLUMN IF NOT EXISTS markdown_content TEXT,
ADD COLUMN IF NOT EXISTS processing_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS processing_error TEXT,
ADD COLUMN IF NOT EXISTS content_length INTEGER,
ADD COLUMN IF NOT EXISTS processed_date TIMESTAMP WITH TIME ZONE;

-- Create new table for file conversion jobs
CREATE TABLE IF NOT EXISTS idea_database.conversion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attachment_id UUID REFERENCES idea_database.attachments(id) ON DELETE CASCADE,
    url_id UUID REFERENCES idea_database.urls(id) ON DELETE CASCADE,
    job_type VARCHAR(20) NOT NULL, -- 'pdf_conversion', 'docx_conversion', 'url_processing', etc.
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    priority INTEGER DEFAULT 5, -- 1-10, lower is higher priority
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure only one of attachment_id or url_id is set
    CONSTRAINT conversion_jobs_single_target CHECK (
        (attachment_id IS NOT NULL AND url_id IS NULL) OR
        (attachment_id IS NULL AND url_id IS NOT NULL)
    )
);

-- Create Google Drive service configuration table
CREATE TABLE IF NOT EXISTS idea_database.drive_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_account_email VARCHAR(255) NOT NULL,
    drive_folder_id VARCHAR(255) NOT NULL,
    folder_name VARCHAR(255) NOT NULL,
    quota_bytes BIGINT DEFAULT 15000000000, -- 15GB default
    used_bytes BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_attachments_drive_file_id ON idea_database.attachments(drive_file_id);
CREATE INDEX IF NOT EXISTS idx_attachments_conversion_status ON idea_database.attachments(conversion_status);
CREATE INDEX IF NOT EXISTS idx_attachments_storage_type ON idea_database.attachments(storage_type);

CREATE INDEX IF NOT EXISTS idx_urls_processing_status ON idea_database.urls(processing_status);
CREATE INDEX IF NOT EXISTS idx_urls_processed_date ON idea_database.urls(processed_date);

CREATE INDEX IF NOT EXISTS idx_conversion_jobs_status ON idea_database.conversion_jobs(status);
CREATE INDEX IF NOT EXISTS idx_conversion_jobs_type ON idea_database.conversion_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_conversion_jobs_priority ON idea_database.conversion_jobs(priority);
CREATE INDEX IF NOT EXISTS idx_conversion_jobs_created_at ON idea_database.conversion_jobs(created_at);

-- Full-text search indexes for markdown content
CREATE INDEX IF NOT EXISTS idx_attachments_markdown_search ON idea_database.attachments USING gin(to_tsvector('english', markdown_content));
CREATE INDEX IF NOT EXISTS idx_urls_markdown_search ON idea_database.urls USING gin(to_tsvector('english', markdown_content));

-- Update processing summary to track new metrics
ALTER TABLE idea_database.processing_summary
ADD COLUMN IF NOT EXISTS attachments_processed INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS attachments_converted INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS urls_processed INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS drive_storage_used_mb INTEGER DEFAULT 0; 