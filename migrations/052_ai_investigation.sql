-- Migration 052: AI Investigation & Evidence Ops
-- Created: 2025-11-28
-- Description: Case management, investigation workflows, and evidence linking

-- 1. Investigation Cases Table
CREATE TABLE IF NOT EXISTS investigation_cases (
    id SERIAL PRIMARY KEY,
    case_number VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    case_type VARCHAR(50) NOT NULL, -- 'harassment', 'scam', 'fraud', 'threat', 'other'
    status VARCHAR(50) NOT NULL DEFAULT 'open', -- 'open', 'investigating', 'pending_evidence', 'resolved', 'closed'
    priority VARCHAR(20) NOT NULL DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    assigned_to INTEGER REFERENCES users(id),
    created_by INTEGER REFERENCES users(id),
    victim_user_id INTEGER REFERENCES users(id),
    suspect_phone VARCHAR(20),
    suspect_name VARCHAR(255),
    suspect_details JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_summary TEXT
);

-- 2. Investigation Timeline Table
CREATE TABLE IF NOT EXISTS investigation_timeline (
    id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES investigation_cases(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- 'created', 'status_change', 'evidence_added', 'note_added', 'action_taken', 'resolved'
    event_description TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Investigation Evidence Links Table
CREATE TABLE IF NOT EXISTS investigation_evidence (
    id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES investigation_cases(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL, -- 'call', 'message', 'screenshot', 'document', 'url', 'other'
    evidence_id INTEGER, -- Foreign key to evidence vault items
    evidence_description TEXT,
    evidence_metadata JSONB DEFAULT '{}',
    added_by INTEGER REFERENCES users(id),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Investigation Notes Table
CREATE TABLE IF NOT EXISTS investigation_notes (
    id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES investigation_cases(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    note_type VARCHAR(50) DEFAULT 'general', -- 'general', 'important', 'ai_insight', 'action_item'
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. AI Investigation Actions Table (links to AI Action Queue)
CREATE TABLE IF NOT EXISTS ai_investigation_actions (
    id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES investigation_cases(id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL, -- 'block_number', 'flag_user', 'collect_evidence', 'notify_authorities', etc.
    action_description TEXT NOT NULL,
    action_data JSONB DEFAULT '{}',
    proposed_by VARCHAR(50) DEFAULT 'ai', -- 'ai' or 'user'
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'completed'
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Investigation Statistics Table
CREATE TABLE IF NOT EXISTS investigation_statistics (
    id SERIAL PRIMARY KEY,
    stat_date DATE UNIQUE NOT NULL,
    total_cases INTEGER DEFAULT 0,
    cases_opened INTEGER DEFAULT 0,
    cases_resolved INTEGER DEFAULT 0,
    cases_by_type JSONB DEFAULT '{}',
    avg_resolution_time_hours DECIMAL(10, 2),
    evidence_items_collected INTEGER DEFAULT 0,
    ai_actions_proposed INTEGER DEFAULT 0,
    ai_actions_approved INTEGER DEFAULT 0,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_investigation_cases_status ON investigation_cases(status);
CREATE INDEX IF NOT EXISTS idx_investigation_cases_created ON investigation_cases(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_investigation_cases_victim ON investigation_cases(victim_user_id);
CREATE INDEX IF NOT EXISTS idx_investigation_timeline_case ON investigation_timeline(case_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_investigation_evidence_case ON investigation_evidence(case_id);
CREATE INDEX IF NOT EXISTS idx_investigation_notes_case ON investigation_notes(case_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_investigation_actions_case ON ai_investigation_actions(case_id);
CREATE INDEX IF NOT EXISTS idx_ai_investigation_actions_status ON ai_investigation_actions(status);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_investigation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER investigation_cases_updated
    BEFORE UPDATE ON investigation_cases
    FOR EACH ROW
    EXECUTE FUNCTION update_investigation_timestamp();

CREATE TRIGGER investigation_notes_updated
    BEFORE UPDATE ON investigation_notes
    FOR EACH ROW
    EXECUTE FUNCTION update_investigation_timestamp();

-- Insert sample data for testing
INSERT INTO investigation_statistics (stat_date, total_cases, cases_opened, cases_resolved, cases_by_type, avg_resolution_time_hours, evidence_items_collected, ai_actions_proposed, ai_actions_approved)
VALUES (CURRENT_DATE - INTERVAL '1 day', 15, 5, 3, '{"harassment": 8, "scam": 5, "fraud": 2}', 48.5, 42, 12, 8)
ON CONFLICT (stat_date) DO NOTHING;

-- Migration complete
