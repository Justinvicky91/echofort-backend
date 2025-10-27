"""
Admin Approvals Management
Handles approval workflows for employee requests, expenses, and system changes
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
import asyncpg
from .database import get_db_pool

router = APIRouter(prefix="/admin/approvals", tags=["admin-approvals"])


class ApprovalRequest(BaseModel):
    type: str  # joining, resignation, leave, expense, policy, system
    title: str
    description: str
    requester: str
    requesterEmail: str
    department: str
    priority: str  # low, medium, high, critical
    details: dict


class ApprovalAction(BaseModel):
    status: str  # approved, rejected
    approvedBy: Optional[str] = None
    rejectedBy: Optional[str] = None
    reason: Optional[str] = None
    notifyAdmin: bool = True
    notifyRequester: bool = True


@router.get("")
async def get_approvals(
    status: Optional[str] = None,
    type: Optional[str] = None
):
    """
    Get all approval requests
    Returns sample data for now (will connect to database later)
    """
    # TODO: Connect to database
    # For now, return empty array to trigger frontend sample data
    return []


@router.post("/{approval_id}/approve")
async def approve_request(approval_id: str, action: ApprovalAction):
    """
    Approve a request
    """
    # TODO: Update database
    # TODO: Send email notifications to admin@echofort.ai and requester
    
    return {
        "success": True,
        "message": f"Approval {approval_id} approved successfully",
        "approvalId": approval_id,
        "status": "approved",
        "notificationsSent": {
            "admin": "admin@echofort.ai" if action.notifyAdmin else None,
            "requester": action.notifyRequester
        }
    }


@router.post("/{approval_id}/reject")
async def reject_request(approval_id: str, action: ApprovalAction):
    """
    Reject a request
    """
    # TODO: Update database
    # TODO: Send email notifications to admin@echofort.ai and requester
    
    return {
        "success": True,
        "message": f"Approval {approval_id} rejected successfully",
        "approvalId": approval_id,
        "status": "rejected",
        "reason": action.reason,
        "notificationsSent": {
            "admin": "admin@echofort.ai" if action.notifyAdmin else None,
            "requester": action.notifyRequester
        }
    }


@router.post("")
async def create_approval(request: ApprovalRequest):
    """
    Create a new approval request
    """
    # TODO: Save to database
    # TODO: Send notification to admin@echofort.ai
    
    return {
        "success": True,
        "message": "Approval request created successfully",
        "approvalId": f"APR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "status": "pending"
    }

