-- Migration 020: Fix AI Learning Table Schema
-- Drops and recreates ai_learning table with correct schema

DROP TABLE IF EXISTS ai_learning CASCADE;

CREATE TABLE ai_learning (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(255) NOT NULL,
    information TEXT NOT NULL,
    source VARCHAR(255),
    confidence FLOAT,
    requires_approval BOOLEAN DEFAULT true,
    approved BOOLEAN DEFAULT false,
    approved_by VARCHAR(255),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_learning_approval ON ai_learning(requires_approval, approved);
CREATE INDEX idx_ai_learning_created ON ai_learning(created_at DESC);

COMMENT ON TABLE ai_learning IS 'AI learning entries requiring Super Admin approval';
COMMENT ON COLUMN ai_learning.confidence IS 'Confidence level (0.0 to 1.0)';
