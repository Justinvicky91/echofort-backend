"""
EchoFort AI Chat API - Block 13
Endpoint for chat console
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid

from ..ai_orchestrator import process_chat_message

router = APIRouter(prefix="/admin/ai/chat", tags=["AI Chat"])

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    role: str = "founder"
    context: Dict[str, Any] = {}

class ChatResponse(BaseModel):
    assistant_message: str
    actions_created: List[Dict[str, Any]] = []
    source_refs: List[Dict[str, Any]] = []
    session_id: str

@router.post("", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    Chat with EchoFort AI
    
    The AI can:
    - Answer questions about the platform
    - Look up user data, payments, complaints
    - Check system health and metrics
    - Propose actions (which go to Action Queue for approval)
    
    SAFETY: AI cannot execute actions directly, only propose them
    """
    try:
        # Generate or use existing session ID
        session_id = request.session_id or str(uuid.uuid4())
        
        # TODO: Get user_id from auth token
        # For now, using a placeholder
        user_id = request.context.get("user_id", 1)
        
        # Process message
        result = process_chat_message(
            message=request.message,
            session_id=session_id,
            role=request.role,
            user_id=user_id,
            context=request.context
        )
        
        return ChatResponse(
            assistant_message=result["assistant_message"],
            actions_created=result["actions_created"],
            source_refs=result["source_refs"],
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 50):
    """
    Get conversation history for a session
    
    Returns the last N messages from a conversation session,
    ordered by creation time (oldest first for display)
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import os
        
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id,
                        session_id,
                        role,
                        message_type,
                        message_text,
                        message_metadata,
                        created_at
                    FROM ai_conversations
                    WHERE session_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s
                """, (session_id, limit))
                
                messages = cur.fetchall()
                return {
                    "session_id": session_id,
                    "messages": [dict(msg) for msg in messages],
                    "count": len(messages)
                }
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load chat history: {str(e)}")


@router.get("/sessions")
async def get_recent_sessions(user_id: Optional[int] = None, limit: int = 10):
    """
    Get recent conversation sessions
    
    Returns a list of recent session IDs with metadata
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import os
        
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT 
                        session_id,
                        COUNT(*) as message_count,
                        MAX(created_at) as last_message_at,
                        MIN(created_at) as first_message_at
                    FROM ai_conversations
                """
                params = []
                
                if user_id:
                    query += " WHERE user_id = %s"
                    params.append(user_id)
                
                query += """
                    GROUP BY session_id
                    ORDER BY MAX(created_at) DESC
                    LIMIT %s
                """
                params.append(limit)
                
                cur.execute(query, params)
                sessions = cur.fetchall()
                return {
                    "sessions": [dict(session) for session in sessions],
                    "count": len(sessions)
                }
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load sessions: {str(e)}")
