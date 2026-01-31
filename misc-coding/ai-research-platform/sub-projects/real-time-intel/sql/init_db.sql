-- Real-Time Intel Database Initialization
-- This script creates the basic database schema for all services

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- NEWS SOURCES AND ARTICLES
-- ============================================================================

-- Sources table for source management
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    quality_score FLOAT DEFAULT 0.5,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- News articles
CREATE TABLE IF NOT EXISTS news_articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    content TEXT,
    url TEXT UNIQUE NOT NULL,
    source_id UUID REFERENCES sources(id),
    published_date TIMESTAMP WITH TIME ZONE,
    processed_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    quality_score FLOAT DEFAULT 0.0,
    sentiment_score FLOAT DEFAULT 0.0,
    categories TEXT[],
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- EVENTS AND PROCESSING
-- ============================================================================

-- News events from event processor
CREATE TABLE IF NOT EXISTS news_events (  
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    source_url TEXT,
    published_date TIMESTAMP WITH TIME ZONE,
    event_type VARCHAR(50),
    priority INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'pending',
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SENTIMENT ANALYSIS
-- ============================================================================

-- Sentiment analysis results
CREATE TABLE IF NOT EXISTS sentiment_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES news_events(id),
    article_id UUID REFERENCES news_articles(id),
    sentiment_score FLOAT NOT NULL,
    sentiment_label VARCHAR(20) NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    emotion_scores JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- MACRO ECONOMIC DATA
-- ============================================================================

-- Macro economic indicators
CREATE TABLE IF NOT EXISTS macro_indicators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    indicator_name VARCHAR(100) NOT NULL,
    value FLOAT NOT NULL,
    unit VARCHAR(20),
    frequency VARCHAR(20),
    source VARCHAR(100),
    date_value DATE NOT NULL,  
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- FINANCIAL DATA
-- ============================================================================

-- Price data
CREATE TABLE IF NOT EXISTS price_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    price FLOAT NOT NULL,
    volume BIGINT,
    market_cap FLOAT,
    price_date DATE NOT NULL,
    source VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Holdings data
CREATE TABLE IF NOT EXISTS holdings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    shares FLOAT NOT NULL,
    avg_cost FLOAT,
    current_value FLOAT,
    portfolio_name VARCHAR(100),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- ALERTS AND NOTIFICATIONS
-- ============================================================================

-- Alert rules
CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Alert history
CREATE TABLE IF NOT EXISTS alert_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID REFERENCES alert_rules(id),
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    event_data JSONB,
    actions_taken JSONB,
    status VARCHAR(20) DEFAULT 'sent'
);

-- ============================================================================
-- HISTORICAL ANALYSIS
-- ============================================================================

-- Historical patterns
CREATE TABLE IF NOT EXISTS historical_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_name VARCHAR(255) NOT NULL,
    description TEXT,
    confidence_score FLOAT,
    historical_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDICES FOR PERFORMANCE
-- ============================================================================

-- Performance indices
CREATE INDEX IF NOT EXISTS idx_news_articles_published_date ON news_articles(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_source_id ON news_articles(source_id);
CREATE INDEX IF NOT EXISTS idx_news_articles_quality_score ON news_articles(quality_score DESC);

CREATE INDEX IF NOT EXISTS idx_news_events_event_id ON news_events(event_id);
CREATE INDEX IF NOT EXISTS idx_news_events_published_date ON news_events(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_news_events_status ON news_events(status);

CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_event_id ON sentiment_analysis(event_id);
CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_article_id ON sentiment_analysis(article_id);

CREATE INDEX IF NOT EXISTS idx_macro_indicators_name_date ON macro_indicators(indicator_name, date_value DESC);
CREATE INDEX IF NOT EXISTS idx_price_data_symbol_date ON price_data(symbol, price_date DESC);
CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON holdings(symbol);

CREATE INDEX IF NOT EXISTS idx_alert_rules_active ON alert_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_alert_history_rule_id ON alert_history(rule_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_triggered_at ON alert_history(triggered_at DESC);

-- ============================================================================
-- SAMPLE DATA (Optional)
-- ============================================================================

-- Insert some sample sources
INSERT INTO sources (name, url, source_type, quality_score) VALUES
    ('Reuters Finance', 'https://reuters.com/finance', 'news', 0.9),
    ('Bloomberg', 'https://bloomberg.com', 'news', 0.95),
    ('Yahoo Finance', 'https://finance.yahoo.com', 'news', 0.8),
    ('MarketWatch', 'https://marketwatch.com', 'news', 0.75)
ON CONFLICT DO NOTHING;

-- Insert sample alert rule
INSERT INTO alert_rules (name, description, conditions, actions) VALUES
    ('High Volatility Alert', 
     'Alert when stock price moves more than 5% in a day',
     '{"price_change_percent": {"gt": 5}}',
     '{"email": {"enabled": true}, "push": {"enabled": true}}')
ON CONFLICT DO NOTHING;

COMMIT; 