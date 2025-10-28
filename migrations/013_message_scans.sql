-- Migration: Message Scanning System
-- Created: Oct 28, 2025
-- Purpose: Store WhatsApp/SMS/Telegram message scans for evidence

CREATE TABLE IF NOT EXISTS message_scans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL, -- 'whatsapp', 'sms', 'telegram'
    sender_phone VARCHAR(20),
    sender_name VARCHAR(255),
    message_text TEXT NOT NULL,
    threat_level INTEGER NOT NULL CHECK (threat_level >= 0 AND threat_level <= 10),
    scam_type VARCHAR(100), -- 'digital_arrest', 'investment', 'loan_harassment', etc.
    confidence INTEGER NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    red_flags JSONB, -- Array of detected red flags
    is_scam BOOLEAN DEFAULT FALSE,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_message_scans_user_id ON message_scans(user_id);
CREATE INDEX IF NOT EXISTS idx_message_scans_platform ON message_scans(platform);
CREATE INDEX IF NOT EXISTS idx_message_scans_threat_level ON message_scans(threat_level);
CREATE INDEX IF NOT EXISTS idx_message_scans_is_scam ON message_scans(is_scam);
CREATE INDEX IF NOT EXISTS idx_message_scans_scanned_at ON message_scans(scanned_at DESC);

-- Comments
COMMENT ON TABLE message_scans IS 'Stores WhatsApp/SMS/Telegram message scans for scam detection';
COMMENT ON COLUMN message_scans.threat_level IS 'Threat level from 0 (safe) to 10 (critical)';
COMMENT ON COLUMN message_scans.confidence IS 'Confidence percentage (0-100) of scam detection';
