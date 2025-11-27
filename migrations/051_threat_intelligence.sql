-- Migration 051: Threat Intelligence System
-- Block 15: 12-hour internet scans for scam pattern detection

-- Table: threat_intelligence_scans
-- Stores information about each 12-hour scan cycle
CREATE TABLE IF NOT EXISTS threat_intelligence_scans (
    id SERIAL PRIMARY KEY,
    scan_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    scan_source VARCHAR(100) NOT NULL, -- 'twitter', 'news', 'government', 'reddit', 'internal'
    scan_status VARCHAR(50) NOT NULL DEFAULT 'running', -- 'running', 'completed', 'failed'
    items_collected INTEGER DEFAULT 0,
    new_patterns_detected INTEGER DEFAULT 0,
    scan_duration_seconds INTEGER,
    error_message TEXT,
    scan_metadata JSONB DEFAULT '{}', -- Additional scan details
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_threat_scans_timestamp ON threat_intelligence_scans(scan_timestamp DESC);
CREATE INDEX idx_threat_scans_status ON threat_intelligence_scans(scan_status);
CREATE INDEX idx_threat_scans_source ON threat_intelligence_scans(scan_source);

-- Table: threat_intelligence_items
-- Stores individual threat intelligence items collected during scans
CREATE TABLE IF NOT EXISTS threat_intelligence_items (
    id SERIAL PRIMARY KEY,
    scan_id INTEGER REFERENCES threat_intelligence_scans(id) ON DELETE CASCADE,
    source_url TEXT, -- URL where the threat was found
    source_type VARCHAR(100), -- 'social_media', 'news', 'government', 'forum', 'user_report'
    content_text TEXT, -- Raw text content
    content_summary TEXT, -- AI-generated summary
    extracted_phone_numbers JSONB DEFAULT '[]', -- Array of phone numbers found
    extracted_urls JSONB DEFAULT '[]', -- Array of URLs found
    extracted_keywords JSONB DEFAULT '[]', -- Array of scam-related keywords
    scam_type VARCHAR(100), -- 'digital_arrest', 'upi_fraud', 'investment_scam', etc.
    severity_score INTEGER CHECK (severity_score BETWEEN 1 AND 10), -- 1=low, 10=critical
    confidence_score DECIMAL(5,2) CHECK (confidence_score BETWEEN 0.00 AND 1.00), -- AI confidence
    geographic_context VARCHAR(100), -- State/city if mentioned
    language VARCHAR(50) DEFAULT 'en', -- Language of content
    is_verified BOOLEAN DEFAULT FALSE, -- Manually verified by admin
    is_false_positive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP,
    verified_by INTEGER REFERENCES users(id)
);

CREATE INDEX idx_threat_items_scan ON threat_intelligence_items(scan_id);
CREATE INDEX idx_threat_items_scam_type ON threat_intelligence_items(scam_type);
CREATE INDEX idx_threat_items_severity ON threat_intelligence_items(severity_score DESC);
CREATE INDEX idx_threat_items_created ON threat_intelligence_items(created_at DESC);
CREATE INDEX idx_threat_items_verified ON threat_intelligence_items(is_verified, is_false_positive);

-- Table: threat_patterns
-- Stores detected patterns from threat intelligence analysis
CREATE TABLE IF NOT EXISTS threat_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(100) NOT NULL, -- 'phone_pattern', 'url_pattern', 'keyword_pattern', 'script_pattern'
    pattern_name VARCHAR(255) NOT NULL,
    pattern_description TEXT,
    pattern_data JSONB NOT NULL, -- Structured pattern data (regex, keywords, etc.)
    scam_type VARCHAR(100), -- Associated scam type
    severity_level VARCHAR(50) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    confidence_score DECIMAL(5,2) CHECK (confidence_score BETWEEN 0.00 AND 1.00),
    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    occurrence_count INTEGER DEFAULT 1,
    affected_users_count INTEGER DEFAULT 0, -- Users who encountered this pattern
    is_active BOOLEAN DEFAULT TRUE,
    is_auto_block BOOLEAN DEFAULT FALSE, -- Automatically block calls/URLs matching this pattern
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    deactivated_at TIMESTAMP,
    deactivated_by INTEGER REFERENCES users(id)
);

CREATE INDEX idx_threat_patterns_type ON threat_patterns(pattern_type);
CREATE INDEX idx_threat_patterns_scam_type ON threat_patterns(scam_type);
CREATE INDEX idx_threat_patterns_active ON threat_patterns(is_active);
CREATE INDEX idx_threat_patterns_severity ON threat_patterns(severity_level);
CREATE INDEX idx_threat_patterns_last_seen ON threat_patterns(last_seen DESC);

