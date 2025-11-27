"""
Block 16 Migration Helper
Manually apply Block 16 (AI Investigation) migrations
"""

from fastapi import APIRouter, HTTPException
import os
import psycopg
from pathlib import Path

router = APIRouter()

@router.post("/admin/apply-block16-migrations/run")
async def apply_block16_migrations():
    """Apply Block 16 (AI Investigation) migrations manually"""
    try:
        # Get database connection
        conn = psycopg.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        
        # Read migration file
        base = Path(__file__).resolve().parents[2]
        migration_file = base / "migrations" / "052_ai_investigation.sql"
        
        if not migration_file.exists():
            raise HTTPException(status_code=404, detail="Migration file not found")
        
        migration_sql = migration_file.read_text(encoding="utf-8")
        
        # Execute migration
        cur.execute(migration_sql)
        conn.commit()
        
        # Verify tables exist
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('investigation_cases', 'investigation_timeline', 
                              'investigation_evidence', 'investigation_notes',
                              'ai_investigation_actions', 'investigation_statistics')
            ORDER BY table_name
        """)
        
        tables = [row[0] for row in cur.fetchall()]
        
        # Get row counts
        table_counts = {}
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            table_counts[table] = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Block 16 migrations applied successfully",
            "tables_created": tables,
            "table_counts": table_counts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/apply-block16-migrations/status")
async def check_migration_status():
    """Check if Block 16 migrations have been applied"""
    try:
        conn = psycopg.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        
        # Check if tables exist
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('investigation_cases', 'investigation_timeline', 
                              'investigation_evidence', 'investigation_notes',
                              'ai_investigation_actions', 'investigation_statistics')
            ORDER BY table_name
        """)
        
        tables = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return {
            "success": True,
            "tables_exist": tables,
            "migration_complete": len(tables) == 6
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
