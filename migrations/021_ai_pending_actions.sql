-- Migration: AI Pending Actions Table
-- Purpose: Store AI-proposed changes that require Super Admin approval
-- Date: 2025-10-31

CREATE TABLE IF NOT EXISTS ai_pending_actions (
    id SERIAL PRIMARY KEY,
    
    -- Action details
    action_type VARCHAR(50) NOT NULL, -- 'sql_execution', 'code_modification', 'migration', 'package_install'
    description TEXT NOT NULL,
    risk_level VARCHAR(20) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    
    -- For SQL execution
    sql_command TEXT,
    rollback_sql TEXT,
    
    -- For code modification
    file_path TEXT,
    code_changes JSONB,
    
    -- For package installation
    package_name VARCHAR(200),
    package_version VARCHAR(50),
    
    -- Approval workflow
    status VARCHAR(30) DEFAULT 'pending_approval', 
    -- Status values: 'pending_approval', 'approved', 'rejected', 'executed', 'failed', 'rolled_back'
    
    requested_by VARCHAR(100) DEFAULT 'echofort_ai',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    executed_at TIMESTAMP,
    
    -- Results
    execution_result JSONB,
    error_message TEXT,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_ai_pending_actions_status ON ai_pending_actions(status);
CREATE INDEX IF NOT EXISTS idx_ai_pending_actions_requested_at ON ai_pending_actions(requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_pending_actions_risk_level ON ai_pending_actions(risk_level);

-- Add comment
COMMENT ON TABLE ai_pending_actions IS 'Stores AI-proposed changes that require Super Admin approval before execution';