-- Table: threat_alerts
-- Stores alerts generated from threat intelligence
CREATE TABLE IF NOT EXISTS threat_alerts (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER REFERENCES threat_patterns(id) ON DELETE SET NULL,
    alert_type VARCHAR(100) NOT NULL, -- 'new_pattern', 'severity_increase', 'mass_outbreak', 'targeted_attack'
    alert_title VARCHAR(255) NOT NULL,
    alert_message TEXT NOT NULL,
    alert_severity VARCHAR(50) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    affected_users_count INTEGER DEFAULT 0,
    recommended_actions JSONB DEFAULT '[]', -- Array of recommended actions
    alert_metadata JSONB DEFAULT '{}', -- Additional context
    is_acknowledged BOOLEAN DEFAULT FALSE,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    acknowledged_by INTEGER REFERENCES users(id),
    resolved_at TIMESTAMP,
    resolved_by INTEGER REFERENCES users(id),
    resolution_notes TEXT
);

CREATE INDEX idx_threat_alerts_pattern ON threat_alerts(pattern_id);
CREATE INDEX idx_threat_alerts_type ON threat_alerts(alert_type);
CREATE INDEX idx_threat_alerts_severity ON threat_alerts(alert_severity);
CREATE INDEX idx_threat_alerts_acknowledged ON threat_alerts(is_acknowledged, is_resolved);
CREATE INDEX idx_threat_alerts_created ON threat_alerts(created_at DESC);

-- Table: threat_intel_sources
-- Configuration for threat intelligence data sources
CREATE TABLE IF NOT EXISTS threat_intel_sources (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL UNIQUE,
    source_type VARCHAR(100) NOT NULL, -- 'twitter', 'news', 'government', 'reddit', 'rss', 'api'
    source_url TEXT,
    source_config JSONB DEFAULT '{}', -- API keys, selectors, etc.
    is_enabled BOOLEAN DEFAULT TRUE,
    scan_frequency_hours INTEGER DEFAULT 12,
    last_scan_at TIMESTAMP,
    last_scan_status VARCHAR(50), -- 'success', 'failed', 'partial'
    success_rate DECIMAL(5,2), -- Percentage of successful scans
    total_scans INTEGER DEFAULT 0,
    total_items_collected INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)
);

CREATE INDEX idx_threat_sources_enabled ON threat_intel_sources(is_enabled);
CREATE INDEX idx_threat_sources_last_scan ON threat_intel_sources(last_scan_at);

