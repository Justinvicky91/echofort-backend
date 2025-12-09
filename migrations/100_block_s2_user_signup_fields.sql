-- BLOCK S2: Add missing fields for User Signup + OTP + Subscription Entitlements
-- This migration adds all fields needed for the complete user account system

-- Add missing user fields for signup and subscription management
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS name VARCHAR(255),
ADD COLUMN IF NOT EXISTS phone VARCHAR(20),
ADD COLUMN IF NOT EXISTS otp_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS plan_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(50) DEFAULT 'inactive',
ADD COLUMN IF NOT EXISTS dashboard_type VARCHAR(50);

-- Add indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON users(subscription_status);
CREATE INDEX IF NOT EXISTS idx_users_plan_id ON users(plan_id);

-- Update OTP table to add user_id reference (if not exists)
ALTER TABLE otps
ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id);

CREATE INDEX IF NOT EXISTS idx_otps_user_id ON otps(user_id);
CREATE INDEX IF NOT EXISTS idx_otps_expires_at ON otps(expires_at);

-- Add comment
COMMENT ON TABLE users IS 'User accounts with signup, OTP verification, and subscription entitlements';
COMMENT ON COLUMN users.otp_verified IS 'Whether user has verified their email/phone via OTP';
COMMENT ON COLUMN users.plan_id IS 'Subscription plan: basic, personal, or family';
COMMENT ON COLUMN users.subscription_status IS 'Subscription status: inactive, active, expired, cancelled';
COMMENT ON COLUMN users.dashboard_type IS 'Dashboard type: dashboard_basic, dashboard_personal, dashboard_family_admin, dashboard_family_member';
