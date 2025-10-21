-- Migration 015: Call Recording Vault & Customer Exemptions
-- Created: 2025-10-21

-- Admin settings table (for vault password and other settings)
CREATE TABLE IF NOT EXISTS admin_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id)
);

-- Add encryption fields to call_recordings table
ALTER TABLE call_recordings
ADD COLUMN IF NOT EXISTS encrypted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS encryption_salt VARCHAR(255),
ADD COLUMN IF NOT EXISTS vault_protected BOOLEAN DEFAULT true;

-- Customer exemptions table
CREATE TABLE IF NOT EXISTS customer_exemptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    exemption_type VARCHAR(50) NOT NULL, -- vip, partner, test, other
    reason TEXT,
    subscription_tier VARCHAR(50) DEFAULT 'family_pack',
    granted_by INTEGER REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP, -- NULL = permanent
    active BOOLEAN DEFAULT true,
    revoked_at TIMESTAMP,
    revoked_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add exemption fields to subscriptions table
ALTER TABLE subscriptions
ADD COLUMN IF NOT EXISTS is_exempt BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS exempt_reason TEXT;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_exemptions_user ON customer_exemptions(user_id);
CREATE INDEX IF NOT EXISTS idx_exemptions_active ON customer_exemptions(active);
CREATE INDEX IF NOT EXISTS idx_exemptions_expires ON customer_exemptions(expires_at);
CREATE INDEX IF NOT EXISTS idx_admin_settings_key ON admin_settings(key);

-- Insert default admin settings
INSERT INTO admin_settings (key, value) VALUES
('vault_enabled', 'true'),
('vault_password_set', 'false')
ON CONFLICT (key) DO NOTHING;

COMMENT ON TABLE admin_settings IS 'Super admin configuration settings';
COMMENT ON TABLE customer_exemptions IS 'VIP/exempt customers who get free access';
COMMENT ON COLUMN call_recordings.encrypted IS 'Whether this recording is encrypted with vault password';
COMMENT ON COLUMN call_recordings.vault_protected IS 'Whether this recording requires vault password to access';

