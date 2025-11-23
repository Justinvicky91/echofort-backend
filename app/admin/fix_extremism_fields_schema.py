"""
Admin Fix Endpoint: Add extremism fields to evidence_vault
Block 5 Step 8
"""

from fastapi import APIRouter
import psycopg
from os import getenv

router = APIRouter()


@router.post("/admin/fix/extremism-fields")
async def fix_extremism_fields_schema():
    """
    Run migration 045: Add Block 5 extremism fields to evidence_vault
    """
    try:
        dsn = getenv("DATABASE_URL")
        
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # Add new columns
                cur.execute("""
                    ALTER TABLE evidence_vault 
                    ADD COLUMN IF NOT EXISTS content_category VARCHAR(100) DEFAULT 'benign',
                    ADD COLUMN IF NOT EXISTS violence_or_extremism_risk INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;
                """)
                
                # Add indexes
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_evidence_vault_content_category 
                    ON evidence_vault(content_category);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_evidence_vault_extremism_risk 
                    ON evidence_vault(violence_or_extremism_risk DESC);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_evidence_vault_tags 
                    ON evidence_vault USING GIN(tags);
                """)
                
                # Add comments
                cur.execute("""
                    COMMENT ON COLUMN evidence_vault.content_category IS 
                    'AI-predicted content category: benign, scam_fraud, harmful_extremism, hate_speech, self_harm_risk, etc. NOT a legal determination.';
                """)
                
                cur.execute("""
                    COMMENT ON COLUMN evidence_vault.violence_or_extremism_risk IS 
                    'AI-predicted risk score 0-10 for violent or extremist content. NOT a legal determination.';
                """)
                
                cur.execute("""
                    COMMENT ON COLUMN evidence_vault.tags IS 
                    'Array of AI-generated tags for detailed classification. NOT legal labels.';
                """)
                
                conn.commit()
        
        return {
            "ok": True,
            "message": "Migration 045 applied successfully - extremism fields added to evidence_vault",
            "columns_added": ["content_category", "violence_or_extremism_risk", "tags"]
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }
