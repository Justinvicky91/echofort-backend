-- Migration 048: AI Pattern Library
-- Purpose: Store learned threat patterns from internet research
-- Block: 8 (AI Command Center)
-- Date: 2025-11-26

-- Create ai_pattern_library table
CREATE TABLE IF NOT EXISTS ai_pattern_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    category VARCHAR(50) NOT NULL,  -- 'PHISHING', 'FRAUD', 'HARASSMENT', 'EXTREMISM'
    description TEXT NOT NULL,  -- Human-readable summary of the pattern
    example_phrases JSONB,  -- Array of example phrases or keywords
    risk_level VARCHAR(20) NOT NULL,  -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    source_url TEXT,  -- URL where the pattern was identified
    tags JSONB,  -- Array of relevant tags
    is_active BOOLEAN DEFAULT TRUE,  -- Can be deactivated if pattern becomes obsolete
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_category CHECK (category IN ('PHISHING', 'FRAUD', 'HARASSMENT', 'EXTREMISM', 'SCAM', 'IMPERSONATION', 'LOAN_HARASSMENT')),
    CONSTRAINT valid_risk_level CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

-- Create indexes for common queries
CREATE INDEX idx_ai_pattern_library_category ON ai_pattern_library(category);
CREATE INDEX idx_ai_pattern_library_risk_level ON ai_pattern_library(risk_level);
CREATE INDEX idx_ai_pattern_library_created_at ON ai_pattern_library(created_at DESC);
CREATE INDEX idx_ai_pattern_library_is_active ON ai_pattern_library(is_active);

-- Create GIN index for JSONB columns for efficient searching
CREATE INDEX idx_ai_pattern_library_example_phrases ON ai_pattern_library USING GIN (example_phrases);
CREATE INDEX idx_ai_pattern_library_tags ON ai_pattern_library USING GIN (tags);

-- Add comments to table
COMMENT ON TABLE ai_pattern_library IS 'Library of learned threat patterns from internet research and analysis';
COMMENT ON COLUMN ai_pattern_library.category IS 'Type of threat: PHISHING, FRAUD, HARASSMENT, EXTREMISM, SCAM, IMPERSONATION, LOAN_HARASSMENT';
COMMENT ON COLUMN ai_pattern_library.description IS 'Human-readable summary of the threat pattern';
COMMENT ON COLUMN ai_pattern_library.example_phrases IS 'JSON array of example phrases, keywords, or signatures';
COMMENT ON COLUMN ai_pattern_library.risk_level IS 'Severity: LOW, MEDIUM, HIGH, CRITICAL';
COMMENT ON COLUMN ai_pattern_library.source_url IS 'URL where this pattern was discovered (for audit trail)';
COMMENT ON COLUMN ai_pattern_library.tags IS 'JSON array of tags for categorization and search';
COMMENT ON COLUMN ai_pattern_library.is_active IS 'Whether this pattern is currently active in detection';

-- Insert a sample pattern for testing
INSERT INTO ai_pattern_library (
    category,
    description,
    example_phrases,
    risk_level,
    source_url,
    tags
) VALUES (
    'PHISHING',
    'Digital Arrest Scam - Impersonation of law enforcement officials claiming victim is under investigation and demanding immediate payment to avoid arrest',
    '["digital arrest", "CBI investigation", "immediate payment required", "your account will be frozen", "arrest warrant issued"]'::jsonb,
    'CRITICAL',
    'https://example.com/digital-arrest-scam-alert',
    '["impersonation", "law_enforcement", "payment_demand", "urgency_tactic"]'::jsonb
);
