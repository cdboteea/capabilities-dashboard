-- Real-Time Intel Database Schema
-- Financial Intelligence Platform - 13 Core Tables
-- Created: 2025-01-22

-- Enable UUID extension for unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. NEWS SOURCES - Dynamic source management with evaluation scores
-- ============================================================================
CREATE TABLE news_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'news_site', 'rss_feed', 'api', 'social_media'
    categories TEXT[], -- ['earnings', 'mergers', 'markets', 'technology', 'politics']
    languages TEXT[] DEFAULT '{"en"}',
    
    -- Source configuration
    crawl_frequency INTEGER DEFAULT 300, -- seconds
    max_articles_per_crawl INTEGER DEFAULT 50,
    rate_limit DECIMAL(4,2) DEFAULT 2.0, -- seconds between requests
    
    -- Quality metrics
    quality_score DECIMAL(4,3) DEFAULT 0.0, -- 0.0 to 1.0
    reliability_score DECIMAL(4,3) DEFAULT 0.0,
    timeliness_score DECIMAL(4,3) DEFAULT 0.0,
    
    -- Status and metadata
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'paused', 'retired', 'failed'
    priority INTEGER DEFAULT 5, -- 1 (highest) to 10 (lowest)
    
    -- Extraction configuration
    extraction_rules JSONB, -- CSS selectors and extraction rules
    authentication_required BOOLEAN DEFAULT FALSE,
    paywall_detected BOOLEAN DEFAULT FALSE,
    
    -- Tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_crawl_at TIMESTAMP WITH TIME ZONE,
    last_successful_crawl_at TIMESTAMP WITH TIME ZONE,
    
    -- Performance metrics
    total_crawls INTEGER DEFAULT 0,
    successful_crawls INTEGER DEFAULT 0,
    failed_crawls INTEGER DEFAULT 0,
    avg_response_time DECIMAL(6,2), -- milliseconds
    avg_articles_per_crawl DECIMAL(6,2)
);

-- ============================================================================
-- 2. SOURCE EVALUATIONS - LLM-based quality assessments
-- ============================================================================
CREATE TABLE source_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id VARCHAR(100) NOT NULL REFERENCES news_sources(source_id),
    
    -- Evaluation details
    evaluation_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    evaluator VARCHAR(50) NOT NULL, -- 'qwen_3_72b', 'human', 'automated'
    evaluation_version VARCHAR(20) DEFAULT '1.0',
    
    -- Quality scores (0.0 to 1.0)
    accuracy_score DECIMAL(4,3) NOT NULL,
    relevance_score DECIMAL(4,3) NOT NULL,
    timeliness_score DECIMAL(4,3) NOT NULL,
    completeness_score DECIMAL(4,3) NOT NULL,
    objectivity_score DECIMAL(4,3) NOT NULL,
    
    -- Overall assessment
    overall_score DECIMAL(4,3) NOT NULL,
    recommendation VARCHAR(20) NOT NULL, -- 'keep', 'monitor', 'retire'
    confidence DECIMAL(4,3) NOT NULL,
    
    -- Detailed analysis
    strengths TEXT[],
    weaknesses TEXT[],
    improvement_suggestions TEXT[],
    
    -- LLM reasoning
    reasoning_log TEXT,
    evaluation_prompt TEXT,
    
    -- Sample analysis
    articles_analyzed INTEGER DEFAULT 0,
    sample_period_days INTEGER DEFAULT 7,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 3. SOURCE RETIREMENT - Retired source documentation
-- ============================================================================
CREATE TABLE source_retirement (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id VARCHAR(100) NOT NULL,
    original_source_data JSONB NOT NULL, -- Full source record backup
    
    -- Retirement details
    retirement_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    retirement_reason VARCHAR(100) NOT NULL,
    final_quality_score DECIMAL(4,3),
    
    -- Performance history
    total_lifetime_crawls INTEGER,
    lifetime_success_rate DECIMAL(5,3),
    avg_quality_score DECIMAL(4,3),
    
    -- Replacement information
    replacement_sources TEXT[],
    migration_notes TEXT,
    
    -- Archival
    archived_articles_count INTEGER DEFAULT 0,
    archive_location TEXT,
    
    retired_by VARCHAR(100), -- 'automated', 'manual', 'admin'
    notes TEXT
);

