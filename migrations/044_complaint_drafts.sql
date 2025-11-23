-- Migration 044: Create Complaint Drafts Table
-- Created: 2025-11-23
-- Purpose: Store complaint drafts generated for users

CREATE TABLE IF NOT EXISTS complaint_drafts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    scam_type VARCHAR(100) NOT NULL,
    recipient_type VARCHAR(50) NOT NULL, -- bank, cybercrime
    recipient_email VARCHAR(255) NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    certificate_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'draft', -- draft, sent, archived
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_complaint_drafts_user ON complaint_drafts(user_id);
CREATE INDEX IF NOT EXISTS idx_complaint_drafts_certificate ON complaint_drafts(certificate_id);
CREATE INDEX IF NOT EXISTS idx_complaint_drafts_status ON complaint_drafts(status);
CREATE INDEX IF NOT EXISTS idx_complaint_drafts_created ON complaint_drafts(created_at DESC);

COMMENT ON TABLE complaint_drafts IS 'Complaint email drafts generated for users (not auto-sent)';
COMMENT ON COLUMN complaint_drafts.certificate_id IS 'Unique EchoFort certificate ID for tracking';
