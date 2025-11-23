-- Migration 046: User Consent Log
-- Block 5 Legal & Safety Hardening
-- Tracks user consent for Terms & Privacy versions

CREATE TABLE IF NOT EXISTS user_consent_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    terms_version VARCHAR(50) NOT NULL,
    privacy_version VARCHAR(50) NOT NULL,
    consent_type VARCHAR(100) NOT NULL,  -- signup, plan_upgrade, feature_update
    consent_channel VARCHAR(50) NOT NULL,  -- mobile, web
    ip_address VARCHAR(100),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for fast lookup
    INDEX idx_user_consent_user_id (user_id),
    INDEX idx_user_consent_timestamp (timestamp)
);

-- Add comment for documentation
COMMENT ON TABLE user_consent_log IS 'Block 5: Tracks user consent to Terms & Privacy versions for DPDP compliance and legal defense';
