"""
AI Learning Center API Endpoints
Provides access to conversation history, decisions, daily digests, and learning patterns
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from app.ai_learning_center import (
    get_conversation_history,
    get_recent_decisions,
    get_daily_digest,
    generate_daily_digest,
    update_decision_outcome,
    learn_from_patterns
)

router = APIRouter(prefix="/admin/ai/learning", tags=["AI Learning Center"])

class DecisionFeedback(BaseModel):
    was_approved: bool
    user_feedback: Optional[str] = None
    outcome_data: Optional[Dict[str, Any]] = None

@router.get("/conversations")
async def list_conversations(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of messages")
):
    """
    Get conversation history with optional filtering
    
    Returns list of conversation messages with metadata
    """
    try:
        conversations = get_conversation_history(session_id, user_id, limit)
        return {
            "success": True,
            "count": len(conversations),
            "conversations": conversations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversations: {str(e)}")

@router.get("/decisions")
async def list_decisions(
    decision_type: Optional[str] = Query(None, description="Filter by decision type"),
    was_approved: Optional[bool] = Query(None, description="Filter by approval status"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of decisions")
):
    """
    Get recent AI decisions with optional filtering
    
    Returns list of decisions with context and outcomes
    """
    try:
        decisions = get_recent_decisions(decision_type, was_approved, limit)
        return {
            "success": True,
            "count": len(decisions),
            "decisions": decisions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch decisions: {str(e)}")

@router.post("/decisions/{decision_id}/feedback")
async def provide_decision_feedback(decision_id: int, feedback: DecisionFeedback):
    """
    Provide feedback on an AI decision
    
    This helps the AI learn from user preferences and improve future decisions
    """
    try:
        update_decision_outcome(
            decision_id,
            feedback.was_approved,
            feedback.user_feedback,
            feedback.outcome_data
        )
        return {
            "success": True,
            "message": "Decision feedback recorded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")

@router.get("/digest/{digest_date}")
async def get_digest(digest_date: date):
    """
    Get the daily digest for a specific date
    
    Returns insights, recommendations, and statistics for that day
    """
    try:
        digest = get_daily_digest(digest_date)
        if not digest:
            return {
                "success": False,
                "message": f"No digest found for {digest_date}. Generate it first."
            }
        return {
            "success": True,
            "digest": digest
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch digest: {str(e)}")

@router.post("/digest/generate")
async def generate_digest(digest_date: Optional[date] = None):
    """
    Generate a daily digest for a specific date (defaults to yesterday)
    
    This analyzes all AI activity for the day and generates insights and recommendations
    """
    try:
        digest = generate_daily_digest(digest_date)
        return {
            "success": True,
            "message": "Daily digest generated successfully",
            "digest": digest
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate digest: {str(e)}")

@router.post("/patterns/learn")
async def trigger_pattern_learning():
    """
    Trigger pattern learning from past interactions
    
    This analyzes successful decisions and stores patterns for future use
    """
    try:
        patterns_learned = learn_from_patterns()
        return {
            "success": True,
            "message": f"Learned {patterns_learned} new patterns from past interactions",
            "patterns_count": patterns_learned
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to learn patterns: {str(e)}")

@router.get("/stats")
async def get_learning_stats():
    """
    Get overall statistics about AI learning and performance
    
    Returns counts, success rates, and trends
    """
    try:
        from ai_learning_center import get_db_connection
        from psycopg2.extras import RealDictCursor
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get conversation stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_conversations,
                COUNT(DISTINCT session_id) as unique_sessions,
                COUNT(DISTINCT user_id) as unique_users
            FROM ai_conversations
        """)
        conv_stats = dict(cur.fetchone())
        
        # Get decision stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_decisions,
                SUM(CASE WHEN was_approved = TRUE THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN was_approved = FALSE THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN was_approved IS NULL THEN 1 ELSE 0 END) as pending,
                AVG(confidence_score) as avg_confidence
            FROM ai_decisions
        """)
        decision_stats = dict(cur.fetchone())
        
        # Get learning pattern stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_patterns,
                AVG(success_rate) as avg_success_rate,
                SUM(usage_count) as total_pattern_usage
            FROM ai_learning_patterns
        """)
        pattern_stats = dict(cur.fetchone())
        
        # Get recent digest count
        cur.execute("""
            SELECT COUNT(*) as digest_count
            FROM ai_daily_digests
            WHERE digest_date >= CURRENT_DATE - INTERVAL '30 days'
        """)
        digest_count = cur.fetchone()['digest_count']
        
        cur.close()
        conn.close()
        
        return {
            "success": True,
            "stats": {
                "conversations": conv_stats,
                "decisions": decision_stats,
                "patterns": pattern_stats,
                "digests_last_30_days": digest_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")
