"""
Fix endpoint to create missing mobile profile tables and stored procedures
"""

from fastapi import APIRouter, Depends
from app.utils import require_super_admin
from app.deps import get_settings
import psycopg

router = APIRouter(prefix="/admin/fix", tags=["admin-fix"])


@router.post("/mobile-profile-schema")
def fix_mobile_profile_schema(user: dict = Depends(require_super_admin)):
    """
    Create missing tables and stored procedures for mobile profile endpoints
    """
    
    sql = """
-- 1. Create user_profiles_mobile table
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
    theme_preference VARCHAR(20) DEFAULT 'light',
    notification_sound BOOLEAN DEFAULT TRUE,
    vibration_enabled BOOLEAN DEFAULT TRUE,
    biometric_enabled BOOLEAN DEFAULT FALSE,
    auto_backup_enabled BOOLEAN DEFAULT TRUE,
    data_saver_mode BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create user_app_preferences table
CREATE TABLE IF NOT EXISTS user_app_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    default_call_action VARCHAR(20) DEFAULT 'ask',
    auto_record_calls BOOLEAN DEFAULT FALSE,
    auto_scan_sms BOOLEAN DEFAULT TRUE,
    auto_check_urls BOOLEAN DEFAULT TRUE,
    show_caller_id BOOLEAN DEFAULT TRUE,
    block_unknown_callers BOOLEAN DEFAULT FALSE,
    block_private_numbers BOOLEAN DEFAULT FALSE,
    enable_call_recording_notification BOOLEAN DEFAULT TRUE,
    enable_scam_prediction BOOLEAN DEFAULT TRUE,
    enable_ai_assistant BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create user_feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    feedback_type VARCHAR(50) NOT NULL,
    category VARCHAR(50),
    subject VARCHAR(200),
    message TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create user_achievements table
CREATE TABLE IF NOT EXISTS user_achievements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_type VARCHAR(50) NOT NULL,
    achievement_name VARCHAR(100) NOT NULL,
    achievement_description TEXT,
    icon_url TEXT,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, achievement_type, achievement_name)
);

-- 5. Create user_statistics_summary table
CREATE TABLE IF NOT EXISTS user_statistics_summary (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    total_scams_blocked INTEGER DEFAULT 0,
    total_calls_protected INTEGER DEFAULT 0,
    total_sms_scanned INTEGER DEFAULT 0,
    total_urls_checked INTEGER DEFAULT 0,
    total_reports_submitted INTEGER DEFAULT 0,
    protection_score INTEGER DEFAULT 0,
    community_reputation INTEGER DEFAULT 50,
    days_active INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Create log_user_activity stored procedure
CREATE OR REPLACE FUNCTION log_user_activity(
    p_user_id INTEGER,
    p_activity_type VARCHAR,
    p_activity_details JSONB,
    p_ip_address VARCHAR,
    p_device_info JSONB
) RETURNS VOID AS $$
BEGIN
    INSERT INTO user_activity_log (user_id, activity_type, activity_details, ip_address, device_info)
    VALUES (p_user_id, p_activity_type, p_activity_details, p_ip_address, p_device_info);
END;
$$ LANGUAGE plpgsql;

-- 7. Create update_user_statistics stored procedure
CREATE OR REPLACE FUNCTION update_user_statistics(p_user_id INTEGER) RETURNS VOID AS $$
BEGIN
    -- Insert or update user statistics
    INSERT INTO user_statistics_summary (user_id, last_updated)
    VALUES (p_user_id, CURRENT_TIMESTAMP)
    ON CONFLICT (user_id) DO UPDATE
    SET last_updated = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;
"""
    
    try:
        settings = get_settings()
        dsn = settings.DATABASE_URL
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        
        return {
            "ok": True,
            "message": "Mobile profile schema created successfully",
            "tables_created": [
                "user_profiles_mobile",
                "user_app_preferences",
                "user_feedback",
                "user_achievements",
                "user_statistics_summary"
            ],
            "functions_created": [
                "log_user_activity",
                "update_user_statistics"
            ]
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": "Failed to create mobile profile schema"
        }