-- ============================================================================
-- 4. MACRO DATA SOURCES - Economic calendar and data feeds
-- ============================================================================
CREATE TABLE macro_data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'economic_calendar', 'fed_data', 'earnings_calendar'
    
    -- API configuration
    api_endpoint TEXT,
    api_key_required BOOLEAN DEFAULT FALSE,
    rate_limit INTEGER DEFAULT 60, -- requests per minute
    
    -- Data characteristics
    update_frequency VARCHAR(50), -- 'real_time', 'daily', 'weekly', 'monthly'
    data_categories TEXT[], -- ['inflation', 'employment', 'gdp', 'interest_rates']
    geographic_coverage TEXT[], -- ['US', 'EU', 'global']
    
    -- Quality and reliability
    data_quality_score DECIMAL(4,3) DEFAULT 0.0,
    historical_accuracy DECIMAL(4,3) DEFAULT 0.0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'active',
    last_update_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 5. RAW EVENTS - All ingested content before processing
-- ============================================================================
CREATE TABLE raw_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Source information
    source_id VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    crawl_job_id VARCHAR(255),
    
    -- Content
    title TEXT,
    content TEXT,
    url TEXT,
    
    -- Metadata
    raw_metadata JSONB,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_date TIMESTAMP WITH TIME ZONE,
    author VARCHAR(255),
    
    -- Processing status
    processing_status VARCHAR(30) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    processing_attempts INTEGER DEFAULT 0,
    
    -- Content characteristics
    content_type VARCHAR(50), -- 'article', 'video', 'podcast', 'social_post'
    language VARCHAR(10),
    word_count INTEGER,
    
    -- Quality indicators
    content_quality_score DECIMAL(4,3),
    extraction_confidence DECIMAL(4,3),
    
    -- Storage
    content_hash VARCHAR(64) UNIQUE, -- SHA-256 for deduplication
    raw_html TEXT, -- Original HTML if available
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 6. PROCESSED EVENTS - Analyzed and classified events
-- ============================================================================
CREATE TABLE processed_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    raw_event_id UUID NOT NULL REFERENCES raw_events(id),
    
    -- Classification
    event_type VARCHAR(50) NOT NULL, -- 'earnings', 'merger', 'fed_announcement', 'market_update'
    event_category VARCHAR(50) NOT NULL,
    event_subcategory VARCHAR(50),
    
    -- Enhanced content
    processed_title TEXT NOT NULL,
    processed_content TEXT NOT NULL,
    content_summary TEXT,
    key_points TEXT[],
    
    -- Entity extraction
    entities JSONB, -- Companies, people, locations, financial instruments
    financial_metrics JSONB, -- Revenue, profit, guidance, ratios
    
    -- Market impact assessment
    market_impact_score DECIMAL(4,3), -- 0.0 to 1.0
    urgency_level VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
    affected_sectors TEXT[],
    affected_companies TEXT[], -- Stock tickers
    
    -- Geographic and temporal
    geographic_relevance TEXT[], -- Countries/regions affected
    event_date TIMESTAMP WITH TIME ZONE,
    market_session VARCHAR(20), -- 'pre_market', 'regular', 'after_hours', 'closed'
    
    -- Processing metadata
    processing_engine VARCHAR(50), -- 'qwen_3_72b', 'automated', 'hybrid'
    processing_confidence DECIMAL(4,3),
    processing_time_ms INTEGER,
    
    -- Quality assessment
    content_quality_score DECIMAL(4,3),
    relevance_score DECIMAL(4,3),
    credibility_score DECIMAL(4,3),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 7. HOLDINGS DATA - Portfolio positions from CSV
