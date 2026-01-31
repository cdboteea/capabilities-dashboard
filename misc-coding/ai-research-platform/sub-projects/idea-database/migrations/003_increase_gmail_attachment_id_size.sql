-- Migration 003: Increase Gmail Attachment ID field size
-- Fix for Gmail attachment IDs that can be 388+ characters long
-- Date: 2025-01-07
-- Description: Gmail attachment IDs from Google API can exceed 255 characters,
--              causing constraint violations and attachment processing failures.

-- Increase the field size to accommodate long Gmail attachment IDs
ALTER TABLE attachments 
ALTER COLUMN gmail_attachment_id TYPE VARCHAR(500);

-- Add comment for documentation
COMMENT ON COLUMN attachments.gmail_attachment_id IS 'Gmail attachment ID (up to 500 chars to handle long Google API IDs)';

-- Record migration completion
INSERT INTO schema_migrations (version, description, applied_at) 
VALUES ('003', 'Increase gmail_attachment_id field size to VARCHAR(500)', NOW())
ON CONFLICT (version) DO NOTHING; 