-- Migration 013: Enhanced Auto-Alerts with Global Support and Evidence Storage

-- Drop old table if exists and create new enhanced version
DROP TABLE IF EXISTS auto_alerts CASCADE;

CREATE TABLE auto_alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Location and type
    country_code VARCHAR(2) NOT NULL DEFAULT 'IN',  -- ISO country code
    alert_type VARCHAR(50) NOT NULL,  -- cybercrime, bank, police, etc.
    scam_type VARCHAR(100) NOT NULL,
    
    -- Incident details
    incident_date VARCHAR(50),
    amount_lost DECIMAL(15, 2) DEFAULT 0,
    
    -- Scammer information (JSON)
    scammer_details JSONB DEFAULT '{}'::jsonb,
    
    -- Complaint details
    description TEXT NOT NULL,
    evidence_files JSONB DEFAULT '[]'::jsonb,  -- Array of evidence files
    
    -- Email draft
    recipient_email VARCHAR(255),
    recipient_name VARCHAR(255),
    subject TEXT,
    body TEXT,
    
    -- EchoFort certificate
    certificate TEXT,
    certificate_id VARCHAR(50),
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'draft',  -- draft, approved, sent, rejected
    user_confirmed BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    sent_at TIMESTAMP,
    
    -- Metadata
    scam_incident_id INTEGER,  -- Link to scam_cases if applicable
    admin_notes TEXT
);

-- Indexes for performance
CREATE INDEX idx_auto_alerts_user ON auto_alerts(user_id);
CREATE INDEX idx_auto_alerts_country ON auto_alerts(country_code);
CREATE INDEX idx_auto_alerts_status ON auto_alerts(status);
CREATE INDEX idx_auto_alerts_created ON auto_alerts(created_at DESC);
CREATE INDEX idx_auto_alerts_scammer ON auto_alerts USING GIN(scammer_details);
CREATE INDEX idx_auto_alerts_evidence ON auto_alerts USING GIN(evidence_files);

-- Comments
COMMENT ON TABLE auto_alerts IS 'Global complaint system with evidence storage and EchoFort authentication';
COMMENT ON COLUMN auto_alerts.country_code IS 'ISO 3166-1 alpha-2 country code';
COMMENT ON COLUMN auto_alerts.scammer_details IS 'JSON: phone, email, upi, account, name';
COMMENT ON COLUMN auto_alerts.evidence_files IS 'JSON array: filename, file_type, file_url, file_size, uploaded_at';
COMMENT ON COLUMN auto_alerts.certificate IS 'EchoFort authentication certificate text';
COMMENT ON COLUMN auto_alerts.status IS 'draft=created, approved=user confirmed, sent=manually sent by user, rejected=cancelled';