-- ============================================================================
CREATE TABLE holdings_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Security identification
    ticker VARCHAR(20) NOT NULL,
    company_name VARCHAR(255),
    cusip VARCHAR(15),
    isin VARCHAR(20),
    
    -- Position details
    shares DECIMAL(15,2),
    market_value DECIMAL(15,2),
    weight DECIMAL(6,4), -- Portfolio weight as decimal (0.05 = 5%)
    
    -- Classification
    sector VARCHAR(100),
    industry VARCHAR(150),
    asset_class VARCHAR(50), -- 'equity', 'bond', 'commodity', 'currency'
    geography VARCHAR(50), -- 'domestic', 'international', 'emerging'
    
    -- Risk metrics
    beta DECIMAL(6,3),
    volatility DECIMAL(6,3),
    var_1d DECIMAL(15,2), -- 1-day Value at Risk
    
    -- Data source and timing
    data_source VARCHAR(100), -- CSV filename or data provider
    as_of_date DATE NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'sold', 'suspended'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique positions per date
    UNIQUE(ticker, as_of_date)
);

-- ============================================================================
-- 8. EVENT HOLDINGS RELEVANCE - Portfolio-aware event routing
-- ============================================================================
CREATE TABLE event_holdings_relevance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Relationships
    event_id VARCHAR(255) NOT NULL REFERENCES processed_events(event_id),
    ticker VARCHAR(20) NOT NULL,
    holdings_id UUID REFERENCES holdings_data(id),
    
    -- Relevance scoring
    direct_relevance_score DECIMAL(4,3), -- Direct mention/impact
    sector_relevance_score DECIMAL(4,3), -- Sector-wide impact
    market_relevance_score DECIMAL(4,3), -- Broad market impact
    
    -- Combined scoring
    overall_relevance_score DECIMAL(4,3) NOT NULL,
    relevance_confidence DECIMAL(4,3),
    
    -- Impact assessment
    impact_type VARCHAR(50), -- 'positive', 'negative', 'neutral', 'mixed'
    impact_magnitude VARCHAR(20), -- 'low', 'medium', 'high'
    impact_timeframe VARCHAR(30), -- 'immediate', 'short_term', 'long_term'
    
    -- Position context
    position_weight DECIMAL(6,4), -- Portfolio weight for impact calculation
    position_value_at_risk DECIMAL(15,2),
    
    -- Reasoning
    relevance_reasoning TEXT,
    key_factors TEXT[],
    
    -- Alert generation
    alert_threshold_exceeded BOOLEAN DEFAULT FALSE,
    alert_generated BOOLEAN DEFAULT FALSE,
    alert_level VARCHAR(20), -- 'info', 'warning', 'critical'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique event-ticker combinations
    UNIQUE(event_id, ticker)
);

-- ============================================================================
-- 9. PRICE HISTORY - 10-year historical price database
-- ============================================================================
CREATE TABLE price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Security identification
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    
    -- OHLCV data
    open_price DECIMAL(12,4),
    high_price DECIMAL(12,4),
    low_price DECIMAL(12,4),
    close_price DECIMAL(12,4),
    adjusted_close DECIMAL(12,4),
    volume BIGINT,
    
    -- Calculated metrics
    daily_return DECIMAL(8,6), -- Percentage return
    volatility_20d DECIMAL(8,6), -- 20-day rolling volatility
    sma_20 DECIMAL(12,4), -- 20-day simple moving average
    sma_50 DECIMAL(12,4), -- 50-day simple moving average
    
    -- Dividends and splits
    dividend_amount DECIMAL(8,4) DEFAULT 0,
    split_ratio DECIMAL(8,4) DEFAULT 1,
    
    -- Data source and quality
    data_source VARCHAR(50), -- 'yahoo', 'alpha_vantage', 'manual'
    data_quality VARCHAR(20) DEFAULT 'good', -- 'good', 'estimated', 'poor'
    
    -- Market context
    market_cap DECIMAL(18,2),
    trading_session VARCHAR(20), -- 'regular', 'extended'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique ticker-date combinations
    UNIQUE(ticker, date)
);

