-- 004_x_post_support.sql
-- Adds tables for X (Twitter) post storage, media mapping, API usage quota
-- and augments existing urls table.

BEGIN;

-- 1. X posts core table -----------------------------------------------------
CREATE TABLE IF NOT EXISTS idea_database.x_posts (
    tweet_id           BIGINT PRIMARY KEY,
    url_id             UUID NOT NULL REFERENCES idea_database.urls(id) ON DELETE CASCADE,
    data               JSONB NOT NULL,               -- raw + normalized tweet info
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Media mapping table ----------------------------------------------------
CREATE TABLE IF NOT EXISTS idea_database.x_media (
    media_key          TEXT PRIMARY KEY,
    tweet_id           BIGINT NOT NULL REFERENCES idea_database.x_posts(tweet_id) ON DELETE CASCADE,
    drive_file_id      TEXT,                          -- Google Drive file id after upload
    type               TEXT,                          -- photo | video | animated_gif
    width              INT,
    height             INT,
    duration_ms        INT,
    metadata           JSONB,                         -- any extra fields
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Monthly API usage tracker ---------------------------------------------
CREATE TABLE IF NOT EXISTS idea_database.x_api_usage (
    month             TEXT PRIMARY KEY,               -- e.g. '2025-07'
    calls_used        INT  NOT NULL DEFAULT 0,
    calls_limit       INT  NOT NULL DEFAULT 100,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Augment urls table -----------------------------------------------------
ALTER TABLE idea_database.urls
    ADD COLUMN IF NOT EXISTS api_used BOOLEAN NOT NULL DEFAULT false;

COMMIT; 