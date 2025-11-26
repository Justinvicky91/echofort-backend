"""
AI Analysis Engine Trigger API
Block 8 Phase 3

Provides endpoints to manually trigger the AI analysis engine
and view analysis results.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
import sys
import os

# Add parent directory to path to import ai_analysis_engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_analysis_engine import run_daily_analysis

router = APIRouter(prefix="/admin/ai/analysis", tags=["AI Analysis Engine"])

class AnalysisResponse(BaseModel):
    """Response model for analysis trigger"""
    success: bool
    message: str
    triggered_at: str

@router.post("/trigger", response_model=AnalysisResponse)
async def trigger_analysis(background_tasks: BackgroundTasks):
    """
    Manually trigger the AI analysis engine.
    
    This endpoint runs the analysis in the background and returns immediately.
    The analysis includes:
    - Platform metrics gathering
    - AI-powered health analysis
    - Proposed action generation
    - Threat pattern discovery
    
    Results will be inserted into ai_action_queue and ai_pattern_library.
    """
    try:
        # Run analysis in background
        background_tasks.add_task(run_daily_analysis)
        
        return AnalysisResponse(
            success=True,
            message="AI analysis engine triggered successfully. Results will be available in the Action Queue shortly.",
            triggered_at=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger analysis: {str(e)}"
        )

@router.post("/run-now")
async def run_analysis_now():
    """
    Run the AI analysis engine synchronously (blocks until complete).
    
    Use this for testing or when you need immediate results.
    WARNING: This may take 30-60 seconds to complete.
    """
    try:
        run_daily_analysis()
        
        return {
            "success": True,
            "message": "AI analysis completed successfully",
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@router.get("/status")
async def get_analysis_status():
    """
    Get the status of the AI analysis engine.
    
    Returns information about the last run and current queue status.
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
                # Get last action created by AI
                cur.execute("""
                    SELECT created_at FROM ai_action_queue 
                    WHERE created_by = 'EchoFortAI'
                    ORDER BY created_at DESC LIMIT 1
                """)
                last_action = cur.fetchone()
                last_action_time = last_action[0].isoformat() if last_action else None
                
                # Get count of pending actions
                cur.execute("""
                    SELECT COUNT(*) FROM ai_action_queue 
                    WHERE status = 'PENDING' AND created_by = 'EchoFortAI'
                """)
                pending_actions = cur.fetchone()[0]
                
                # Get count of patterns added today
                cur.execute("""
                    SELECT COUNT(*) FROM ai_pattern_library 
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                patterns_today = cur.fetchone()[0]
                
                return {
                    "status": "operational",
                    "last_analysis_run": last_action_time,
                    "pending_actions": pending_actions,
                    "patterns_discovered_today": patterns_today,
                    "checked_at": datetime.now().isoformat()
                }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )
