-- Migration 050: AI Learning Center
-- Purpose: Store AI conversations, decisions, and daily digests for learning and improvement

-- Table: ai_conversations
-- Stores all AI chat conversations with full context
CREATE TABLE IF NOT EXISTS ai_conversations (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR(50) NOT NULL, -- 'founder', 'admin', 'employee'
    message_type VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
    message_text TEXT NOT NULL,
    message_metadata JSONB DEFAULT '{}', -- {tools_used, actions_created, source_refs, etc.}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_conversations_session ON ai_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_user ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_created ON ai_conversations(created_at DESC);

-- Table: ai_decisions
-- Tracks all AI decisions and their outcomes for learning
CREATE TABLE IF NOT EXISTS ai_decisions (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT REFERENCES ai_conversations(id) ON DELETE CASCADE,
    decision_type VARCHAR(100) NOT NULL, -- 'action_proposal', 'data_query', 'recommendation', 'alert'
    decision_context JSONB NOT NULL, -- {query, tools_used, data_analyzed, reasoning}
    decision_outcome JSONB DEFAULT '{}', -- {action_id, status, user_feedback, effectiveness}
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    was_approved BOOLEAN DEFAULT NULL, -- NULL if not yet reviewed, TRUE/FALSE after review
    user_feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_decisions_type ON ai_decisions(decision_type);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_approved ON ai_decisions(was_approved);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_created ON ai_decisions(created_at DESC);

-- Table: ai_daily_digests
-- Stores daily summaries of AI activity and insights
CREATE TABLE IF NOT EXISTS ai_daily_digests (
    id BIGSERIAL PRIMARY KEY,
    digest_date DATE NOT NULL UNIQUE,
    total_conversations INT DEFAULT 0,
    total_decisions INT DEFAULT 0,
    decisions_approved INT DEFAULT 0,
    decisions_rejected INT DEFAULT 0,
    top_queries JSONB DEFAULT '[]', -- [{query, count, avg_confidence}]
    key_insights JSONB DEFAULT '[]', -- [{insight, category, importance}]
    platform_health_summary JSONB DEFAULT '{}', -- {uptime, errors, performance}
    recommendations JSONB DEFAULT '[]', -- [{recommendation, priority, reasoning}]
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_daily_digests_date ON ai_daily_digests(digest_date DESC);

-- Table: ai_learning_patterns
-- Stores learned patterns from past interactions for improving future responses
CREATE TABLE IF NOT EXISTS ai_learning_patterns (
    id BIGSERIAL PRIMARY KEY,
    pattern_type VARCHAR(100) NOT NULL, -- 'query_pattern', 'decision_pattern', 'user_preference'
    pattern_data JSONB NOT NULL, -- {query_template, expected_tools, typical_outcome}
    success_rate DECIMAL(5,2) DEFAULT 0.00, -- Percentage of successful outcomes
    usage_count INT DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_learning_patterns_type ON ai_learning_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_ai_learning_patterns_success ON ai_learning_patterns(success_rate DESC);

-- Insert sample data for testing
INSERT INTO ai_daily_digests (digest_date, total_conversations, total_decisions, key_insights, recommendations)
VALUES (
    CURRENT_DATE - INTERVAL '1 day',
    12,
    5,
    '[
        {"insight": "Digital Arrest scams increased 45% this week", "category": "threat_detection", "importance": "high"},
        {"insight": "Family Pack subscriptions show 34% higher retention", "category": "revenue", "importance": "medium"}
    ]'::jsonb,
    '[
        {"recommendation": "Consider promotional campaign for Family Pack", "priority": "high", "reasoning": "Higher retention indicates strong product-market fit"},
        {"recommendation": "Increase monitoring for Digital Arrest scam patterns", "priority": "critical", "reasoning": "45% increase in threat activity"}
    ]'::jsonb
) ON CONFLICT (digest_date) DO NOTHING;
