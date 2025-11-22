-- Fix: Ensure user_activity_log table exists with proper schema
-- This migration is idempotent and can be run multiple times safely

-- User Activity Log (with enhanced schema for admin stats)
CREATE TABLE IF NOT EXISTS user_activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(100) NOT NULL,
    activity_details TEXT,
    ip_address VARCHAR(45),
    device_info TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for performance (CREATE INDEX IF NOT EXISTS is idempotent)
CREATE INDEX IF NOT EXISTS idx_user_activity_log_user_id ON user_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_activity_type ON user_activity_log(activity_type);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_timestamp ON user_activity_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_user_timestamp ON user_activity_log(user_id, timestamp DESC);

-- Comment
COMMENT ON TABLE user_activity_log IS 'Tracks all user activities across the platform for analytics and monitoring';
