"""
Admin endpoint to apply BLOCK S2 schema changes
Adds fields for User Signup + OTP + Subscription Entitlements
"""
from fastapi import APIRouter, Depends
from app.utils import require_super_admin
from app.deps import get_settings
import psycopg

router = APIRouter(prefix="/admin/fix", tags=["admin-fix"])

@router.post("/block-s2-schema")
def fix_block_s2_schema(user: dict = Depends(require_super_admin)):
    """
    Apply BLOCK S2 schema changes to users and otps tables.
    Adds fields needed for signup, OTP verification, and subscription entitlements.
    """
    
    sql = """
-- BLOCK S2: Add missing fields for User Signup + OTP + Subscription Entitlements

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
            "message": "BLOCK S2 schema updated successfully",
            "details": {
                "action": "ALTER TABLE users, otps - added signup and subscription fields",
                "users_columns_added": [
                    "name", "phone", "otp_verified", 
                    "plan_id", "subscription_status", "dashboard_type"
                ],
                "otps_columns_added": ["user_id"],
                "indexes_created": [
                    "idx_users_email", "idx_users_phone", 
                    "idx_users_subscription_status", "idx_users_plan_id",
                    "idx_otps_user_id", "idx_otps_expires_at"
                ]
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": "Failed to update BLOCK S2 schema"
        }