-- ============================================================================
-- 10. HISTORICAL IMPACT - Event impact tracking and analysis
-- ============================================================================
CREATE TABLE historical_impact (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Event reference
    event_id VARCHAR(255) NOT NULL REFERENCES processed_events(event_id),
    ticker VARCHAR(20) NOT NULL,
    
    -- Price impact measurements
    price_before DECIMAL(12,4), -- Price before event
    price_1h_after DECIMAL(12,4),
    price_1d_after DECIMAL(12,4),
    price_1w_after DECIMAL(12,4),
    price_1m_after DECIMAL(12,4),
    
    -- Return calculations
    return_1h DECIMAL(8,6),
    return_1d DECIMAL(8,6),
    return_1w DECIMAL(8,6),
    return_1m DECIMAL(8,6),
    
    -- Volume impact
    avg_volume_before BIGINT, -- 20-day average before event
    volume_on_event_day BIGINT,
    volume_ratio DECIMAL(6,3), -- Event day volume / average volume
    
    -- Market context
    market_return_1d DECIMAL(8,6), -- Market return for comparison
    sector_return_1d DECIMAL(8,6), -- Sector return for comparison
    relative_performance_1d DECIMAL(8,6), -- Stock vs market
    
    -- Statistical significance
    abnormal_return_1d DECIMAL(8,6), -- Return minus expected return
    statistical_significance DECIMAL(6,4), -- p-value
    confidence_level DECIMAL(4,3),
    
    -- Event characteristics
    event_timing VARCHAR(30), -- 'pre_market', 'during_market', 'after_market'
    earnings_season BOOLEAN DEFAULT FALSE,
    concurrent_events TEXT[], -- Other events on same day
    
    -- Analysis metadata
    analysis_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data_completeness DECIMAL(4,3), -- Percentage of required data available
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique event-ticker combinations
    UNIQUE(event_id, ticker)
);

-- ============================================================================
-- 11. SENTIMENT SCORES - Multi-level sentiment analysis
-- ============================================================================
CREATE TABLE sentiment_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Content reference
    event_id VARCHAR(255) NOT NULL REFERENCES processed_events(event_id),
    
    -- Overall sentiment
    overall_sentiment DECIMAL(4,3), -- -1.0 (very negative) to 1.0 (very positive)
    sentiment_magnitude DECIMAL(4,3), -- 0.0 to 1.0 (strength of sentiment)
    sentiment_classification VARCHAR(20), -- 'very_negative', 'negative', 'neutral', 'positive', 'very_positive'
    
    -- Entity-specific sentiment
    company_sentiment JSONB, -- Sentiment for each mentioned company
    sector_sentiment JSONB, -- Sentiment for each mentioned sector
    market_sentiment DECIMAL(4,3), -- Overall market sentiment
    
    -- Financial context sentiment
    earnings_sentiment DECIMAL(4,3), -- Sentiment about earnings/financial performance
    guidance_sentiment DECIMAL(4,3), -- Sentiment about future guidance
    management_sentiment DECIMAL(4,3), -- Sentiment about management/leadership
    
    -- Analysis details
    sentiment_engine VARCHAR(50), -- 'mlx_local', 'qwen_3_72b', 'financial_bert'
    confidence_score DECIMAL(4,3),
    processing_time_ms INTEGER,
    
    -- Supporting data
    positive_keywords TEXT[],
    negative_keywords TEXT[],
    neutral_keywords TEXT[],
    financial_terms_detected TEXT[],
    
    -- Quality metrics
    text_quality_score DECIMAL(4,3), -- Quality of input text for sentiment analysis
    sentiment_reliability DECIMAL(4,3), -- Reliability of sentiment score
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique sentiment per event
    UNIQUE(event_id)
);

