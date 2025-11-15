-- DPDP (Digital Personal Data Protection Act, 2023) Compliance
-- User consent management, data retention, and privacy controls

-- User Consent Table
CREATE TABLE IF NOT EXISTS user_consents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type VARCHAR(100) NOT NULL, -- data_collection, location_tracking, call_recording, data_sharing, marketing
    purpose TEXT NOT NULL, -- Specific purpose for data processing
    consent_given BOOLEAN DEFAULT FALSE,
    consent_date TIMESTAMP,
    withdrawal_date TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    consent_version VARCHAR(20) DEFAULT '1.0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_consents_user ON user_consents(user_id);
CREATE INDEX IF NOT EXISTS idx_user_consents_type ON user_consents(consent_type);
CREATE INDEX IF NOT EXISTS idx_user_consents_active ON user_consents(is_active);

-- Privacy Policy Acceptance Table
CREATE TABLE IF NOT EXISTS privacy_policy_acceptances (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    policy_version VARCHAR(20) NOT NULL,
    accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    acceptance_method VARCHAR(50) -- signup, update, explicit
);

CREATE INDEX IF NOT EXISTS idx_privacy_acceptances_user ON privacy_policy_acceptances(user_id);
CREATE INDEX IF NOT EXISTS idx_privacy_acceptances_version ON privacy_policy_acceptances(policy_version);

-- Data Access Audit Log
CREATE TABLE IF NOT EXISTS data_access_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    accessed_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    access_type VARCHAR(50) NOT NULL, -- view, export, modify, delete, share
    data_category VARCHAR(100) NOT NULL, -- profile, location, calls, messages, vault
    access_reason TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_data_access_user ON data_access_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_data_access_type ON data_access_logs(access_type);
CREATE INDEX IF NOT EXISTS idx_data_access_time ON data_access_logs(accessed_at DESC);

