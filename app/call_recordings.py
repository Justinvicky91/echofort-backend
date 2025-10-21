"""
Call Recordings API
Handles call recording storage, retrieval, and management based on subscription plans.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import psycopg
from app.deps import get_current_user, get_db

router = APIRouter()


class CallRecording(BaseModel):
    id: Optional[str] = None
    user_id: str
    phone_number: str
    caller_name: Optional[str] = None
    duration: int  # in seconds
    recording_url: Optional[str] = None
    trust_factor: int  # 0-10
    scam_type: Optional[str] = None  # "digital_arrest", "loan_harassment", "investment", etc.
    is_scam: bool = False
    is_harassment: bool = False
    is_threatening: bool = False
    recorded_at: datetime
    plan_type: str  # "basic", "personal", "family"


class CallRecordingFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    scam_only: bool = False
    min_trust_factor: Optional[int] = None
    max_trust_factor: Optional[int] = None


@router.get("/recordings", response_model=List[CallRecording])
async def get_call_recordings(
    filter: Optional[CallRecordingFilter] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get call recordings based on user's subscription plan.
    
    - Basic plan: No call recordings
    - Personal plan: ALL call recordings (normal + scam)
    - Family plan: Only scam/harassment/threatening calls
    """
    
    user_id = current_user["id"]
    plan_type = current_user.get("plan_type", "basic")
    
    if plan_type == "basic":
        raise HTTPException(
            status_code=403,
            detail="Call recording feature not available in Basic plan. Upgrade to Personal or Family plan."
        )
    
    query = """
        SELECT * FROM call_recordings
        WHERE user_id = %s
    """
    params = [user_id]
    
    # Family plan: Only scam/harassment/threatening calls
    if plan_type == "family":
        query += " AND (is_scam = TRUE OR is_harassment = TRUE OR is_threatening = TRUE)"
    
    # Apply filters
    if filter:
        if filter.start_date:
            query += " AND recorded_at >= %s"
            params.append(filter.start_date)
        
        if filter.end_date:
            query += " AND recorded_at <= %s"
            params.append(filter.end_date)
        
        if filter.scam_only:
            query += " AND is_scam = TRUE"
        
        if filter.min_trust_factor is not None:
            query += " AND trust_factor >= %s"
            params.append(filter.min_trust_factor)
        
        if filter.max_trust_factor is not None:
            query += " AND trust_factor <= %s"
            params.append(filter.max_trust_factor)
    
    query += " ORDER BY recorded_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    cursor = db.cursor()
    cursor.execute(query, params)
    recordings = cursor.fetchall()
    
    return [
        CallRecording(
            id=str(r[0]),
            user_id=str(r[1]),
            phone_number=r[2],
            caller_name=r[3],
            duration=r[4],
            recording_url=r[5],
            trust_factor=r[6],
            scam_type=r[7],
            is_scam=r[8],
            is_harassment=r[9],
            is_threatening=r[10],
            recorded_at=r[11],
            plan_type=r[12]
        )
        for r in recordings
    ]


