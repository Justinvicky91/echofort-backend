"""
Manual migration runner endpoint
"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text

router = APIRouter(prefix="/admin", tags=["Migration"])

@router.post("/run-mobile-migration")
async def run_mobile_migration(request: Request):
    """
    Manually run the mobile users schema migration
    """
    try:
        db = request.app.state.db
        
        migration_sql = """
        -- Add mobile user columns to users table
        ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(100) UNIQUE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
        ALTER TABLE users ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT true;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

        -- Create index for faster lookups
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);
        """
        
        await db.execute(text(migration_sql))
        
        return {
            "ok": True,
            "message": "Mobile users schema migration completed successfully"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Migration failed: {str(e)}")
