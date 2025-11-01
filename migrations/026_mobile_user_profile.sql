-- Mobile User Profile System
-- Extended user profile management for mobile app

-- User Profiles (Extended)
CREATE TABLE IF NOT EXISTS user_profiles_mobile (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    avatar_url TEXT,
    bio TEXT,
    date_of_birth DATE,
    gender VARCHAR(20),
    country VARCHAR(100),
    city VARCHAR(100),
    timezone VARCHAR(50),
    language_preference VARCHAR(10) DEFAULT 'en',
    theme_preference VARCHAR(20) DEFAULT 'light', -- light, dark, auto
    notification_sound BOOLEAN DEFAULT TRUE,
    vibration_enabled BOOLEAN DEFAULT TRUE,
    biometric_enabled BOOLEAN DEFAULT FALSE,
    auto_backup_enabled BOOLEAN DEFAULT TRUE,
    data_saver_mode BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Preferences (App-specific)
CREATE TABLE IF NOT EXISTS user_app_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    default_call_action VARCHAR(20) DEFAULT 'ask', -- ask, block, allow
    auto_record_calls BOOLEAN DEFAULT FALSE,
    auto_scan_sms BOOLEAN DEFAULT TRUE,
    auto_check_urls BOOLEAN DEFAULT TRUE,
    show_caller_id BOOLEAN DEFAULT TRUE,
    block_unknown_callers BOOLEAN DEFAULT FALSE,
    block_private_numbers BOOLEAN DEFAULT FALSE,
    enable_call_recording_notification BOOLEAN DEFAULT TRUE,
    enable_scam_prediction BOOLEAN DEFAULT TRUE,
    enable_ai_assistant BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Activity Log
CREATE TABLE IF NOT EXISTS user_activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL, -- login, logout, profile_update, settings_change, etc.
    activity_details JSONB,
    ip_address VARCHAR(45),
    device_info JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_activity_log_user ON user_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_type ON user_activity_log(activity_type);
CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON user_activity_log(timestamp DESC);

-- User Sessions (Mobile)
CREATE TABLE IF NOT EXISTS user_sessions_mobile (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token TEXT NOT NULL UNIQUE,
    device_id VARCHAR(255),
    device_name VARCHAR(255),
    platform VARCHAR(20), -- ios, android
    app_version VARCHAR(50),
    ip_address VARCHAR(45),
    location_country VARCHAR(100),
    location_city VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions_mobile(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions_mobile(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions_mobile(is_active);

-- User Avatars (for upload tracking)
CREATE TABLE IF NOT EXISTS user_avatars (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(50),
    is_current BOOLEAN DEFAULT TRUE,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_avatars_user ON user_avatars(user_id);

-- User Feedback
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    feedback_type VARCHAR(50) NOT NULL, -- bug, feature_request, complaint, praise, other
    category VARCHAR(100),
    subject VARCHAR(255),
    message TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    platform VARCHAR(20),
    app_version VARCHAR(50),
    status VARCHAR(20) DEFAULT 'new', -- new, in_progress, resolved, closed
    admin_response TEXT,
    responded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_user ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON user_feedback(status);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON user_feedback(feedback_type);

-- User Achievements/Badges
CREATE TABLE IF NOT EXISTS user_achievements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_type VARCHAR(100) NOT NULL,
    achievement_name VARCHAR(255) NOT NULL,
    achievement_description TEXT,
    icon_url TEXT,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, achievement_type)
);

CREATE INDEX IF NOT EXISTS idx_achievements_user ON user_achievements(user_id);

-- User Statistics Summary
CREATE TABLE IF NOT EXISTS user_statistics_summary (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    total_scams_blocked INTEGER DEFAULT 0,
    total_calls_protected INTEGER DEFAULT 0,
    total_sms_scanned INTEGER DEFAULT 0,
    total_urls_checked INTEGER DEFAULT 0,
    total_reports_submitted INTEGER DEFAULT 0,
    protection_score INTEGER DEFAULT 0 CHECK (protection_score >= 0 AND protection_score <= 100),
    community_reputation INTEGER DEFAULT 50 CHECK (community_reputation >= 0 AND community_reputation <= 100),
    days_active INTEGER DEFAULT 0,
    last_active_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Function to log user activity
CREATE OR REPLACE FUNCTION log_user_activity(
    p_user_id INTEGER,
    p_activity_type VARCHAR(50),
    p_activity_details JSONB DEFAULT NULL,
    p_ip_address VARCHAR(45) DEFAULT NULL,
    p_device_info JSONB DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_activity_id INTEGER;
BEGIN
    INSERT INTO user_activity_log 
    (user_id, activity_type, activity_details, ip_address, device_info)
    VALUES (p_user_id, p_activity_type, p_activity_details, p_ip_address, p_device_info)
    RETURNING id INTO v_activity_id;
    
    RETURN v_activity_id;
END;
$$ LANGUAGE plpgsql;

-- Function to update user statistics
CREATE OR REPLACE FUNCTION update_user_statistics(
    p_user_id INTEGER
) RETURNS VOID AS $$
BEGIN
    INSERT INTO user_statistics_summary (user_id)
    VALUES (p_user_id)
    ON CONFLICT (user_id) DO UPDATE
    SET 
        total_scams_blocked = (
            SELECT COUNT(*) FROM call_history 
            WHERE user_id = p_user_id AND was_blocked = true
        ) + (
            SELECT COUNT(*) FROM sms_threats 
            WHERE user_id = p_user_id AND is_scam = true AND action_taken = 'block'
        ),
        total_calls_protected = (
            SELECT COUNT(*) FROM call_history 
            WHERE user_id = p_user_id
        ),
        total_sms_scanned = (
            SELECT COALESCE(total_sms_scanned, 0) FROM sms_statistics 
            WHERE user_id = p_user_id
        ),
        total_urls_checked = (
            SELECT COALESCE(urls_checked, 0) FROM url_check_statistics 
            WHERE user_id = p_user_id
        ),
        total_reports_submitted = (
            SELECT COUNT(*) FROM caller_id_reports 
            WHERE reported_by = p_user_id
        ) + (
            SELECT COUNT(*) FROM sms_scam_reports 
            WHERE reported_by = p_user_id
        ),
        last_active_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Insert default achievements
INSERT INTO user_achievements (user_id, achievement_type, achievement_name, achievement_description, icon_url)
SELECT 
    id,
    'first_login',
    'Welcome Aboard!',
    'Completed first login to EchoFort',
    '/icons/achievements/welcome.png'
FROM users
WHERE NOT EXISTS (
    SELECT 1 FROM user_achievements 
    WHERE user_id = users.id AND achievement_type = 'first_login'
)
LIMIT 0; -- Don't actually insert, just define the pattern

COMMENT ON TABLE user_profiles_mobile IS 'Extended user profiles for mobile app';
COMMENT ON TABLE user_app_preferences IS 'App-specific user preferences';
COMMENT ON TABLE user_activity_log IS 'User activity tracking';
COMMENT ON TABLE user_sessions_mobile IS 'Mobile app sessions';
COMMENT ON TABLE user_avatars IS 'User avatar upload history';
COMMENT ON TABLE user_feedback IS 'User feedback and support requests';
COMMENT ON TABLE user_achievements IS 'User achievements and badges';
COMMENT ON TABLE user_statistics_summary IS 'Aggregated user statistics';