-- Table: threat_intel_statistics
-- Daily statistics for threat intelligence system
CREATE TABLE IF NOT EXISTS threat_intel_statistics (
    id SERIAL PRIMARY KEY,
    stat_date DATE NOT NULL UNIQUE,
    total_scans INTEGER DEFAULT 0,
    successful_scans INTEGER DEFAULT 0,
    failed_scans INTEGER DEFAULT 0,
    total_items_collected INTEGER DEFAULT 0,
    new_patterns_detected INTEGER DEFAULT 0,
    alerts_generated INTEGER DEFAULT 0,
    threats_blocked INTEGER DEFAULT 0, -- Threats blocked based on this intelligence
    users_protected INTEGER DEFAULT 0, -- Users who were protected
    avg_scan_duration_seconds INTEGER,
    top_scam_types JSONB DEFAULT '[]', -- Array of {type, count}
    top_sources JSONB DEFAULT '[]', -- Array of {source, items_count}
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_threat_stats_date ON threat_intel_statistics(stat_date DESC);

-- Insert default threat intelligence sources
INSERT INTO threat_intel_sources (source_name, source_type, source_url, source_config, is_enabled, scan_frequency_hours, created_at) VALUES
('Cybercrime Portal', 'government', 'https://cybercrime.gov.in/', '{"scrape_type": "html", "selectors": {"alerts": ".alert-item"}}', TRUE, 12, CURRENT_TIMESTAMP),
('CERT-In Advisories', 'government', 'https://www.cert-in.org.in/', '{"scrape_type": "html", "selectors": {"advisories": ".advisory-list"}}', TRUE, 12, CURRENT_TIMESTAMP),
('Twitter Scam Reports', 'twitter', 'https://twitter.com/search', '{"search_queries": ["digital arrest scam india", "upi fraud", "cybercrime india"], "language": "en,hi"}', TRUE, 12, CURRENT_TIMESTAMP),
('Reddit India Scams', 'reddit', 'https://www.reddit.com/r/india', '{"subreddits": ["india", "IndianStockMarket", "IndiaTech"], "keywords": ["scam", "fraud", "cheated"]}', TRUE, 12, CURRENT_TIMESTAMP),
('Indian Cybercrime News', 'news', 'https://www.google.com/search?q=cybercrime+india&tbm=nws', '{"scrape_type": "google_news", "keywords": ["cybercrime", "scam", "fraud", "digital arrest"]}', TRUE, 12, CURRENT_TIMESTAMP),
('Sanchar Saathi Chakshu', 'government', 'https://sancharsaathi.gov.in/sfc', '{"scrape_type": "html", "note": "Fraud communication reporting portal"}', TRUE, 12, CURRENT_TIMESTAMP)
ON CONFLICT (source_name) DO NOTHING;

-- Function: Update threat pattern occurrence
CREATE OR REPLACE FUNCTION update_threat_pattern_occurrence()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE threat_patterns
    SET 
        occurrence_count = occurrence_count + 1,
        last_seen = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.pattern_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update pattern occurrence when new item is linked
CREATE TRIGGER trigger_update_pattern_occurrence
AFTER INSERT ON threat_intelligence_items
FOR EACH ROW
WHEN (NEW.scam_type IS NOT NULL)
EXECUTE FUNCTION update_threat_pattern_occurrence();

-- Function: Generate daily statistics
CREATE OR REPLACE FUNCTION generate_threat_intel_daily_stats(stat_date_param DATE)
RETURNS VOID AS $$
BEGIN
    INSERT INTO threat_intel_statistics (
        stat_date,
        total_scans,
        successful_scans,
        failed_scans,
        total_items_collected,
        new_patterns_detected,
        alerts_generated,
        avg_scan_duration_seconds,
        top_scam_types,
        top_sources
    )
    SELECT
        stat_date_param,
        COUNT(*),
        COUNT(*) FILTER (WHERE scan_status = 'completed'),
        COUNT(*) FILTER (WHERE scan_status = 'failed'),
        COALESCE(SUM(items_collected), 0),
        COALESCE(SUM(new_patterns_detected), 0),
        (SELECT COUNT(*) FROM threat_alerts WHERE DATE(created_at) = stat_date_param),
        AVG(scan_duration_seconds)::INTEGER,
        (
            SELECT JSONB_AGG(row_to_json(t))
            FROM (
                SELECT scam_type, COUNT(*) as count
                FROM threat_intelligence_items
                WHERE DATE(created_at) = stat_date_param AND scam_type IS NOT NULL
                GROUP BY scam_type
                ORDER BY count DESC
                LIMIT 10
            ) t
        ),
        (
            SELECT JSONB_AGG(row_to_json(s))
            FROM (
                SELECT scan_source, SUM(items_collected) as items_count
                FROM threat_intelligence_scans
                WHERE DATE(scan_timestamp) = stat_date_param
                GROUP BY scan_source
                ORDER BY items_count DESC
                LIMIT 10
            ) s
        )
    FROM threat_intelligence_scans
    WHERE DATE(scan_timestamp) = stat_date_param
    ON CONFLICT (stat_date) DO UPDATE SET
        total_scans = EXCLUDED.total_scans,
        successful_scans = EXCLUDED.successful_scans,
        failed_scans = EXCLUDED.failed_scans,
        total_items_collected = EXCLUDED.total_items_collected,
        new_patterns_detected = EXCLUDED.new_patterns_detected,
        alerts_generated = EXCLUDED.alerts_generated,
        avg_scan_duration_seconds = EXCLUDED.avg_scan_duration_seconds,
        top_scam_types = EXCLUDED.top_scam_types,
        top_sources = EXCLUDED.top_sources;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON threat_intelligence_scans TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON threat_intelligence_items TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON threat_patterns TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON threat_alerts TO PUBLIC;
GRANT SELECT, INSERT, UPDATE ON threat_intel_sources TO PUBLIC;
GRANT SELECT, INSERT, UPDATE ON threat_intel_statistics TO PUBLIC;

GRANT USAGE, SELECT ON SEQUENCE threat_intelligence_scans_id_seq TO PUBLIC;
GRANT USAGE, SELECT ON SEQUENCE threat_intelligence_items_id_seq TO PUBLIC;
GRANT USAGE, SELECT ON SEQUENCE threat_patterns_id_seq TO PUBLIC;
GRANT USAGE, SELECT ON SEQUENCE threat_alerts_id_seq TO PUBLIC;
GRANT USAGE, SELECT ON SEQUENCE threat_intel_sources_id_seq TO PUBLIC;
GRANT USAGE, SELECT ON SEQUENCE threat_intel_statistics_id_seq TO PUBLIC;
