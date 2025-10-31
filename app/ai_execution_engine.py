"""
EchoFort AI Execution Engine
Allows AI to propose and execute changes with Super Admin approval
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import json

router = APIRouter(prefix="/api/ai-execution", tags=["AI Execution"])


class PendingAction(BaseModel):
    action_type: str
    description: str
    risk_level: str
    sql_command: Optional[str] = None
    rollback_sql: Optional[str] = None
    file_path: Optional[str] = None
    code_changes: Optional[Dict] = None
    package_name: Optional[str] = None
    package_version: Optional[str] = None


class ActionApproval(BaseModel):
    action_id: int
    approved: bool
    notes: Optional[str] = None


async def get_db_engine():
    """Get async database engine"""
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise Exception("DATABASE_URL not configured")
    
    # Convert postgres:// or postgresql:// to postgresql+asyncpg://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    return create_async_engine(database_url)


async def propose_action(action: PendingAction) -> dict:
    """
    Store a proposed action for Super Admin approval
    """
    engine = await get_db_engine()
    
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                INSERT INTO ai_pending_actions (
                    action_type, description, risk_level,
                    sql_command, rollback_sql,
                    file_path, code_changes,
                    package_name, package_version,
                    status, requested_by, requested_at
                )
                VALUES (
                    :action_type, :description, :risk_level,
                    :sql_command, :rollback_sql,
                    :file_path, :code_changes,
                    :package_name, :package_version,
                    'pending_approval', 'echofort_ai', CURRENT_TIMESTAMP
                )
                RETURNING id
            """),
            {
                "action_type": action.action_type,
                "description": action.description,
                "risk_level": action.risk_level,
                "sql_command": action.sql_command,
                "rollback_sql": action.rollback_sql,
                "file_path": action.file_path,
                "code_changes": json.dumps(action.code_changes) if action.code_changes else None,
                "package_name": action.package_name,
                "package_version": action.package_version
            }
        )
        
        action_id = result.fetchone()[0]
    
    await engine.dispose()
    
    return {
        "action_id": action_id,
        "status": "pending_approval",
        "message": f"Action #{action_id} submitted for Super Admin approval"
    }


async def execute_sql_action(action_id: int, sql_command: str, rollback_sql: Optional[str] = None) -> dict:
    """
    Execute approved SQL command
    """
    engine = await get_db_engine()
    
    try:
        async with engine.begin() as conn:
            # Execute the SQL command
            await conn.execute(text(sql_command))
            
            # Update action status
            await conn.execute(
                text("""
                    UPDATE ai_pending_actions
                    SET status = 'executed',
                        executed_at = CURRENT_TIMESTAMP,
                        execution_result = :result
                    WHERE id = :action_id
                """),
                {
                    "action_id": action_id,
                    "result": '{"status": "success", "message": "SQL executed successfully"}'
                }
            )
        
        await engine.dispose()
        
        return {
            "status": "success",
            "message": "SQL command executed successfully",
            "action_id": action_id
        }
    
    except Exception as e:
        # Update action status to failed
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    UPDATE ai_pending_actions
                    SET status = 'failed',
                        error_message = :error
                    WHERE id = :action_id
                """),
                {
                    "action_id": action_id,
                    "error": str(e)
                }
            )
        
        await engine.dispose()
        
        return {
            "status": "failed",
            "message": f"SQL execution failed: {str(e)}",
            "action_id": action_id
        }


@router.get("/pending-actions")
async def get_pending_actions():
    """
    Get all pending actions awaiting approval
    """
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
    
    return {"actions": actions, "count": len(actions)}


@router.post("/approve-action")
async def approve_action(approval: ActionApproval):
    """
    Approve or reject a pending action
    """
    engine = await get_db_engine()
    
    # Get action details
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT action_type, sql_command, rollback_sql, status
                FROM ai_pending_actions
                WHERE id = :action_id
            """),
            {"action_id": approval.action_id}
        )
        
        row = result.fetchone()
        if not row:
            await engine.dispose()
            raise HTTPException(status_code=404, detail="Action not found")
        
        action_type, sql_command, rollback_sql, status = row
        
        if status != 'pending_approval':
            await engine.dispose()
            raise HTTPException(status_code=400, detail=f"Action already {status}")
    
    if approval.approved:
        # Execute the action
        if action_type == "sql_execution":
            result = await execute_sql_action(approval.action_id, sql_command, rollback_sql)
            return result
        else:
            # For other action types, mark as approved (to be implemented)
            async with engine.begin() as conn:
                await conn.execute(
                    text("""
                        UPDATE ai_pending_actions
                        SET status = 'approved',
                            reviewed_at = CURRENT_TIMESTAMP,
                            reviewed_by = 'super_admin'
                        WHERE id = :action_id
                    """),
                    {"action_id": approval.action_id}
                )
            
            await engine.dispose()
            
            return {
                "status": "approved",
                "message": f"Action #{approval.action_id} approved (execution pending)",
                "action_id": approval.action_id
            }
    else:
        # Reject the action
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    UPDATE ai_pending_actions
                    SET status = 'rejected',
                        reviewed_at = CURRENT_TIMESTAMP,
                        reviewed_by = 'super_admin'
                    WHERE id = :action_id
                """),
                {"action_id": approval.action_id}
            )
        
        await engine.dispose()
        
        return {
            "status": "rejected",
            "message": f"Action #{approval.action_id} rejected",
            "action_id": approval.action_id
        }


@router.get("/action-history")
async def get_action_history(limit: int = 50):
    """
    Get history of all actions (approved, rejected, executed, failed)
    """
    engine = await get_db_engine()
    
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT id, action_type, description, risk_level,
                       status, requested_at, reviewed_at, executed_at,
                       error_message
                FROM ai_pending_actions
                ORDER BY requested_at DESC
                LIMIT :limit
            """),
            {"limit": limit}
        )
        
        actions = []
        for row in result:
            actions.append({
                "id": row[0],
                "action_type": row[1],
                "description": row[2],
                "risk_level": row[3],
                "status": row[4],
                "requested_at": row[5].isoformat() if row[5] else None,
                "reviewed_at": row[6].isoformat() if row[6] else None,
                "executed_at": row[7].isoformat() if row[7] else None,
                "error_message": row[8]
            })
    
    await engine.dispose()
    
    return {"actions": actions, "count": len(actions)}
