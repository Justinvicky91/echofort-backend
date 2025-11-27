"""
Temporary Migration Helper for Block 14 & 15
Applies migrations 050 (AI Learning Center) and 051 (Threat Intelligence) to production database.
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import psycopg
import os

router = APIRouter(prefix="/admin/apply-block14-15-migrations", tags=["Migration Helper"])

@router.post("/run")
async def apply_block14_15_migrations():
    """
    Apply Block 14 & 15 migrations (050, 051) to the production database.
    Idempotent and safe to run multiple times.
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
            "050_ai_learning_center.sql",
            "051_threat_intelligence.sql"
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
                # If error is "already exists", that's OK (idempotent)
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
        
        # Verify Block 14 tables exist
        verification = {}
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                # Block 14 tables
                for table_name in ["ai_conversations", "ai_decisions", "ai_daily_digests", "ai_learning_patterns"]:
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
                
                # Block 15 tables
                for table_name in ["threat_intelligence_scans", "threat_intelligence_items", "threat_patterns", "threat_alerts"]:
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
            "message": "Block 14 & 15 migrations applied. Verify the results above."
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )

@router.get("/verify")
async def verify_block14_15_tables():
    """
    Verify that Block 14 & 15 tables exist and return row counts.
    Read-only verification endpoint.
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
                # Block 14 tables
                for table_name in ["ai_conversations", "ai_decisions", "ai_daily_digests", "ai_learning_patterns"]:
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
                
                # Block 15 tables
                for table_name in ["threat_intelligence_scans", "threat_intelligence_items", "threat_patterns", "threat_alerts"]:
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
