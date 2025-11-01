"""
Simple proxy endpoint for AI Pending Actions to bypass HTTP/2 CORS issues
"""

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

router = APIRouter(prefix="/proxy", tags=["proxy"])


async def get_db_engine():
    """Create async database engine"""
    database_url = os.getenv("DATABASE_URL", "")
    
    # Handle Heroku/Railway postgres:// URLs
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    return create_async_engine(database_url, echo=False)


@router.get("/ai-pending-actions")
async def get_pending_actions_proxy():
    """
    Proxy endpoint to get pending actions with inline CORS headers
    """
    try:
        engine = await get_db_engine()
        
        async with engine.begin() as conn:
            result = await conn.execute(
                text("""
                    SELECT id, action_type, description, risk_level,
                           sql_command, rollback_sql, file_path,
                           requested_at, status
                    FROM ai_pending_actions
                    WHERE status = 'pending_approval'
                    ORDER BY requested_at DESC
                """)
            )
            
            actions = []
            for row in result:
                actions.append({
                    "id": row[0],
                    "action_type": row[1],
                    "description": row[2],
                    "risk_level": row[3],
                    "sql_command": row[4],
                    "rollback_sql": row[5],
                    "file_path": row[6],
                    "requested_at": row[7].isoformat() if row[7] else None,
                    "status": row[8]
                })
        
        await engine.dispose()
        
        # Return with explicit CORS headers
        response = JSONResponse(content={"actions": actions, "count": len(actions)})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch pending actions: {str(e)}")
        response = JSONResponse(
            status_code=500,
            content={"error": str(e), "actions": [], "count": 0}
        )
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
