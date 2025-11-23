"""
Admin Fix Endpoint: Create user_consent_log table
Block 5 Step 7
"""

from fastapi import APIRouter
import psycopg
from os import getenv

router = APIRouter()


@router.post("/admin/fix/user-consent-log")
async def fix_user_consent_log_schema():
    """
    Create user_consent_log table if it doesn't exist
    """
    try:
        dsn = getenv("DATABASE_URL")
        
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # Create table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_consent_log (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        terms_version VARCHAR(50) NOT NULL,
                        privacy_version VARCHAR(50) NOT NULL,
                        consent_type VARCHAR(100) NOT NULL,
                        consent_channel VARCHAR(50) NOT NULL,
                        ip_address VARCHAR(100),
                        user_agent TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create indexes
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_consent_user_id 
                    ON user_consent_log(user_id);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_consent_timestamp 
                    ON user_consent_log(timestamp);
                """)
                
                # Add comment
                cur.execute("""
                    COMMENT ON TABLE user_consent_log IS 
                    'Block 5: Tracks user consent to Terms & Privacy versions for DPDP compliance and legal defense';
                """)
                
                conn.commit()
        
        return {
            "ok": True,
            "message": "user_consent_log table created successfully",
            "table": "user_consent_log"
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }
