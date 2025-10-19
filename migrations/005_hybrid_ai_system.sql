-- migrations/005_hybrid_ai_system.sql
-- Hybrid AI System: OpenAI + Self-Learning + Internet Monitoring

-- ============================================================================
-- INTERNET SCAM INTELLIGENCE
-- ============================================================================

CREATE TABLE IF NOT EXISTS scam_intelligence (
    id SERIAL PRIMARY KEY,
    scam_type VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    severity VARCHAR(20),
    defense_method TEXT,
    source VARCHAR(255),
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scam_severity 
ON scam_intelligence(severity, discovered_at DESC);

COMMENT ON TABLE scam_intelligence IS 'Internet-scraped scam data updated daily';

-- ============================================================================
-- AI LEARNING DATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_learning_data (
    id SERIAL PRIMARY KEY,
    user_question TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    context_data JSONB,
    model_used VARCHAR(50) DEFAULT 'gpt-4',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_learning_created 
ON ai_learning_data(created_at DESC);

COMMENT ON TABLE ai_learning_data IS 'OpenAI responses stored for transition to autonomous AI';

-- ============================================================================
-- APP VERSION TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS app_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE NOT NULL,
    release_notes TEXT,
    scams_addressed TEXT[],
    released_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE app_versions IS 'Mobile app versions for update tracking';

-- ============================================================================
-- ERROR LOGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    error_type VARCHAR(100),
    error_message TEXT,
    endpoint VARCHAR(255),
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_error_logs_created 
ON error_logs(created_at DESC);

COMMENT ON TABLE error_logs IS 'Platform errors for AI health monitoring';

-- ============================================================================
-- EMAIL LOGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_logs (
    id SERIAL PRIMARY KEY,
    recipient VARCHAR(255),
    email_type VARCHAR(50),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_logs_sent 
ON email_logs(sent_at DESC);

COMMENT ON TABLE email_logs IS 'Email tracking for SendGrid cost monitoring';

-- ============================================================================
-- ADD SUBSCRIPTION_PLAN TO USERS
-- ============================================================================

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='users' AND column_name='subscription_plan'
    ) THEN
        ALTER TABLE users ADD COLUMN subscription_plan VARCHAR(50);
    END IF;
END $$;

-- ============================================================================
-- INSERT SAMPLE SCAM DATA (with CURRENT_TIMESTAMP)
-- ============================================================================

-- Delete any existing scam data to ensure fresh timestamps
DELETE FROM scam_intelligence;

-- Insert sample scam data with CURRENT_TIMESTAMP
INSERT INTO scam_intelligence (scam_type, description, severity, defense_method, source, discovered_at, last_seen)
VALUES 
    ('AI Voice Clone Scam', 'Scammers use AI to clone family member voices and request emergency money', 'critical', 'Always verify by calling back on known number. Use family code word.', 'cybercrime.gov.in', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('UPI Refund Scam', 'Fake customer service asking for UPI PIN to process refund', 'high', 'Never share UPI PIN. Banks never ask for it.', 'rbi.org.in', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('Deepfake Video Call Scam', 'Video calls with deepfake of CEO/family member requesting money transfer', 'critical', 'Ask questions only real person would know. Verify through another channel.', 'fbi.gov', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- ============================================================================
-- OPTIMIZATION
-- ============================================================================

ANALYZE scam_intelligence;
ANALYZE ai_learning_data;
ANALYZE error_logs;
ANALYZE email_logs;
