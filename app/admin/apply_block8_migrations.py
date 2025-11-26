"""
Temporary Migration Helper for Block 8
Block 9 Step 2.1

This endpoint applies migrations 047, 048, 049 to the production database.
It is idempotent and safe to run multiple times.

SECURITY: This endpoint should be disabled after use.
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import psycopg
import os

router = APIRouter(prefix="/admin/apply-block8-migrations", tags=["Migration Helper"])

@router.post("/run")
async def apply_block8_migrations():
    """
    Apply Block 8 migrations (047, 048, 049) to the production database.
    
    This is a temporary endpoint for Block 9 Step 2.1.
    It should be disabled or removed after successful migration.
    
    Returns:
        dict: Status of each migration
    """
    try:
        # Get database URL from environment
        database_url = os.getenv("DATABASE_URL", "")
        if database_url.startswith("postgresql+psycopg://"):
            database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        # Define migrations to apply
        migrations = [
            "047_ai_action_queue.sql",
            "048_ai_pattern_library.sql",
            "049_ai_investigation_tasks.sql"
        ]
        
        results = {}
        
        # Get migrations directory
        base = Path(__file__).resolve().parents[2]
        mdir = base / "migrations"
        
        # Apply each migration in a separate transaction
        for fname in migrations:
            try:
                migration_path = mdir / fname
                
                if not migration_path.exists():
                    results[fname] = {
                        "success": False,
                        "error": f"Migration file not found: {migration_path}"
                    }
                    continue
                
                # Read migration SQL
                sql = migration_path.read_text(encoding="utf-8")
                
                # Execute migration in its own transaction
                with psycopg.connect(database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql)
                        conn.commit()
                
                results[fname] = {
                    "success": True,
                    "message": "Migration applied successfully"
                }
                
            except Exception as e:
                # If error is "table already exists", that's OK (idempotent)
                error_msg = str(e)
                if "already exists" in error_msg.lower():
                    results[fname] = {
                        "success": True,
                        "message": "Migration already applied (table exists)",
                        "note": error_msg
                    }
                else:
                    results[fname] = {
                        "success": False,
                        "error": error_msg
                    }
                    # Don't stop on error, continue with next migration
        
        # Verify tables exist
        verification = {}
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                for table_name in ["ai_action_queue", "ai_pattern_library", "ai_investigation_tasks"]:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {table_name};")
                        count = cur.fetchone()[0]
                        verification[table_name] = {
                            "exists": True,
                            "row_count": count
                        }
                    except Exception as e:
                        verification[table_name] = {
                            "exists": False,
                            "error": str(e)
                        }
        
        return {
            "success": True,
            "migrations": results,
            "verification": verification,
            "message": "Block 8 migrations applied. Verify the results above."
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )

@router.get("/verify")
async def verify_block8_tables():
    """
    Verify that Block 8 tables exist and return row counts.
    
    This is a read-only verification endpoint.
    """
    try:
        database_url = os.getenv("DATABASE_URL", "")
        if database_url.startswith("postgresql+psycopg://"):
            database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        verification = {}
        
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                for table_name in ["ai_action_queue", "ai_pattern_library", "ai_investigation_tasks"]:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {table_name};")
                        count = cur.fetchone()[0]
                        verification[table_name] = {
                            "exists": True,
                            "row_count": count
                        }
                    except Exception as e:
                        verification[table_name] = {
                            "exists": False,
                            "error": str(e)
                        }
        
        return {
            "success": True,
            "tables": verification
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )
