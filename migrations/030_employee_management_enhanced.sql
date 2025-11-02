-- Enhanced Employee Management System
-- For evidence verification and support staff

CREATE TABLE IF NOT EXISTS employee_roles (
    id SERIAL PRIMARY KEY,
    role_name VARCHAR(100) NOT NULL UNIQUE,
    role_description TEXT,
    permissions JSONB, -- {view_evidence: true, verify_evidence: true, etc.}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default roles
INSERT INTO employee_roles (role_name, role_description, permissions) VALUES
('evidence_verifier', 'Verifies and processes user-submitted evidence', '{"view_evidence": true, "verify_evidence": true, "download_evidence": true, "view_call_recordings": true}'),
('support_agent', 'Handles user support tickets and queries', '{"view_users": true, "view_tickets": true, "respond_tickets": true, "view_subscriptions": true}'),
('data_analyst', 'Analyzes scam patterns and user data', '{"view_analytics": true, "view_reports": true, "export_data": true, "view_all_users": true}'),
('super_admin', 'Full system access', '{"all": true}')
ON CONFLICT (role_name) DO NOTHING;

CREATE TABLE IF NOT EXISTS employee_assignments (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES employee_roles(id) ON DELETE CASCADE,
    assigned_by INTEGER REFERENCES users(id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(employee_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_employee_assignments_employee ON employee_assignments(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_assignments_role ON employee_assignments(role_id);

-- Evidence verification workflow
CREATE TABLE IF NOT EXISTS evidence_verification_queue (
    id SERIAL PRIMARY KEY,
    evidence_id INTEGER NOT NULL,
    evidence_type VARCHAR(50) NOT NULL, -- call_recording, screenshot, document, etc.
    submitted_by INTEGER NOT NULL REFERENCES users(id),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Assignment
    assigned_to INTEGER REFERENCES users(id),
    assigned_at TIMESTAMP,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_review, verified, rejected, escalated
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    
    -- Verification
    verified_by INTEGER REFERENCES users(id),
    verified_at TIMESTAMP,
    verification_notes TEXT,
    verification_result VARCHAR(50), -- authentic, fake, inconclusive, needs_more_info
    
    -- Metadata
    scam_type VARCHAR(100),
    scam_category VARCHAR(100),
    reported_amount DECIMAL(15, 2),
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evidence_queue_status ON evidence_verification_queue(status);
CREATE INDEX IF NOT EXISTS idx_evidence_queue_assigned ON evidence_verification_queue(assigned_to);
CREATE INDEX IF NOT EXISTS idx_evidence_queue_submitter ON evidence_verification_queue(submitted_by);

-- Employee performance tracking
CREATE TABLE IF NOT EXISTS employee_performance (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Metrics
    cases_assigned INTEGER DEFAULT 0,
    cases_completed INTEGER DEFAULT 0,
    cases_verified INTEGER DEFAULT 0,
    cases_rejected INTEGER DEFAULT 0,
    average_processing_time_minutes INTEGER,
    
    -- Quality metrics
    accuracy_score DECIMAL(5, 2), -- percentage
    user_satisfaction_score DECIMAL(5, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(employee_id, date)
);

CREATE INDEX IF NOT EXISTS idx_employee_performance_employee ON employee_performance(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_performance_date ON employee_performance(date DESC);

COMMENT ON TABLE employee_roles IS 'Employee role definitions with permissions';
COMMENT ON TABLE employee_assignments IS 'Employee role assignments';
COMMENT ON TABLE evidence_verification_queue IS 'Queue for evidence verification workflow';
COMMENT ON TABLE employee_performance IS 'Employee performance metrics tracking';
