"""
AI Command Center Admin API
Block 8: Autonomous Analysis + Human-Approved Execution

Endpoints for managing AI-proposed actions and pattern library.
All endpoints require Super Admin authentication.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import psycopg
from ..deps import get_settings

router = APIRouter(prefix="/admin/ai", tags=["AI Command Center"])

# ============================================================================
# Pydantic Models
# ============================================================================

class ActionQueueItem(BaseModel):
    """Model for AI action queue item"""
    id: UUID
    created_at: datetime
    created_by: str
    type: str
    target: str
    payload: Dict[str, Any]
    impact_summary: str
    status: str
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    executed_by: Optional[str] = None
    executed_at: Optional[datetime] = None
    error_log: Optional[str] = None

class ActionApprovalRequest(BaseModel):
    """Request model for approving an action"""
    admin_id: UUID = Field(..., description="UUID of the Super Admin approving the action")
    notes: Optional[str] = Field(None, description="Optional notes about the approval")

class ActionRejectionRequest(BaseModel):
    """Request model for rejecting an action"""
    admin_id: UUID = Field(..., description="UUID of the Super Admin rejecting the action")
    reason: str = Field(..., description="Reason for rejection")

class PatternLibraryItem(BaseModel):
    """Model for pattern library item"""
    id: UUID
    created_at: datetime
    category: str
    description: str
    example_phrases: Optional[List[str]] = None
    risk_level: str
    source_url: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: bool
    last_updated: datetime

class CreatePatternRequest(BaseModel):
    """Request model for creating a new pattern"""
    category: str = Field(..., description="PHISHING, FRAUD, HARASSMENT, EXTREMISM, etc.")
    description: str = Field(..., description="Human-readable summary of the pattern")
    example_phrases: Optional[List[str]] = Field(None, description="Example phrases or keywords")
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    source_url: Optional[str] = Field(None, description="URL where pattern was discovered")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")

# ============================================================================
# Database Connection Helper
# ============================================================================

def get_db_connection():
    """Get database connection using psycopg"""
    s = get_settings()
    db_url = s.DATABASE_URL
    if db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
    return psycopg.connect(db_url)

# ============================================================================
# Action Queue Endpoints
# ============================================================================

@router.get("/actions", response_model=List[ActionQueueItem])
async def list_actions(
    status: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 100
):
    """
    List AI-proposed actions from the queue.
    
    Query Parameters:
    - status: Filter by status (PENDING, APPROVED, REJECTED, EXECUTED, FAILED)
    - type: Filter by action type (config_change, pattern_update, etc.)
    - limit: Maximum number of results (default: 100)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                        id, created_at, created_by, type, target, payload,
                        impact_summary, status, approved_by, approved_at,
                        executed_by, executed_at, error_log
                    FROM ai_action_queue
                    WHERE 1=1
                """
                params = []
                
                if status:
                    query += " AND status = %s"
                    params.append(status)
                
                if type:
                    query += " AND type = %s"
                    params.append(type)
                
                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                actions = []
                for row in rows:
                    actions.append(ActionQueueItem(
                        id=row[0],
                        created_at=row[1],
                        created_by=row[2],
                        type=row[3],
                        target=row[4],
                        payload=row[5],
                        impact_summary=row[6],
                        status=row[7],
                        approved_by=row[8],
                        approved_at=row[9],
                        executed_by=row[10],
                        executed_at=row[11],
                        error_log=row[12]
                    ))
                
                return actions
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch actions: {str(e)}"
        )

@router.get("/actions/{action_id}", response_model=ActionQueueItem)
async def get_action(action_id: UUID):
    """Get details of a specific action by ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id, created_at, created_by, type, target, payload,
                        impact_summary, status, approved_by, approved_at,
                        executed_by, executed_at, error_log
                    FROM ai_action_queue
                    WHERE id = %s
                """, (str(action_id),))
                
                row = cur.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Action {action_id} not found"
                    )
                
                return ActionQueueItem(
                    id=row[0],
                    created_at=row[1],
                    created_by=row[2],
                    type=row[3],
                    target=row[4],
                    payload=row[5],
                    impact_summary=row[6],
                    status=row[7],
                    approved_by=row[8],
                    approved_at=row[9],
                    executed_by=row[10],
                    executed_at=row[11],
                    error_log=row[12]
                )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch action: {str(e)}"
        )

@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: UUID, request: ActionApprovalRequest):
    """
    Approve an action in the queue.
    Changes status from PENDING to APPROVED.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if action exists and is pending
                cur.execute("""
                    SELECT status FROM ai_action_queue WHERE id = %s
                """, (str(action_id),))
                
                row = cur.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Action {action_id} not found"
                    )
                
                if row[0] != 'PENDING':
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Action is not in PENDING status (current: {row[0]})"
                    )
                
                # Update status to APPROVED
                cur.execute("""
                    UPDATE ai_action_queue
                    SET 
                        status = 'APPROVED',
                        approved_by = %s,
                        approved_at = NOW()
                    WHERE id = %s
                """, (str(request.admin_id), str(action_id)))
                
                conn.commit()
                
                return {
                    "success": True,
                    "message": f"Action {action_id} approved successfully",
                    "action_id": str(action_id),
                    "status": "APPROVED"
                }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve action: {str(e)}"
        )

@router.post("/actions/{action_id}/reject")
async def reject_action(action_id: UUID, request: ActionRejectionRequest):
    """
    Reject an action in the queue.
    Changes status from PENDING to REJECTED.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if action exists and is pending
                cur.execute("""
                    SELECT status FROM ai_action_queue WHERE id = %s
                """, (str(action_id),))
                
                row = cur.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Action {action_id} not found"
                    )
                
                if row[0] != 'PENDING':
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Action is not in PENDING status (current: {row[0]})"
                    )
                
                # Update status to REJECTED
                cur.execute("""
                    UPDATE ai_action_queue
                    SET 
                        status = 'REJECTED',
                        approved_by = %s,
                        approved_at = NOW(),
                        error_log = %s
                    WHERE id = %s
                """, (str(request.admin_id), f"Rejected by admin: {request.reason}", str(action_id)))
                
                conn.commit()
                
                return {
                    "success": True,
                    "message": f"Action {action_id} rejected successfully",
                    "action_id": str(action_id),
                    "status": "REJECTED",
                    "reason": request.reason
                }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject action: {str(e)}"
        )

# ============================================================================
# Pattern Library Endpoints
# ============================================================================

@router.get("/patterns", response_model=List[PatternLibraryItem])
async def list_patterns(
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    is_active: Optional[bool] = True,
    limit: int = 100
):
    """
    List patterns from the AI pattern library.
    
    Query Parameters:
    - category: Filter by category (PHISHING, FRAUD, etc.)
    - risk_level: Filter by risk level (LOW, MEDIUM, HIGH, CRITICAL)
    - is_active: Filter by active status (default: True)
    - limit: Maximum number of results (default: 100)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                        id, created_at, category, description, example_phrases,
                        risk_level, source_url, tags, is_active, last_updated
                    FROM ai_pattern_library
                    WHERE 1=1
                """
                params = []
                
                if category:
                    query += " AND category = %s"
                    params.append(category)
                
                if risk_level:
                    query += " AND risk_level = %s"
                    params.append(risk_level)
                
                if is_active is not None:
                    query += " AND is_active = %s"
                    params.append(is_active)
                
                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                patterns = []
                for row in rows:
                    patterns.append(PatternLibraryItem(
                        id=row[0],
                        created_at=row[1],
                        category=row[2],
                        description=row[3],
                        example_phrases=row[4] if row[4] else None,
                        risk_level=row[5],
                        source_url=row[6],
                        tags=row[7] if row[7] else None,
                        is_active=row[8],
                        last_updated=row[9]
                    ))
                
                return patterns
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch patterns: {str(e)}"
        )

@router.get("/patterns/{pattern_id}", response_model=PatternLibraryItem)
async def get_pattern(pattern_id: UUID):
    """Get details of a specific pattern by ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id, created_at, category, description, example_phrases,
                        risk_level, source_url, tags, is_active, last_updated
                    FROM ai_pattern_library
                    WHERE id = %s
                """, (str(pattern_id),))
                
                row = cur.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Pattern {pattern_id} not found"
                    )
                
                return PatternLibraryItem(
                    id=row[0],
                    created_at=row[1],
                    category=row[2],
                    description=row[3],
                    example_phrases=row[4] if row[4] else None,
                    risk_level=row[5],
                    source_url=row[6],
                    tags=row[7] if row[7] else None,
                    is_active=row[8],
                    last_updated=row[9]
                )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pattern: {str(e)}"
        )

@router.post("/patterns", response_model=PatternLibraryItem)
async def create_pattern(request: CreatePatternRequest):
    """
    Create a new pattern in the library.
    This endpoint is typically used by the AI Analysis Engine,
    but can also be used manually by Super Admin.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ai_pattern_library (
                        category, description, example_phrases,
                        risk_level, source_url, tags
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING 
                        id, created_at, category, description, example_phrases,
                        risk_level, source_url, tags, is_active, last_updated
                """, (
                    request.category,
                    request.description,
                    request.example_phrases,
                    request.risk_level,
                    request.source_url,
                    request.tags
                ))
                
                row = cur.fetchone()
                conn.commit()
                
                return PatternLibraryItem(
                    id=row[0],
                    created_at=row[1],
                    category=row[2],
                    description=row[3],
                    example_phrases=row[4] if row[4] else None,
                    risk_level=row[5],
                    source_url=row[6],
                    tags=row[7] if row[7] else None,
                    is_active=row[8],
                    last_updated=row[9]
                )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create pattern: {str(e)}"
        )

# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/stats")
async def get_stats():
    """Get statistics about the AI Command Center"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Action queue stats
                cur.execute("""
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM ai_action_queue
                    GROUP BY status
                """)
                action_stats = {row[0]: row[1] for row in cur.fetchall()}
                
                # Pattern library stats
                cur.execute("""
                    SELECT 
                        category,
                        COUNT(*) as count
                    FROM ai_pattern_library
                    WHERE is_active = TRUE
                    GROUP BY category
                """)
                pattern_stats = {row[0]: row[1] for row in cur.fetchall()}
                
                # Total patterns by risk level
                cur.execute("""
                    SELECT 
                        risk_level,
                        COUNT(*) as count
                    FROM ai_pattern_library
                    WHERE is_active = TRUE
                    GROUP BY risk_level
                """)
                risk_stats = {row[0]: row[1] for row in cur.fetchall()}
                
                return {
                    "action_queue": {
                        "pending": action_stats.get('PENDING', 0),
                        "approved": action_stats.get('APPROVED', 0),
                        "rejected": action_stats.get('REJECTED', 0),
                        "executed": action_stats.get('EXECUTED', 0),
                        "failed": action_stats.get('FAILED', 0),
                        "total": sum(action_stats.values())
                    },
                    "pattern_library": {
                        "by_category": pattern_stats,
                        "by_risk_level": risk_stats,
                        "total_active": sum(pattern_stats.values())
                    }
                }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stats: {str(e)}"
        )
