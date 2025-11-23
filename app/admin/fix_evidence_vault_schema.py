"""
Admin endpoint to manually create evidence_vault table
This bypasses the migration system for immediate deployment
"""
from fastapi import APIRouter, Depends
from app.utils import require_super_admin
from app.deps import get_settings
import psycopg

router = APIRouter(prefix="/admin/fix", tags=["admin-fix"])

@router.post("/evidence-vault-schema")
def fix_evidence_vault_schema(user: dict = Depends(require_super_admin)):
    """
    Manually create evidence_vault table with correct schema.
    This endpoint bypasses the migration system for immediate deployment.
    
    Safe to run multiple times (uses IF NOT EXISTS).
    """
    
    sql = """
-- Create evidence_vault table
CREATE TABLE IF NOT EXISTS evidence_vault (
    id SERIAL PRIMARY KEY,
    evidence_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    family_member_id VARCHAR(255),
    purchase_person_id VARCHAR(255),
    
    -- Evidence type and details
    evidence_type VARCHAR(50) NOT NULL,
    
    -- Call recording specific fields
    caller_number VARCHAR(50),
    duration INTEGER,
    recording_url TEXT,
    threat_level INTEGER,
    scam_type VARCHAR(100),
    ai_analysis JSONB,
    
    -- Location data
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    address TEXT,
    
    -- EchoFort seal and retention
    echofort_seal TEXT,
    retention_expiry TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_evidence_vault_user ON evidence_vault(user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_evidence_id ON evidence_vault(evidence_id);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_type ON evidence_vault(evidence_type);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_scam_type ON evidence_vault(scam_type);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_threat_level ON evidence_vault(threat_level);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_created ON evidence_vault(created_at DESC);
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
            "message": "evidence_vault table created successfully",
            "table": "evidence_vault"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
