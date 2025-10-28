-- Promo Code System Migration
-- Created: Oct 28, 2025
-- Purpose: Referral/Promo code system with 10% discount and commission tracking

-- Promo Codes Table
CREATE TABLE IF NOT EXISTS promo_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    discount_percentage DECIMAL(5,2) NOT NULL DEFAULT 10.00,
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_by_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    max_uses INTEGER DEFAULT NULL, -- NULL = unlimited
    current_uses INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    applicable_plans TEXT[] DEFAULT ARRAY['Personal', 'Family'], -- Which plans can use this code
    notes TEXT,
    CONSTRAINT valid_discount CHECK (discount_percentage >= 0 AND discount_percentage <= 100)
);

-- Promo Code Usage Table
CREATE TABLE IF NOT EXISTS promo_code_usage (
    id SERIAL PRIMARY KEY,
    promo_code_id INTEGER REFERENCES promo_codes(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE SET NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    original_amount DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) NOT NULL,
    final_amount DECIMAL(10,2) NOT NULL,
    commission_amount DECIMAL(10,2) NOT NULL, -- 10% of final amount goes to referrer
    commission_paid BOOLEAN DEFAULT FALSE,
    commission_paid_at TIMESTAMP,
    CONSTRAINT valid_amounts CHECK (
        original_amount >= final_amount AND
        final_amount >= 0 AND
        discount_amount >= 0 AND
        commission_amount >= 0
    )
);

-- Add promo_code_id to subscriptions table
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS promo_code_id INTEGER REFERENCES promo_codes(id) ON DELETE SET NULL;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS discount_applied DECIMAL(10,2) DEFAULT 0.00;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);
CREATE INDEX IF NOT EXISTS idx_promo_codes_created_by ON promo_codes(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_promo_codes_active ON promo_codes(is_active);
CREATE INDEX IF NOT EXISTS idx_promo_code_usage_promo ON promo_code_usage(promo_code_id);
CREATE INDEX IF NOT EXISTS idx_promo_code_usage_user ON promo_code_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_promo_code_usage_subscription ON promo_code_usage(subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_promo_code ON subscriptions(promo_code_id);

-- Sample promo codes (for testing)
INSERT INTO promo_codes (code, discount_percentage, created_by_name, notes, max_uses)
VALUES 
    ('WELCOME10', 10.00, 'System', 'Welcome offer for new users', NULL),
    ('FAMILY2025', 10.00, 'System', 'Family plan promotion 2025', 1000)
ON CONFLICT (code) DO NOTHING;

COMMENT ON TABLE promo_codes IS 'Stores promotional codes for discounts and referral tracking';
COMMENT ON TABLE promo_code_usage IS 'Tracks usage of promo codes and commission calculations';
COMMENT ON COLUMN promo_codes.applicable_plans IS 'Array of plan names that can use this promo code';
COMMENT ON COLUMN promo_code_usage.commission_amount IS 'Commission paid to referrer (10% of final amount)';
