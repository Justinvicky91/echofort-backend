-- Migration 052: AI Web Logs
-- Track internet search activity for EchoFort AI

CREATE TABLE IF NOT EXISTS ai_web_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    query TEXT NOT NULL,
    category VARCHAR(50),  -- scam_fraud, harassment, child_safety, extremism, marketing_competitor, generic
    results_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_web_logs_user_id ON ai_web_logs(user_id);
CREATE INDEX idx_ai_web_logs_created_at ON ai_web_logs(created_at DESC);
CREATE INDEX idx_ai_web_logs_category ON ai_web_logs(category);

COMMENT ON TABLE ai_web_logs IS 'Tracks internet search activity by EchoFort AI';
COMMENT ON COLUMN ai_web_logs.category IS 'Search category for enhanced queries';
