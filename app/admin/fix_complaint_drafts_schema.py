"""
Admin endpoint to manually create complaint_drafts table
"""
from fastapi import APIRouter, Depends
from app.utils import require_super_admin
from app.deps import get_settings
import psycopg

router = APIRouter(prefix="/admin/fix", tags=["admin-fix"])

@router.post("/complaint-drafts-schema")
def fix_complaint_drafts_schema(user: dict = Depends(require_super_admin)):
    """
    Manually create complaint_drafts table with correct schema.
    Safe to run multiple times (uses IF NOT EXISTS).
    """
    
    sql = """
-- Create complaint_drafts table
CREATE TABLE IF NOT EXISTS complaint_drafts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    scam_type VARCHAR(100) NOT NULL,
    recipient_type VARCHAR(50) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    certificate_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',
    
    created_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_complaint_drafts_user ON complaint_drafts(user_id);
CREATE INDEX IF NOT EXISTS idx_complaint_drafts_certificate ON complaint_drafts(certificate_id);
CREATE INDEX IF NOT EXISTS idx_complaint_drafts_status ON complaint_drafts(status);
CREATE INDEX IF NOT EXISTS idx_complaint_drafts_created ON complaint_drafts(created_at DESC);
"""
    
    settings = get_settings()
    dsn = settings.DATABASE_URL.replace("postgresql://", "postgresql://", 1)
    
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        
        return {
            "success": True,
            "message": "complaint_drafts table created successfully",
            "table": "complaint_drafts"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
