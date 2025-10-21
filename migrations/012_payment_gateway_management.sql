-- Migration 012: Payment Gateway Management System
-- Super Admin can configure multiple payment gateways without code deployment

-- Payment gateways configuration table
CREATE TABLE IF NOT EXISTS payment_gateways (
    id SERIAL PRIMARY KEY,
    gateway_name VARCHAR(50) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    test_mode BOOLEAN DEFAULT FALSE,
    api_key_encrypted TEXT NOT NULL,
    secret_key_encrypted TEXT NOT NULL,
    webhook_secret_encrypted TEXT,
    supported_currencies JSONB DEFAULT '[]'::jsonb,
    supported_regions JSONB DEFAULT '[]'::jsonb,
    priority INTEGER DEFAULT 999,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id)
);

-- Admin audit log table (if not exists)
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_payment_gateways_enabled ON payment_gateways(enabled);
CREATE INDEX IF NOT EXISTS idx_payment_gateways_priority ON payment_gateways(priority);
CREATE INDEX IF NOT EXISTS idx_payment_gateways_regions ON payment_gateways USING GIN(supported_regions);
CREATE INDEX IF NOT EXISTS idx_payment_gateways_currencies ON payment_gateways USING GIN(supported_currencies);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_admin ON admin_audit_log(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_action ON admin_audit_log(action);

-- Insert default payment gateways (disabled by default, admin needs to configure)
INSERT INTO payment_gateways (gateway_name, enabled, test_mode, api_key_encrypted, secret_key_encrypted, supported_currencies, supported_regions, priority)
VALUES 
    ('razorpay', FALSE, TRUE, 'CONFIGURE_IN_ADMIN_PANEL', 'CONFIGURE_IN_ADMIN_PANEL', '["INR"]'::jsonb, '["IN"]'::jsonb, 1),
    ('stripe', FALSE, TRUE, 'CONFIGURE_IN_ADMIN_PANEL', 'CONFIGURE_IN_ADMIN_PANEL', '["USD", "EUR", "GBP", "AUD", "CAD"]'::jsonb, '["US", "GB", "EU", "AU", "CA"]'::jsonb, 2),
    ('paypal', FALSE, TRUE, 'CONFIGURE_IN_ADMIN_PANEL', 'CONFIGURE_IN_ADMIN_PANEL', '["USD", "EUR", "GBP"]'::jsonb, '["US", "GB", "EU"]'::jsonb, 3),
    ('square', FALSE, TRUE, 'CONFIGURE_IN_ADMIN_PANEL', 'CONFIGURE_IN_ADMIN_PANEL', '["USD", "GBP", "AUD"]'::jsonb, '["US", "GB", "AU"]'::jsonb, 4),
    ('adyen', FALSE, TRUE, 'CONFIGURE_IN_ADMIN_PANEL', 'CONFIGURE_IN_ADMIN_PANEL', '["EUR", "USD", "GBP"]'::jsonb, '["EU", "US", "GB"]'::jsonb, 5),
    ('alipay', FALSE, TRUE, 'CONFIGURE_IN_ADMIN_PANEL', 'CONFIGURE_IN_ADMIN_PANEL', '["CNY", "USD"]'::jsonb, '["CN"]'::jsonb, 6),
    ('wechat', FALSE, TRUE, 'CONFIGURE_IN_ADMIN_PANEL', 'CONFIGURE_IN_ADMIN_PANEL', '["CNY"]'::jsonb, '["CN"]'::jsonb, 7)
ON CONFLICT (gateway_name) DO NOTHING;

-- Comments
COMMENT ON TABLE payment_gateways IS 'Payment gateway configurations managed by Super Admin';
COMMENT ON COLUMN payment_gateways.api_key_encrypted IS 'Encrypted API key using Fernet encryption';
COMMENT ON COLUMN payment_gateways.secret_key_encrypted IS 'Encrypted secret key using Fernet encryption';
COMMENT ON COLUMN payment_gateways.priority IS 'Lower number = higher priority (1 = highest)';
COMMENT ON TABLE admin_audit_log IS 'Audit log for all admin actions';