@router.post("/upload")
async def upload_call_recording(
    phone_number: str,
    duration: int,
    trust_factor: int,
    scam_type: Optional[str] = None,
    is_scam: bool = False,
    is_harassment: bool = False,
    is_threatening: bool = False,
    recording_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Upload call recording from mobile app.
    Supports offline recording with auto-upload when online.
    """
    
    user_id = current_user["id"]
    plan_type = current_user.get("plan_type", "basic")
    
    if plan_type == "basic":
        raise HTTPException(
            status_code=403,
            detail="Call recording not available in Basic plan"
        )
    
    # Family plan: Only save scam/harassment/threatening calls
    if plan_type == "family" and not (is_scam or is_harassment or is_threatening):
        return {
            "success": True,
            "message": "Call not saved (Family plan only saves scam/harassment/threatening calls)",
            "saved": False
        }
    
    # TODO: Upload file to S3 or storage
    recording_url = f"https://storage.echofort.ai/recordings/{user_id}/{datetime.now().timestamp()}.mp3"
    
    # Save to database
    query = """
        INSERT INTO call_recordings (
            user_id, phone_number, duration, recording_url, trust_factor,
            scam_type, is_scam, is_harassment, is_threatening, recorded_at, plan_type
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    cursor = db.cursor()
    cursor.execute(query, (
        user_id, phone_number, duration, recording_url, trust_factor,
        scam_type, is_scam, is_harassment, is_threatening, datetime.now(), plan_type
    ))
    recording_id = cursor.fetchone()[0]
    db.commit()
    
    return {
        "success": True,
        "recording_id": str(recording_id),
        "recording_url": recording_url,
        "saved": True
    }


@router.get("/recording/{recording_id}")
async def get_recording(
    recording_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get specific call recording by ID"""
    
    user_id = current_user["id"]
    role = current_user.get("role", "user")
    
    query = "SELECT * FROM call_recordings WHERE id = %s"
    params = [recording_id]
    
    # Non-admin users can only access their own recordings
    if role not in ["super_admin", "admin"]:
        query += " AND user_id = %s"
        params.append(user_id)
    
    cursor = db.cursor()
    cursor.execute(query, params)
    recording = cursor.fetchone()
    
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    return CallRecording(
        id=str(recording[0]),
        user_id=str(recording[1]),
        phone_number=recording[2],
        caller_name=recording[3],
        duration=recording[4],
        recording_url=recording[5],
        trust_factor=recording[6],
        scam_type=recording[7],
        is_scam=recording[8],
        is_harassment=recording[9],
        is_threatening=recording[10],
        recorded_at=recording[11],
        plan_type=recording[12]
    )


@router.delete("/recording/{recording_id}")
async def delete_recording(
    recording_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete call recording"""
    
    user_id = current_user["id"]
    
    query = "DELETE FROM call_recordings WHERE id = %s AND user_id = %s"
    cursor = db.cursor()
    cursor.execute(query, (recording_id, user_id))
    db.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    return {"success": True, "message": "Recording deleted"}


@router.get("/stats")
async def get_recording_stats(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get call recording statistics for user"""
    
    user_id = current_user["id"]
    
    query = """
        SELECT 
            COUNT(*) as total_recordings,
            COUNT(*) FILTER (WHERE is_scam = TRUE) as scam_calls,
            COUNT(*) FILTER (WHERE is_harassment = TRUE) as harassment_calls,
            COUNT(*) FILTER (WHERE is_threatening = TRUE) as threatening_calls,
            AVG(trust_factor) as avg_trust_factor,
            SUM(duration) as total_duration
        FROM call_recordings
        WHERE user_id = %s
    """
    
    cursor = db.cursor()
    cursor.execute(query, (user_id,))
    stats = cursor.fetchone()
    
    return {
        "total_recordings": stats[0] or 0,
        "scam_calls": stats[1] or 0,
        "harassment_calls": stats[2] or 0,
        "threatening_calls": stats[3] or 0,
        "avg_trust_factor": float(stats[4]) if stats[4] else 0.0,
        "total_duration_seconds": stats[5] or 0,
        "total_duration_hours": round((stats[5] or 0) / 3600, 2)
    }


@router.get("/admin/all-recordings")
async def get_all_recordings_admin(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Super Admin only: Get ALL call recordings from all users.
    For legal/court purposes.
    """
    
    role = current_user.get("role", "user")
    
    if role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can access all recordings"
        )
    
    query = """
        SELECT * FROM call_recordings
        ORDER BY recorded_at DESC
        LIMIT %s OFFSET %s
    """
    
    cursor = db.cursor()
    cursor.execute(query, (limit, offset))
    recordings = cursor.fetchall()
    
    return [
        CallRecording(
            id=str(r[0]),
            user_id=str(r[1]),
            phone_number=r[2],
            caller_name=r[3],
            duration=r[4],
            recording_url=r[5],
            trust_factor=r[6],
            scam_type=r[7],
            is_scam=r[8],
            is_harassment=r[9],
            is_threatening=r[10],
            recorded_at=r[11],
            plan_type=r[12]
        )
        for r in recordings
    ]

