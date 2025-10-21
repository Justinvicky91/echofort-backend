-- Migration 011: AI Pending Tasks Table
-- For EchoFort AI autonomous command execution with approval workflow

CREATE TABLE IF NOT EXISTS ai_pending_tasks (
    task_id SERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL DEFAULT 1,
    command TEXT NOT NULL,
    action_type VARCHAR(50) NOT NULL CHECK (action_type IN ('code_change', 'marketing', 'database', 'infrastructure', 'analysis', 'error', 'unknown')),
    description TEXT NOT NULL,
    code TEXT,
    sql TEXT,
    files_to_modify TEXT,
    preview TEXT,
    estimated_impact VARCHAR(20) CHECK (estimated_impact IN ('High', 'Medium', 'Low', 'None', 'Unknown')),
    risks TEXT,
    benefits TEXT,
    requires_approval BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'completed', 'failed')),
    admin_feedback TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    executed_at TIMESTAMP,
    CONSTRAINT valid_status_transition CHECK (
        (status = 'pending') OR
        (status = 'approved' AND approved_at IS NOT NULL) OR
        (status = 'rejected') OR
        (status = 'completed' AND executed_at IS NOT NULL) OR
        (status = 'failed')
    )
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ai_pending_tasks_status ON ai_pending_tasks(status);
CREATE INDEX IF NOT EXISTS idx_ai_pending_tasks_created_at ON ai_pending_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_pending_tasks_action_type ON ai_pending_tasks(action_type);

-- Add comment
COMMENT ON TABLE ai_pending_tasks IS 'Stores EchoFort AI autonomous commands awaiting Super Admin approval';

