# app/admin/execute_sql.py
# TEMPORARY SQL execution endpoint for database setup

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import os
import psycopg

router = APIRouter(prefix="/admin", tags=["admin"])

class SQLRequest(BaseModel):
    sql: str

@router.post("/execute-sql")
async def execute_sql(request: Request, key: str, sql_req: SQLRequest):
    """
    TEMPORARY endpoint to execute raw SQL
    DELETE THIS AFTER DATABASE SETUP IS COMPLETE
    """
    # Security check
    if key != "EchoFort9176":
        raise HTTPException(403, "Invalid key")
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        raise HTTPException(500, "DATABASE_URL not found")
    
    # Convert to psycopg format
    db_url = db_url.replace("postgresql://", "postgresql://").replace("+psycopg", "").replace("+asyncpg", "")
    
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # Execute the SQL
                cur.execute(sql_req.sql)
                conn.commit()
                
                return {"ok": True, "message": "SQL executed successfully"}
    except Exception as e:
        raise HTTPException(500, f"SQL execution failed: {str(e)}")