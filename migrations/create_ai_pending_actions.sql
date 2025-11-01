-- Create ai_pending_actions table for AI execution engine
CREATE TABLE IF NOT EXISTS ai_pending_actions (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    risk_level VARCHAR(50) NOT NULL,
    sql_command TEXT,
    rollback_command TEXT,
    affected_tables TEXT[],
    estimated_impact TEXT,
    status VARCHAR(50) DEFAULT 'pending_approval',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by INTEGER,
    executed_at TIMESTAMP,
    execution_result TEXT,
    notes TEXT
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_ai_pending_actions_status ON ai_pending_actions(status);
CREATE INDEX IF NOT EXISTS idx_ai_pending_actions_created_at ON ai_pending_actions(created_at DESC);

COMMENT ON TABLE ai_pending_actions IS 'Stores AI-proposed fixes awaiting Super Admin approval';
COMMENT ON COLUMN ai_pending_actions.action_type IS 'Type of action: sql_execution, configuration, data_insertion, etc.';
COMMENT ON COLUMN ai_pending_actions.risk_level IS 'Risk level: low, medium, high, critical';
COMMENT ON COLUMN ai_pending_actions.status IS 'Status: pending_approval, approved, rejected, executed, failed';
