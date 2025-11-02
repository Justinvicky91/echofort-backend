from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from typing import Optional
from ..utils import is_admin

router = APIRouter(prefix="/admin/vault", tags=["admin-vault"])

@router.get("/call-recordings")
async def get_all_call_recordings(
    user_id: int,
    request: Request,
    search: Optional[str] = None,
    scam_detected: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get all call recordings across all users for Super Admin"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    query = """
        SELECT 
            crm.id,
            crm.user_id,
            u.username,
            u.email,
            u.full_name,
            crm.phone_number,
            crm.caller_name,
            crm.call_direction,
            crm.call_duration_seconds,
            crm.call_timestamp,
            crm.file_url,
            crm.file_size_bytes,
            crm.file_format,
            crm.scam_detected,
            crm.scam_confidence_score,
            crm.scam_type,
            crm.threat_level,
            crm.is_reported,
            crm.created_at
        FROM call_recording_metadata crm
        JOIN users u ON crm.user_id = u.id
        WHERE 1=1
    """
    
    params = {}
    
    if search:
        query += " AND (u.username ILIKE :search OR u.email ILIKE :search OR u.full_name ILIKE :search OR crm.phone_number ILIKE :search)"
        params['search'] = f"%{search}%"
    
    if scam_detected is not None:
        query += " AND crm.scam_detected = :scam_detected"
        params['scam_detected'] = scam_detected
    
    if start_date:
        query += " AND crm.call_timestamp >= :start_date"
        params['start_date'] = start_date
    
    if end_date:
        query += " AND crm.call_timestamp <= :end_date"
        params['end_date'] = end_date
    
    query += " ORDER BY crm.call_timestamp DESC LIMIT :limit OFFSET :offset"
    params['limit'] = limit
    params['offset'] = offset
    
    rows = (await request.app.state.db.execute(text(query), params)).fetchall()
    
    return {
        "ok": True,
        "recordings": [dict(r._mapping) for r in rows],
        "total": len(rows),
        "limit": limit,
        "offset": offset
    }

@router.get("/call-recordings/{recording_id}")
async def get_call_recording_details(
    user_id: int,
    recording_id: int,
    request: Request
):
    """Get detailed information about a specific call recording"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    row = (await request.app.state.db.execute(text("""
        SELECT 
            crm.*,
            u.username,
            u.email,
            u.full_name,
            u.phone as user_phone
        FROM call_recording_metadata crm
        JOIN users u ON crm.user_id = u.id
        WHERE crm.id = :recording_id
    """), {"recording_id": recording_id})).fetchone()
    
    if not row:
        raise HTTPException(404, "Recording not found")
    
    return {"ok": True, "recording": dict(row._mapping)}

@router.get("/evidence")
async def get_all_evidence(
    user_id: int,
    request: Request,
    search: Optional[str] = None,
    evidence_type: Optional[str] = None,
    verification_status: Optional[str] = None,
    scam_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get all evidence submissions across all users for Super Admin"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    query = """
        SELECT 
            evm.id,
            evm.user_id,
            u.username,
            u.email,
            u.full_name,
            evm.evidence_type,
            evm.title,
            evm.description,
            evm.file_url,
            evm.file_size_bytes,
            evm.scam_type,
            evm.scam_category,
            evm.reported_amount,
            evm.currency,
            evm.incident_date,
            evm.verification_status,
            evm.severity_level,
            evm.police_complaint_filed,
            evm.complaint_number,
            evm.created_at
        FROM evidence_vault_metadata evm
        JOIN users u ON evm.user_id = u.id
        WHERE 1=1
    """
    
    params = {}
    
    if search:
        query += " AND (u.username ILIKE :search OR u.email ILIKE :search OR u.full_name ILIKE :search OR evm.title ILIKE :search)"
        params['search'] = f"%{search}%"
    
    if evidence_type:
        query += " AND evm.evidence_type = :evidence_type"
        params['evidence_type'] = evidence_type
    
    if verification_status:
        query += " AND evm.verification_status = :verification_status"
        params['verification_status'] = verification_status
    
    if scam_type:
        query += " AND evm.scam_type = :scam_type"
        params['scam_type'] = scam_type
    
    if start_date:
        query += " AND evm.created_at >= :start_date"
        params['start_date'] = start_date
    
    if end_date:
        query += " AND evm.created_at <= :end_date"
        params['end_date'] = end_date
    
    query += " ORDER BY evm.created_at DESC LIMIT :limit OFFSET :offset"
    params['limit'] = limit
    params['offset'] = offset
    
    rows = (await request.app.state.db.execute(text(query), params)).fetchall()
    
    return {
        "ok": True,
        "evidence": [dict(r._mapping) for r in rows],
        "total": len(rows),
        "limit": limit,
        "offset": offset
    }

@router.get("/evidence/{evidence_id}")
async def get_evidence_details(
    user_id: int,
    evidence_id: int,
    request: Request
):
    """Get detailed information about a specific evidence item"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    row = (await request.app.state.db.execute(text("""
        SELECT 
            evm.*,
            u.username,
            u.email,
            u.full_name,
            u.phone as user_phone
        FROM evidence_vault_metadata evm
        JOIN users u ON evm.user_id = u.id
        WHERE evm.id = :evidence_id
    """), {"evidence_id": evidence_id})).fetchone()
    
    if not row:
        raise HTTPException(404, "Evidence not found")
    
    # Log access
    await request.app.state.db.execute(text("""
        INSERT INTO evidence_access_log (evidence_id, accessed_by, access_type, ip_address)
        VALUES (:evidence_id, :user_id, 'view', :ip)
    """), {
        "evidence_id": evidence_id,
        "user_id": user_id,
        "ip": request.client.host if request.client else None
    })
    await request.app.state.db.commit()
    
    return {"ok": True, "evidence": dict(row._mapping)}

@router.get("/stats")
async def get_vault_statistics(user_id: int, request: Request):
    """Get vault statistics for Super Admin dashboard"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    stats = {}
    
    # Call recordings stats
    call_stats = (await request.app.state.db.execute(text("""
        SELECT 
            COUNT(*) as total_recordings,
            COUNT(CASE WHEN scam_detected = TRUE THEN 1 END) as scam_recordings,
            COUNT(CASE WHEN is_reported = TRUE THEN 1 END) as reported_recordings,
            SUM(call_duration_seconds) as total_duration_seconds,
            SUM(file_size_bytes) as total_storage_bytes
        FROM call_recording_metadata
    """))).fetchone()
    
    stats['call_recordings'] = dict(call_stats._mapping) if call_stats else {}
    
    # Evidence stats
    evidence_stats = (await request.app.state.db.execute(text("""
        SELECT 
            COUNT(*) as total_evidence,
            COUNT(CASE WHEN verification_status = 'verified' THEN 1 END) as verified_evidence,
            COUNT(CASE WHEN verification_status = 'pending' THEN 1 END) as pending_evidence,
            COUNT(CASE WHEN police_complaint_filed = TRUE THEN 1 END) as police_complaints,
            SUM(reported_amount) as total_reported_amount,
            SUM(file_size_bytes) as total_storage_bytes
        FROM evidence_vault_metadata
    """))).fetchone()
    
    stats['evidence'] = dict(evidence_stats._mapping) if evidence_stats else {}
    
    # Recent activity
    recent_recordings = (await request.app.state.db.execute(text("""
        SELECT COUNT(*) as count
        FROM call_recording_metadata
        WHERE created_at >= NOW() - INTERVAL '24 hours'
    """))).fetchone()
    
    recent_evidence = (await request.app.state.db.execute(text("""
        SELECT COUNT(*) as count
        FROM evidence_vault_metadata
        WHERE created_at >= NOW() - INTERVAL '24 hours'
    """))).fetchone()
    
    stats['recent_24h'] = {
        'recordings': recent_recordings[0] if recent_recordings else 0,
        'evidence': recent_evidence[0] if recent_evidence else 0
    }
    
    return {"ok": True, "stats": stats}

@router.post("/evidence/{evidence_id}/verify")
async def verify_evidence(
    user_id: int,
    evidence_id: int,
    request: Request,
    verification_result: str,
    notes: Optional[str] = None
):
    """Verify or reject evidence submission"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    await request.app.state.db.execute(text("""
        UPDATE evidence_vault_metadata
        SET verification_status = :status,
            verified_by = :user_id,
            verified_at = CURRENT_TIMESTAMP,
            verification_notes = :notes,
            verification_result = :result
        WHERE id = :evidence_id
    """), {
        "status": "verified" if verification_result == "authentic" else "rejected",
        "user_id": user_id,
        "notes": notes,
        "result": verification_result,
        "evidence_id": evidence_id
    })
    await request.app.state.db.commit()
    
    return {"ok": True, "message": "Evidence verification updated"}