-- ============================================================================
-- 12. ALERTS - Generated notifications and delivery
-- ============================================================================
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Alert source
    event_id VARCHAR(255) REFERENCES processed_events(event_id),
    trigger_type VARCHAR(50) NOT NULL, -- 'portfolio_relevance', 'high_impact', 'breaking_news', 'quality_threshold'
    
    -- Alert classification
    alert_level VARCHAR(20) NOT NULL, -- 'info', 'warning', 'critical', 'urgent'
    urgency_score DECIMAL(4,3),
    priority INTEGER DEFAULT 5, -- 1 (highest) to 10 (lowest)
    
    -- Content
    title VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    summary TEXT,
    
    -- Context
    affected_tickers TEXT[],
    portfolio_impact DECIMAL(15,2), -- Dollar impact estimate
    relevance_score DECIMAL(4,3),
    
    -- Alert rules
    alert_rule_id VARCHAR(100),
    threshold_value DECIMAL(10,4),
    actual_value DECIMAL(10,4),
    threshold_exceeded BOOLEAN DEFAULT TRUE,
    
    -- Timing
    event_timestamp TIMESTAMP WITH TIME ZONE,
    alert_generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Delivery configuration
    delivery_channels TEXT[], -- ['web_dashboard', 'email', 'webhook', 'macos_notification']
    delivery_status VARCHAR(30) DEFAULT 'pending', -- 'pending', 'sent', 'failed', 'cancelled'
    
    -- Expiration
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- User interaction
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100),
    
    -- Feedback
    user_rating INTEGER, -- 1-5 stars
    feedback_text TEXT,
    false_positive BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 13. ALERT DELIVERY LOG - Alert delivery tracking
-- ============================================================================
CREATE TABLE alert_delivery_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Alert reference
    alert_id VARCHAR(255) NOT NULL REFERENCES alerts(alert_id),
    
    -- Delivery details
    delivery_channel VARCHAR(50) NOT NULL, -- 'web_dashboard', 'email', 'webhook', 'macos_notification'
    delivery_method VARCHAR(100), -- Specific method or endpoint
    
    -- Attempt tracking
    attempt_number INTEGER DEFAULT 1,
    delivery_status VARCHAR(30) NOT NULL, -- 'success', 'failed', 'retry', 'cancelled'
    
    -- Timing
    attempted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE,
    
    -- Technical details
    response_code INTEGER,
    response_message TEXT,
    error_details JSONB,
    
    -- Delivery metadata
    recipient VARCHAR(255),
    delivery_size_bytes INTEGER,
    processing_time_ms INTEGER,
    
    -- Retry configuration
    retry_after TIMESTAMP WITH TIME ZONE,
    max_retries INTEGER DEFAULT 3,
    backoff_factor DECIMAL(4,2) DEFAULT 1.5,
    
    -- Success metrics
    delivery_confirmed BOOLEAN DEFAULT FALSE,
    user_interaction BOOLEAN DEFAULT FALSE, -- Did user click/view?
    interaction_timestamp TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- News Sources
CREATE INDEX idx_news_sources_status ON news_sources(status);
CREATE INDEX idx_news_sources_quality ON news_sources(quality_score DESC);
CREATE INDEX idx_news_sources_last_crawl ON news_sources(last_crawl_at);

-- Source Evaluations
CREATE INDEX idx_source_evaluations_source ON source_evaluations(source_id);
CREATE INDEX idx_source_evaluations_date ON source_evaluations(evaluation_date DESC);
CREATE INDEX idx_source_evaluations_score ON source_evaluations(overall_score DESC);

-- Raw Events
CREATE INDEX idx_raw_events_source ON raw_events(source_id);
CREATE INDEX idx_raw_events_status ON raw_events(processing_status);
CREATE INDEX idx_raw_events_extracted ON raw_events(extracted_at DESC);
CREATE INDEX idx_raw_events_hash ON raw_events(content_hash);

-- Processed Events
CREATE INDEX idx_processed_events_type ON processed_events(event_type);
CREATE INDEX idx_processed_events_date ON processed_events(event_date DESC);
CREATE INDEX idx_processed_events_impact ON processed_events(market_impact_score DESC);
CREATE INDEX idx_processed_events_urgency ON processed_events(urgency_level);

-- Holdings Data
CREATE INDEX idx_holdings_ticker ON holdings_data(ticker);
CREATE INDEX idx_holdings_date ON holdings_data(as_of_date DESC);
CREATE INDEX idx_holdings_weight ON holdings_data(weight DESC);

