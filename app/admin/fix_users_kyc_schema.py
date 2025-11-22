"""
Admin endpoint to manually add KYC fields to users table
This bypasses the broken migration system
"""
from fastapi import APIRouter, Depends
from app.utils import require_super_admin
from app.deps import get_settings
import psycopg

router = APIRouter(prefix="/admin/fix", tags=["admin-fix"])

@router.post("/users-kyc-schema")
def fix_users_kyc_schema(user: dict = Depends(require_super_admin)):
    """
    Manually add KYC and address fields to users table.
    This endpoint bypasses the broken migration system.
    """
    
    sql = """
-- Add KYC and address fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS full_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS address_line1 VARCHAR(500),
ADD COLUMN IF NOT EXISTS address_line2 VARCHAR(500),
ADD COLUMN IF NOT EXISTS city VARCHAR(100),
ADD COLUMN IF NOT EXISTS district VARCHAR(100),
ADD COLUMN IF NOT EXISTS state VARCHAR(100),
ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'India',
ADD COLUMN IF NOT EXISTS pincode VARCHAR(20),
ADD COLUMN IF NOT EXISTS id_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS id_number VARCHAR(100),
ADD COLUMN IF NOT EXISTS id_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS kyc_status VARCHAR(50) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS kyc_verified_at TIMESTAMP;

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_kyc_status ON users(kyc_status);
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
            "message": "Users KYC schema updated successfully",
            "details": {
                "action": "ALTER TABLE users - added KYC fields",
                "columns_added": [
                    "full_name", "address_line1", "address_line2", 
                    "city", "district", "state", "country", "pincode",
                    "id_type", "id_number", "id_verified", 
                    "kyc_status", "kyc_verified_at"
                ]
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": "Failed to update users KYC schema"
        }
