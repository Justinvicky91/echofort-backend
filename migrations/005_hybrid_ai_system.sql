-- 005_hybrid_ai_system.sql
-- Hybrid AI: OpenAI + Self-Learning + Internet Monitoring

-- Internet scam intelligence
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

CREATE INDEX IF NOT EXISTS idx_scam_severity ON scam_intelligence(severity, discovered_at DESC);

-- AI learning data (stores OpenAI responses for future)
CREATE TABLE IF NOT EXISTS ai_learning_data (
    id SERIAL PRIMARY KEY,
    user_question TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    context_data JSONB,
    model_used VARCHAR(50) DEFAULT 'gpt-4',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_learning_created ON ai_learning_data(created_at DESC);

-- App versions tracking
CREATE TABLE IF NOT EXISTS app_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE NOT NULL,
    release_notes TEXT,
    scams_addressed TEXT[],
    released_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Error logs
CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    error_type VARCHAR(100),
    error_message TEXT,
    endpoint VARCHAR(255),
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_error_logs_created ON error_logs(created_at DESC);

-- Email logs (for cost tracking)
CREATE TABLE IF NOT EXISTS email_logs (
    id SERIAL PRIMARY KEY,
    recipient VARCHAR(255),
    email_type VARCHAR(50),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add subscription_plan if doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='subscription_plan') THEN
        ALTER TABLE users ADD COLUMN subscription_plan VARCHAR(50);
    END IF;
END $$;

COMMENT ON TABLE scam_intelligence IS 'Internet-scraped scam data updated daily';
COMMENT ON TABLE ai_learning_data IS 'OpenAI responses for transition to autonomous AI';
