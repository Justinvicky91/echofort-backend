"""
Block 24F - Apply password_reset_tokens table migration
"""

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text
from pathlib import Path

router = APIRouter(prefix="/admin", tags=["migrations"])

@router.post("/apply-block24f-migration")
async def apply_block24f_migration(request: Request):
    """
    Apply Block 24F migration: Create password_reset_tokens table
    """
    try:
        db = request.app.state.db
        
        # Read migration file
        migration_file = Path(__file__).parent.parent.parent / "migrations" / "024_password_reset_tokens.sql"
        
        if not migration_file.exists():
            raise HTTPException(500, f"Migration file not found: {migration_file}")
        
        migration_sql = migration_file.read_text()
        
        print("=" * 70)
        print("APPLYING BLOCK 24F MIGRATION")
        print("=" * 70)
        print(migration_sql)
        print("=" * 70)
        
        # Execute migration
        await db.execute(text(migration_sql))
        
        # Verify table was created
        result = await db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'password_reset_tokens'
        """))
        
        table_exists = result.fetchone()
        
        if not table_exists:
            raise HTTPException(500, "Migration executed but table not found")
        
        print("✅ Block 24F migration applied successfully")
        
        return {
            "success": True,
            "message": "Block 24F migration applied: password_reset_tokens table created",
            "migration_file": str(migration_file)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise HTTPException(500, f"Migration failed: {str(e)}")
