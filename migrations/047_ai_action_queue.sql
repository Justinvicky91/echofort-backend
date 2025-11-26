-- Migration 047: AI Action Queue
-- Purpose: Create table for AI-proposed actions with human approval workflow
-- Block: 8 (AI Command Center)
-- Date: 2025-11-26

-- Create ai_action_queue table
CREATE TABLE IF NOT EXISTS ai_action_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255) DEFAULT 'EchoFortAI',
    type VARCHAR(100) NOT NULL,  -- 'config_change', 'pattern_update', 'infra_suggestion', 'investigate_anomaly'
    target VARCHAR(255) NOT NULL,  -- 'Block5Config', 'sms_patterns', 'railway_backend', etc.
    payload JSONB NOT NULL,  -- The actual change data
    impact_summary TEXT NOT NULL,  -- Human-readable explanation
    status VARCHAR(50) DEFAULT 'PENDING',  -- 'PENDING', 'APPROVED', 'REJECTED', 'EXECUTED', 'FAILED'
    approved_by UUID REFERENCES users(id),  -- Super Admin who approved
    approved_at TIMESTAMP WITH TIME ZONE,
    executed_by VARCHAR(255),  -- 'ExecutionEngineV1', etc.
    executed_at TIMESTAMP WITH TIME ZONE,
    error_log TEXT,  -- Stores any errors from failed executions
    CONSTRAINT valid_status CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXECUTED', 'FAILED')),
    CONSTRAINT valid_type CHECK (type IN ('config_change', 'pattern_update', 'infra_suggestion', 'investigate_anomaly'))
);

-- Create indexes for common queries
CREATE INDEX idx_ai_action_queue_status ON ai_action_queue(status);
CREATE INDEX idx_ai_action_queue_created_at ON ai_action_queue(created_at DESC);
CREATE INDEX idx_ai_action_queue_type ON ai_action_queue(type);
CREATE INDEX idx_ai_action_queue_approved_by ON ai_action_queue(approved_by);

-- Add comment to table
COMMENT ON TABLE ai_action_queue IS 'AI-proposed actions requiring human approval before execution';
COMMENT ON COLUMN ai_action_queue.type IS 'Type of action: config_change, pattern_update, infra_suggestion, investigate_anomaly';
COMMENT ON COLUMN ai_action_queue.target IS 'Target service or component for the action';
COMMENT ON COLUMN ai_action_queue.payload IS 'JSON data containing the actual change details';
COMMENT ON COLUMN ai_action_queue.impact_summary IS 'Human-readable explanation of what this action will do';
COMMENT ON COLUMN ai_action_queue.status IS 'Current status: PENDING (awaiting approval), APPROVED (ready to execute), REJECTED, EXECUTED, FAILED';