-- Data Retention Policies
CREATE TABLE IF NOT EXISTS data_retention_policies (
    id SERIAL PRIMARY KEY,
    data_category VARCHAR(100) NOT NULL UNIQUE, -- profile, location, calls, messages, vault, analytics
    retention_days INTEGER NOT NULL, -- Number of days to retain data
    auto_delete BOOLEAN DEFAULT TRUE,
    description TEXT,
    legal_basis TEXT, -- Legal reason for retention period
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_retention_category ON data_retention_policies(data_category);

-- Data Deletion Requests
CREATE TABLE IF NOT EXISTS data_deletion_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    request_type VARCHAR(50) NOT NULL, -- full_account, specific_data, anonymize
    data_categories JSONB, -- Array of data categories to delete
    reason TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    processed_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_deletion_requests_user ON data_deletion_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_deletion_requests_status ON data_deletion_requests(status);
CREATE INDEX IF NOT EXISTS idx_deletion_requests_time ON data_deletion_requests(requested_at DESC);

-- Data Export Requests (Data Portability)
CREATE TABLE IF NOT EXISTS data_export_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    export_format VARCHAR(20) DEFAULT 'json', -- json, csv, pdf
    data_categories JSONB, -- Array of data categories to export
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, ready, downloaded, expired
    file_url TEXT,
    file_size_bytes BIGINT,
    expires_at TIMESTAMP,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    downloaded_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_export_requests_user ON data_export_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_export_requests_status ON data_export_requests(status);
CREATE INDEX IF NOT EXISTS idx_export_requests_time ON data_export_requests(requested_at DESC);

-- Data Processing Activities
CREATE TABLE IF NOT EXISTS data_processing_activities (
    id SERIAL PRIMARY KEY,
    activity_name VARCHAR(255) NOT NULL,
    data_categories JSONB NOT NULL, -- Array of data categories processed
    processing_purpose TEXT NOT NULL,
    legal_basis VARCHAR(100) NOT NULL, -- consent, contract, legal_obligation, legitimate_interest
    data_recipients TEXT, -- Who receives the data
    retention_period VARCHAR(100),
    security_measures TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processing_activities_active ON data_processing_activities(is_active);

-- User Privacy Preferences
CREATE TABLE IF NOT EXISTS user_privacy_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    allow_analytics BOOLEAN DEFAULT TRUE,
    allow_marketing BOOLEAN DEFAULT FALSE,
    allow_data_sharing BOOLEAN DEFAULT FALSE,
    allow_location_tracking BOOLEAN DEFAULT TRUE,
    allow_call_recording BOOLEAN DEFAULT TRUE,
    data_retention_preference VARCHAR(50) DEFAULT 'standard', -- minimal, standard, extended
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default data retention policies
INSERT INTO data_retention_policies (data_category, retention_days, auto_delete, description, legal_basis) VALUES
('profile_data', 1825, FALSE, 'User profile information retained for 5 years after account deletion', 'Legal obligation for KYC compliance'),
('location_data', 90, TRUE, 'GPS location history retained for 90 days', 'User consent for family safety features'),
('call_recordings', 365, TRUE, 'Call recordings retained for 1 year', 'User consent for evidence collection'),
('call_analysis', 730, TRUE, 'Call analysis results retained for 2 years', 'Legitimate interest for improving AI models'),
('messages_scanned', 180, TRUE, 'Scanned messages retained for 6 months', 'User consent for scam detection'),
('scam_reports', 1095, FALSE, 'Scam reports retained for 3 years', 'Legal obligation for law enforcement cooperation'),
('vault_evidence', 1825, FALSE, 'Evidence vault items retained for 5 years', 'User consent for evidence preservation'),
('analytics_data', 365, TRUE, 'Usage analytics retained for 1 year', 'Legitimate interest for service improvement'),
('audit_logs', 2555, FALSE, 'Security audit logs retained for 7 years', 'Legal obligation for security compliance'),
('payment_records', 2555, FALSE, 'Payment and invoice records retained for 7 years', 'Legal obligation for tax compliance')
ON CONFLICT (data_category) DO NOTHING;

-- Insert default data processing activities
INSERT INTO data_processing_activities (activity_name, data_categories, processing_purpose, legal_basis, data_recipients, retention_period, security_measures) VALUES
(
    'AI Call Screening',
    '["call_audio", "call_transcription", "caller_id"]',
    'Real-time analysis of incoming calls to detect scam patterns and protect users from fraud',
    'consent',
    'Internal AI systems only',
    '1 year',
    'End-to-end encryption, access controls, audit logging'
),
(
    'GPS Location Tracking',
    '["gps_coordinates", "location_history"]',
    'Track user location for family safety and geofencing features',
    'consent',
    'Family members (if sharing enabled)',
    '90 days',
    'Encrypted storage, role-based access, audit logging'
),
(
    'Scam Database',
    '["phone_numbers", "scam_reports", "trust_scores"]',
    'Maintain database of reported scammers to protect all users',
    'legitimate_interest',
    'All EchoFort users (anonymized)',
    '3 years',
    'Anonymization, access controls, regular audits'
),
(
    'Evidence Vault',
    '["call_recordings", "screenshots", "messages", "documents"]',
    'Store user-submitted evidence of scams for legal proceedings',
    'consent',
    'User only (unless shared with authorities)',
    '5 years',
    'End-to-end encryption, secure storage, access logging'
),
(
    'Payment Processing',
    '["payment_details", "billing_address", "transaction_history"]',
    'Process subscription payments and maintain billing records',
    'contract',
    'Razorpay, Stripe (payment processors)',
    '7 years',
    'PCI-DSS compliance, tokenization, encrypted transmission'
),
(
    'Analytics and Improvement',
    '["usage_patterns", "feature_usage", "error_logs"]',
    'Analyze app usage to improve features and fix bugs',
    'legitimate_interest',
    'Internal analytics team only',
    '1 year',
    'Anonymization, aggregation, access controls'
)
ON CONFLICT DO NOTHING;

-- Function to check if user has given consent for a specific purpose
CREATE OR REPLACE FUNCTION check_user_consent(
    p_user_id INTEGER,
    p_consent_type VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    v_consent_given BOOLEAN;
BEGIN
    SELECT consent_given INTO v_consent_given
    FROM user_consents
    WHERE user_id = p_user_id
    AND consent_type = p_consent_type
    AND is_active = TRUE
    ORDER BY consent_date DESC
    LIMIT 1;
    
    RETURN COALESCE(v_consent_given, FALSE);
END;
$$ LANGUAGE plpgsql;

-- Function to log data access
CREATE OR REPLACE FUNCTION log_data_access(
    p_user_id INTEGER,
    p_accessed_by_user_id INTEGER,
    p_access_type VARCHAR,
    p_data_category VARCHAR,
    p_access_reason TEXT DEFAULT NULL,
    p_ip_address VARCHAR DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO data_access_logs (
        user_id,
        accessed_by_user_id,
        access_type,
        data_category,
        access_reason,
        ip_address,
        accessed_at
    ) VALUES (
        p_user_id,
        p_accessed_by_user_id,
        p_access_type,
        p_data_category,
        p_access_reason,
        p_ip_address,
        CURRENT_TIMESTAMP
    );
END;
$$ LANGUAGE plpgsql;

-- Function to automatically delete expired data
CREATE OR REPLACE FUNCTION auto_delete_expired_data() RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER := 0;
    v_policy RECORD;
BEGIN
    -- Loop through each retention policy
    FOR v_policy IN 
        SELECT * FROM data_retention_policies WHERE auto_delete = TRUE
    LOOP
        -- Delete expired data based on category
        CASE v_policy.data_category
            WHEN 'location_data' THEN
                DELETE FROM gps_locations
                WHERE recorded_at < CURRENT_TIMESTAMP - (v_policy.retention_days || ' days')::INTERVAL;
                v_deleted_count := v_deleted_count + 1;
                
            WHEN 'call_recordings' THEN
                DELETE FROM call_recordings
                WHERE created_at < CURRENT_TIMESTAMP - (v_policy.retention_days || ' days')::INTERVAL;
                v_deleted_count := v_deleted_count + 1;
                
            WHEN 'call_analysis' THEN
                DELETE FROM realtime_call_analysis
                WHERE analysis_timestamp < CURRENT_TIMESTAMP - (v_policy.retention_days || ' days')::INTERVAL;
                v_deleted_count := v_deleted_count + 1;
                
            WHEN 'messages_scanned' THEN
                DELETE FROM sms_detections
                WHERE detected_at < CURRENT_TIMESTAMP - (v_policy.retention_days || ' days')::INTERVAL;
                v_deleted_count := v_deleted_count + 1;
                
            WHEN 'analytics_data' THEN
                DELETE FROM ai_usage
                WHERE created_at < CURRENT_TIMESTAMP - (v_policy.retention_days || ' days')::INTERVAL;
                v_deleted_count := v_deleted_count + 1;
                
            ELSE
                -- Skip unknown categories
                NULL;
        END CASE;
    END LOOP;
    
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE user_consents IS 'User consent records for DPDP compliance';
COMMENT ON TABLE privacy_policy_acceptances IS 'Privacy policy acceptance tracking';
COMMENT ON TABLE data_access_logs IS 'Audit log of all data access events';
COMMENT ON TABLE data_retention_policies IS 'Data retention policies by category';
COMMENT ON TABLE data_deletion_requests IS 'User requests for data deletion (Right to be Forgotten)';
COMMENT ON TABLE data_export_requests IS 'User requests for data export (Data Portability)';
COMMENT ON TABLE data_processing_activities IS 'Record of Processing Activities (ROPA)';
COMMENT ON TABLE user_privacy_preferences IS 'User privacy preferences and settings';
COMMENT ON FUNCTION check_user_consent IS 'Check if user has given consent for a specific purpose';
COMMENT ON FUNCTION log_data_access IS 'Log data access for audit trail';
COMMENT ON FUNCTION auto_delete_expired_data IS 'Automatically delete data past retention period';
