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