-- Event Holdings Relevance
CREATE INDEX idx_event_relevance_event ON event_holdings_relevance(event_id);
CREATE INDEX idx_event_relevance_ticker ON event_holdings_relevance(ticker);
CREATE INDEX idx_event_relevance_score ON event_holdings_relevance(overall_relevance_score DESC);
CREATE INDEX idx_event_relevance_alert ON event_holdings_relevance(alert_threshold_exceeded);

-- Price History
CREATE INDEX idx_price_history_ticker_date ON price_history(ticker, date DESC);
CREATE INDEX idx_price_history_date ON price_history(date DESC);

-- Historical Impact
CREATE INDEX idx_historical_impact_event ON historical_impact(event_id);
CREATE INDEX idx_historical_impact_ticker ON historical_impact(ticker);
CREATE INDEX idx_historical_impact_return ON historical_impact(return_1d DESC);

-- Sentiment Scores
CREATE INDEX idx_sentiment_event ON sentiment_scores(event_id);
CREATE INDEX idx_sentiment_overall ON sentiment_scores(overall_sentiment);
CREATE INDEX idx_sentiment_confidence ON sentiment_scores(confidence_score DESC);

-- Alerts
CREATE INDEX idx_alerts_level ON alerts(alert_level);
CREATE INDEX idx_alerts_generated ON alerts(alert_generated_at DESC);
CREATE INDEX idx_alerts_active ON alerts(is_active);
CREATE INDEX idx_alerts_ticker ON alerts USING GIN(affected_tickers);

-- Alert Delivery Log
CREATE INDEX idx_delivery_alert ON alert_delivery_log(alert_id);
CREATE INDEX idx_delivery_status ON alert_delivery_log(delivery_status);
CREATE INDEX idx_delivery_attempted ON alert_delivery_log(attempted_at DESC);

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to relevant tables
CREATE TRIGGER update_news_sources_updated_at BEFORE UPDATE ON news_sources 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_processed_events_updated_at BEFORE UPDATE ON processed_events 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_holdings_data_updated_at BEFORE UPDATE ON holdings_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_price_history_updated_at BEFORE UPDATE ON price_history 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON alerts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SAMPLE DATA FOR TESTING
-- ============================================================================

-- Insert sample news sources
INSERT INTO news_sources (source_id, name, url, source_type, categories, quality_score, status) VALUES
('reuters_finance', 'Reuters Finance', 'https://reuters.com/finance', 'news_site', '{"earnings","mergers","markets"}', 0.95, 'active'),
('bloomberg_markets', 'Bloomberg Markets', 'https://bloomberg.com/markets', 'news_site', '{"markets","economics","trading"}', 0.92, 'active'),
('cnbc_markets', 'CNBC Markets', 'https://cnbc.com/markets', 'news_site', '{"markets","earnings","breaking"}', 0.88, 'active'),
('marketwatch', 'MarketWatch', 'https://marketwatch.com', 'news_site', '{"markets","personal_finance","earnings"}', 0.85, 'active'),
('yahoo_finance', 'Yahoo Finance', 'https://finance.yahoo.com', 'news_site', '{"markets","earnings","analyst_ratings"}', 0.82, 'active');

-- Insert sample macro data sources
INSERT INTO macro_data_sources (source_id, name, source_type, data_categories, update_frequency, status) VALUES
('fed_economic_data', 'Federal Reserve Economic Data', 'fed_data', '{"interest_rates","inflation","employment"}', 'daily', 'active'),
('bls_employment', 'Bureau of Labor Statistics', 'economic_calendar', '{"employment","inflation","wages"}', 'monthly', 'active'),
('earnings_calendar', 'Financial Earnings Calendar', 'earnings_calendar', '{"earnings","guidance","estimates"}', 'daily', 'active');

COMMIT;

-- Schema creation completed
SELECT 'Real-Time Intel database schema created successfully with 13 tables and performance indexes' as status; 