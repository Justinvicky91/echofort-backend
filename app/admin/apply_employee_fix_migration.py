"""
Apply Migration 053: Add name and email columns to employees table
Block P0-LAUNCH-FIX Task 3
"""

from fastapi import APIRouter, HTTPException
import psycopg2
import os
from pathlib import Path

router = APIRouter(prefix="/admin/apply-employee-fix-migration", tags=["Migrations"])

@router.post("")
async def apply_employee_fix_migration():
    """
    Apply migration 053: Add name and email columns to employees table
    
    This fixes the P0 blocker where Customer Hub shows N/A for employee names and emails.
    """
    try:
        # Read migration file
        base = Path(__file__).resolve().parents[2]
        migration_file = base / "migrations" / "053_add_employee_name_email.sql"
        
        if not migration_file.exists():
            raise HTTPException(500, f"Migration file not found: {migration_file}")
        
        sql = migration_file.read_text(encoding="utf-8")
        
        # Execute migration
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            
            return {
                "success": True,
                "message": "Migration 053 applied successfully",
                "migration": "053_add_employee_name_email.sql",
                "changes": [
                    "Added 'name' column to employees table",
                    "Added 'email' column to employees table",
                    "Populated name and email for existing employees",
                    "Added unique index on email column"
                ]
            }
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(500, f"Migration failed: {str(e)}")
