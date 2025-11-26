-- Migration 049: AI Investigation Tasks
-- Purpose: Store investigation tasks created by AI for human review
-- Block: 8 (AI Command Center - Phase 4)
-- Date: 2025-11-26

-- Create ai_investigation_tasks table
CREATE TABLE IF NOT EXISTS ai_investigation_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255) DEFAULT 'EchoFortAI',
    target VARCHAR(255) NOT NULL,  -- What needs investigation (e.g., 'churn_rate', 'refund_spike')
    details JSONB NOT NULL,  -- Investigation details and context
    status VARCHAR(50) DEFAULT 'PENDING',  -- 'PENDING', 'IN_PROGRESS', 'RESOLVED', 'DISMISSED'
    assigned_to BIGINT REFERENCES users(id),  -- Admin assigned to investigate
    assigned_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,  -- Notes from the investigation
    CONSTRAINT valid_status CHECK (status IN ('PENDING', 'IN_PROGRESS', 'RESOLVED', 'DISMISSED'))
);

-- Create indexes for common queries
CREATE INDEX idx_ai_investigation_tasks_status ON ai_investigation_tasks(status);
CREATE INDEX idx_ai_investigation_tasks_created_at ON ai_investigation_tasks(created_at DESC);
CREATE INDEX idx_ai_investigation_tasks_assigned_to ON ai_investigation_tasks(assigned_to);

-- Add comments to table
COMMENT ON TABLE ai_investigation_tasks IS 'Investigation tasks created by AI for human review';
COMMENT ON COLUMN ai_investigation_tasks.target IS 'What needs investigation (e.g., churn_rate, refund_spike, anomaly)';
COMMENT ON COLUMN ai_investigation_tasks.details IS 'JSON data containing investigation context and metrics';
COMMENT ON COLUMN ai_investigation_tasks.status IS 'Current status: PENDING, IN_PROGRESS, RESOLVED, DISMISSED';
COMMENT ON COLUMN ai_investigation_tasks.assigned_to IS 'Admin assigned to investigate this task';
COMMENT ON COLUMN ai_investigation_tasks.resolution_notes IS 'Notes from the investigation and resolution';
