"""
AI Execution Engine Trigger API
Block 8 Phase 4

Provides endpoints to manually trigger the execution engine
and view execution results.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_execution_engine_v2 import process_approved_actions

router = APIRouter(prefix="/admin/ai/execution", tags=["AI Execution Engine"])

class ExecutionResponse(BaseModel):
    """Response model for execution trigger"""
    success: bool
    message: str
    triggered_at: str

@router.post("/trigger", response_model=ExecutionResponse)
async def trigger_execution(background_tasks: BackgroundTasks):
    """
    Manually trigger the AI execution engine.
    
    This endpoint runs the execution engine in the background and returns immediately.
    The engine will:
    - Fetch all APPROVED actions from the queue
    - Execute each action using the appropriate safe executor
    - Update action status to EXECUTED or FAILED
    
    SAFETY: Only executes actions that have been explicitly approved by a Super Admin.
    """
    try:
        # Run execution in background
        background_tasks.add_task(process_approved_actions)
        
        return ExecutionResponse(
            success=True,
            message="AI execution engine triggered successfully. Check action queue for results.",
            triggered_at=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger execution: {str(e)}"
        )

@router.post("/run-now")
async def run_execution_now():
    """
    Run the AI execution engine synchronously (blocks until complete).
    
    Use this for testing or when you need immediate results.
    WARNING: This may take time depending on the number of approved actions.
    """
    try:
        process_approved_actions()
        
        return {
            "success": True,
            "message": "AI execution completed successfully",
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Execution failed: {str(e)}"
        )

@router.get("/status")
async def get_execution_status():
    """
    Get the status of the AI execution engine.
    
    Returns information about executed actions and pending approvals.
    """
    try:
        from ..deps import get_settings
        import psycopg
        
        s = get_settings()
        db_url = s.DATABASE_URL
        if db_url.startswith("postgresql+psycopg://"):
            db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
        
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # Get last executed action
                cur.execute("""
                    SELECT executed_at FROM ai_action_queue 
                    WHERE status = 'EXECUTED'
                    ORDER BY executed_at DESC LIMIT 1
                """)
                last_execution = cur.fetchone()
                last_execution_time = last_execution[0].isoformat() if last_execution else None
                
                # Get count of approved actions waiting for execution
                cur.execute("""
                    SELECT COUNT(*) FROM ai_action_queue 
                    WHERE status = 'APPROVED'
                """)
                pending_execution = cur.fetchone()[0]
                
                # Get count of executed actions today
                cur.execute("""
                    SELECT COUNT(*) FROM ai_action_queue 
                    WHERE status = 'EXECUTED' 
                    AND executed_at > NOW() - INTERVAL '24 hours'
                """)
                executed_today = cur.fetchone()[0]
                
                # Get count of failed actions today
                cur.execute("""
                    SELECT COUNT(*) FROM ai_action_queue 
                    WHERE status = 'FAILED' 
                    AND executed_at > NOW() - INTERVAL '24 hours'
                """)
                failed_today = cur.fetchone()[0]
                
                return {
                    "status": "operational",
                    "last_execution": last_execution_time,
                    "pending_execution": pending_execution,
                    "executed_today": executed_today,
                    "failed_today": failed_today,
                    "checked_at": datetime.now().isoformat()
                }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )
