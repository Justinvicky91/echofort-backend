-- Migration 043: Create Evidence Vault Table
-- Created: 2025-11-23
-- Purpose: Main evidence vault table for storing all evidence types

CREATE TABLE IF NOT EXISTS evidence_vault (
    id SERIAL PRIMARY KEY,
    evidence_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    family_member_id VARCHAR(255),
    purchase_person_id VARCHAR(255),
    
    -- Evidence type and details
    evidence_type VARCHAR(50) NOT NULL, -- call_recording, screenshot, sms, email, etc.
    
    -- Call recording specific fields
    caller_number VARCHAR(50),
    duration INTEGER, -- in seconds
    recording_url TEXT,
    threat_level INTEGER, -- 1-10
    scam_type VARCHAR(100),
    ai_analysis JSONB,
    
    -- Location data
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    address TEXT,
    
    -- EchoFort seal and retention
    echofort_seal TEXT,
    retention_expiry TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_evidence_vault_user ON evidence_vault(user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_evidence_id ON evidence_vault(evidence_id);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_type ON evidence_vault(evidence_type);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_scam_type ON evidence_vault(scam_type);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_threat_level ON evidence_vault(threat_level);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_created ON evidence_vault(created_at DESC);

COMMENT ON TABLE evidence_vault IS 'Main evidence vault for storing all types of evidence with 7-year retention';
COMMENT ON COLUMN evidence_vault.echofort_seal IS 'Legal certification seal for evidence';
COMMENT ON COLUMN evidence_vault.retention_expiry IS '7-year retention period for legal compliance';
