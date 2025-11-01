"""
Server-Side Rendered AI Pending Actions Page
Bypasses HTTP/2 CORS issues by rendering HTML directly on the backend
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

router = APIRouter(prefix="/admin", tags=["admin"])


async def get_db_engine():
    """Create async database engine"""
    database_url = os.getenv("DATABASE_URL", "")
    
    # Handle Heroku/Railway postgres:// URLs
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    return create_async_engine(database_url, echo=False)


@router.get("/ai-pending-actions-data", response_class=HTMLResponse)
async def get_pending_actions_ssr():
    """
    Server-side rendered pending actions page
    Returns HTML with embedded data - no CORS issues
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
        
        # Generate HTML with embedded JSON data
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI Pending Actions Data</title>
    <script>
        // Expose data to parent window
        window.aiPendingActionsData = {actions};
        
        // Send data to parent if in iframe
        if (window.parent !== window) {{
            window.parent.postMessage({{
                type: 'AI_PENDING_ACTIONS_DATA',
                data: {actions}
            }}, '*');
        }}
    </script>
</head>
<body>
    <pre>{len(actions)} pending actions loaded</pre>
</body>
</html>
"""
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch pending actions: {str(e)}")
        error_html = f"""
<!DOCTYPE html>
<html>
<head><title>Error</title></head>
<body>
    <pre>Error: {str(e)}</pre>
    <script>
        window.aiPendingActionsData = [];
        if (window.parent !== window) {{
            window.parent.postMessage({{
                type: 'AI_PENDING_ACTIONS_ERROR',
                error: '{str(e)}'
            }}, '*');
        }}
    </script>
</body>
</html>
"""
        return HTMLResponse(content=error_html, status_code=500)
