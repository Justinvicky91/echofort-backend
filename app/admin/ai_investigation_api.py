"""
AI Investigation API Endpoints
Provides REST API for case management, evidence linking, and investigation workflows
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.ai_investigation import (
    create_investigation_case,
    get_investigation_cases,
    get_case_details,
    update_case_status,
    add_evidence_to_case,
    add_note_to_case,
    propose_investigation_action,
    approve_investigation_action,
    get_investigation_statistics,
    generate_daily_investigation_stats
)

router = APIRouter()

# Request Models
class CreateCaseRequest(BaseModel):
    title: str
    description: str
    case_type: str  # 'harassment', 'scam', 'fraud', 'threat', 'other'
    priority: Optional[str] = "medium"  # 'low', 'medium', 'high', 'critical'
    victim_user_id: Optional[int] = None
    suspect_phone: Optional[str] = None
    suspect_name: Optional[str] = None
    suspect_details: Optional[Dict[str, Any]] = None
    created_by: Optional[int] = None

class UpdateStatusRequest(BaseModel):
    status: str  # 'open', 'investigating', 'pending_evidence', 'resolved', 'closed'
    resolution_summary: Optional[str] = None
    updated_by: Optional[int] = None

class AddEvidenceRequest(BaseModel):
    evidence_type: str  # 'call', 'message', 'screenshot', 'document', 'url', 'other'
    evidence_description: str
    evidence_id: Optional[int] = None
    evidence_metadata: Optional[Dict[str, Any]] = None
    added_by: Optional[int] = None

class AddNoteRequest(BaseModel):
    note_text: str
    note_type: Optional[str] = "general"  # 'general', 'important', 'ai_insight', 'action_item'
    created_by: Optional[int] = None

class ProposeActionRequest(BaseModel):
    action_type: str
    action_description: str
    action_data: Optional[Dict[str, Any]] = None
    proposed_by: Optional[str] = "ai"

class ApproveActionRequest(BaseModel):
    approved_by: int

# Endpoints

@router.post("/admin/ai/investigation/cases/create")
async def create_case(request: CreateCaseRequest):
    """Create a new investigation case"""
    try:
        case = create_investigation_case(
            title=request.title,
            description=request.description,
            case_type=request.case_type,
            priority=request.priority,
            victim_user_id=request.victim_user_id,
            suspect_phone=request.suspect_phone,
            suspect_name=request.suspect_name,
            suspect_details=request.suspect_details,
            created_by=request.created_by
        )
        return {"success": True, "case": case}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/ai/investigation/cases")
async def list_cases(status: Optional[str] = None, case_type: Optional[str] = None, 
                    limit: int = 50, offset: int = 0):
    """Get list of investigation cases"""
    try:
        cases = get_investigation_cases(status=status, case_type=case_type, 
                                       limit=limit, offset=offset)
        return {"success": True, "count": len(cases), "cases": cases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/ai/investigation/cases/{case_id}")
async def get_case(case_id: int):
    """Get full case details"""
    try:
        case_data = get_case_details(case_id)
        if not case_data:
            raise HTTPException(status_code=404, detail="Case not found")
        return {"success": True, "data": case_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/admin/ai/investigation/cases/{case_id}/status")
async def update_status(case_id: int, request: UpdateStatusRequest):
    """Update case status"""
    try:
        case = update_case_status(
            case_id=case_id,
            new_status=request.status,
            updated_by=request.updated_by,
            resolution_summary=request.resolution_summary
        )
        return {"success": True, "case": case}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/ai/investigation/cases/{case_id}/evidence")
async def add_evidence(case_id: int, request: AddEvidenceRequest):
    """Add evidence to a case"""
    try:
        evidence = add_evidence_to_case(
            case_id=case_id,
            evidence_type=request.evidence_type,
            evidence_description=request.evidence_description,
            evidence_id=request.evidence_id,
            evidence_metadata=request.evidence_metadata,
            added_by=request.added_by
        )
        return {"success": True, "evidence": evidence}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/ai/investigation/cases/{case_id}/notes")
async def add_note(case_id: int, request: AddNoteRequest):
    """Add a note to a case"""
    try:
        note = add_note_to_case(
            case_id=case_id,
            note_text=request.note_text,
            note_type=request.note_type,
            created_by=request.created_by
        )
        return {"success": True, "note": note}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/ai/investigation/cases/{case_id}/actions/propose")
async def propose_action(case_id: int, request: ProposeActionRequest):
    """Propose an AI investigation action"""
    try:
        action = propose_investigation_action(
            case_id=case_id,
            action_type=request.action_type,
            action_description=request.action_description,
            action_data=request.action_data,
            proposed_by=request.proposed_by
        )
        return {"success": True, "action": action}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/ai/investigation/actions/{action_id}/approve")
async def approve_action(action_id: int, request: ApproveActionRequest):
    """Approve an AI investigation action"""
    try:
        action = approve_investigation_action(
            action_id=action_id,
            approved_by=request.approved_by
        )
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")
        return {"success": True, "action": action}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/ai/investigation/stats")
async def get_stats(days: int = 30):
    """Get investigation statistics"""
    try:
        stats = get_investigation_statistics(days=days)
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/ai/investigation/stats/generate")
async def generate_stats():
    """Generate daily investigation statistics"""
    try:
        stats = generate_daily_investigation_stats()
        return {"success": True, "stats": stats, "message": "Daily statistics generated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/ai/investigation/dashboard")
async def get_dashboard():
    """Get investigation dashboard summary"""
    try:
        # Get open cases
        open_cases = get_investigation_cases(status="open", limit=10)
        
        # Get investigating cases
        investigating_cases = get_investigation_cases(status="investigating", limit=10)
        
        # Get recent stats
        recent_stats = get_investigation_statistics(days=7)
        
        # Calculate summary
        total_open = len(get_investigation_cases(status="open", limit=1000))
        total_investigating = len(get_investigation_cases(status="investigating", limit=1000))
        total_resolved = len(get_investigation_cases(status="resolved", limit=1000))
        
        return {
            "success": True,
            "dashboard": {
                "summary": {
                    "total_open": total_open,
                    "total_investigating": total_investigating,
                    "total_resolved": total_resolved
                },
                "open_cases": open_cases,
                "investigating_cases": investigating_cases,
                "recent_stats": recent_stats
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
