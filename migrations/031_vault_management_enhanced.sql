-- Enhanced Vault Management for Super Admin
-- Comprehensive call recordings and evidence management

-- Call recordings metadata enhancement
CREATE TABLE IF NOT EXISTS call_recording_metadata (
    id SERIAL PRIMARY KEY,
    recording_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Call details
    phone_number VARCHAR(20),
    caller_name VARCHAR(255),
    call_direction VARCHAR(20), -- incoming, outgoing
    call_duration_seconds INTEGER,
    call_timestamp TIMESTAMP,
    
    -- Recording details
    file_url TEXT,
    file_size_bytes BIGINT,
    file_format VARCHAR(20), -- mp3, wav, m4a
    recording_quality VARCHAR(20), -- low, medium, high
    
    -- Scam detection
    scam_detected BOOLEAN DEFAULT FALSE,
    scam_confidence_score DECIMAL(5, 2),
    scam_type VARCHAR(100),
    scam_keywords TEXT[], -- Array of detected keywords
    
    -- Analysis
    transcription_text TEXT,
    transcription_language VARCHAR(10),
    sentiment_score DECIMAL(5, 2),
    threat_level VARCHAR(20), -- low, medium, high, critical
    
    -- Status
    is_reported BOOLEAN DEFAULT FALSE,
    reported_to_authorities BOOLEAN DEFAULT FALSE,
    report_reference_number VARCHAR(100),
    
    -- Metadata
    device_id VARCHAR(255),
    app_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_call_metadata_user ON call_recording_metadata(user_id);
CREATE INDEX IF NOT EXISTS idx_call_metadata_phone ON call_recording_metadata(phone_number);
CREATE INDEX IF NOT EXISTS idx_call_metadata_scam ON call_recording_metadata(scam_detected);
CREATE INDEX IF NOT EXISTS idx_call_metadata_timestamp ON call_recording_metadata(call_timestamp DESC);

-- Evidence vault enhancement
CREATE TABLE IF NOT EXISTS evidence_vault_metadata (
    id SERIAL PRIMARY KEY,
    evidence_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Evidence details
    evidence_type VARCHAR(50) NOT NULL, -- call_recording, screenshot, email, sms, document, video
    title VARCHAR(255),
    description TEXT,
    
    -- File details
    file_url TEXT,
    file_size_bytes BIGINT,
    file_format VARCHAR(50),
    file_hash VARCHAR(64), -- SHA-256 for integrity
    
    -- Scam details
    scam_type VARCHAR(100),
    scam_category VARCHAR(100), -- phishing, vishing, smishing, investment, romance, etc.
    reported_amount DECIMAL(15, 2),
    currency VARCHAR(10) DEFAULT 'INR',
    scammer_details JSONB, -- {name, phone, email, address, etc.}
    
    -- Incident details
    incident_date TIMESTAMP,
    incident_location VARCHAR(255),
    police_complaint_filed BOOLEAN DEFAULT FALSE,
    complaint_number VARCHAR(100),
    police_station VARCHAR(255),
    
    -- Verification status
    verification_status VARCHAR(50) DEFAULT 'pending', -- pending, verified, rejected, under_review
    verified_by INTEGER REFERENCES users(id),
    verified_at TIMESTAMP,
    verification_notes TEXT,
    
    -- Sharing and permissions
    shared_with_authorities BOOLEAN DEFAULT FALSE,
    shared_at TIMESTAMP,
    public_visibility BOOLEAN DEFAULT FALSE,
    
    -- Tags and categorization
    tags TEXT[],
    severity_level VARCHAR(20), -- low, medium, high, critical
    
    -- Metadata
    device_id VARCHAR(255),
    ip_address VARCHAR(45),
    geolocation JSONB, -- {lat, lng, city, country}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evidence_metadata_user ON evidence_vault_metadata(user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_metadata_type ON evidence_vault_metadata(evidence_type);
CREATE INDEX IF NOT EXISTS idx_evidence_metadata_status ON evidence_vault_metadata(verification_status);
CREATE INDEX IF NOT EXISTS idx_evidence_metadata_scam_type ON evidence_vault_metadata(scam_type);
CREATE INDEX IF NOT EXISTS idx_evidence_metadata_created ON evidence_vault_metadata(created_at DESC);

-- Evidence access log (for audit trail)
CREATE TABLE IF NOT EXISTS evidence_access_log (
    id SERIAL PRIMARY KEY,
    evidence_id INTEGER NOT NULL,
    accessed_by INTEGER NOT NULL REFERENCES users(id),
    access_type VARCHAR(50), -- view, download, share, delete
    access_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_evidence_access_evidence ON evidence_access_log(evidence_id);
CREATE INDEX IF NOT EXISTS idx_evidence_access_user ON evidence_access_log(accessed_by);

COMMENT ON TABLE call_recording_metadata IS 'Enhanced metadata for call recordings with scam detection';
COMMENT ON TABLE evidence_vault_metadata IS 'Enhanced metadata for evidence vault items';
COMMENT ON TABLE evidence_access_log IS 'Audit trail for evidence access';
