from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from typing import Optional
from ..utils import is_admin

router = APIRouter(prefix="/admin/user-activity", tags=["admin-activity"])

@router.get("/")
async def get_all_user_activity(
    user_id: int,
    request: Request,
    search: Optional[str] = None,
    activity_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get all user activities for Super Admin monitoring"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    query = """
        SELECT 
            ual.id,
            ual.user_id,
            u.username,
            u.email,
            u.full_name,
            ual.activity_type,
            ual.activity_details,
            ual.ip_address,
            ual.device_info,
            ual.timestamp
        FROM user_activity_log ual
        JOIN users u ON ual.user_id = u.id
        WHERE 1=1
    """
    
    params = {}
    
    if search:
        query += " AND (u.username ILIKE :search OR u.email ILIKE :search OR u.full_name ILIKE :search)"
        params['search'] = f"%{search}%"
    
    if activity_type:
        query += " AND ual.activity_type = :activity_type"
        params['activity_type'] = activity_type
    
    if start_date:
        query += " AND ual.timestamp >= :start_date"
        params['start_date'] = start_date
    
    if end_date:
        query += " AND ual.timestamp <= :end_date"
        params['end_date'] = end_date
    
    query += " ORDER BY ual.timestamp DESC LIMIT :limit OFFSET :offset"
    params['limit'] = limit
    params['offset'] = offset
    
    rows = (await request.app.state.db.execute(text(query), params)).fetchall()
    
    return {
        "ok": True,
        "activities": [dict(r._mapping) for r in rows],
        "total": len(rows),
        "limit": limit,
        "offset": offset
    }

@router.get("/{target_user_id}")
async def get_user_activity_by_id(
    user_id: int,
    target_user_id: int,
    request: Request,
    limit: int = 100
):
    """Get specific user's activity timeline"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    rows = (await request.app.state.db.execute(text("""
        SELECT 
            ual.*,
            u.username,
            u.email
        FROM user_activity_log ual
        JOIN users u ON ual.user_id = u.id
        WHERE ual.user_id = :target_user_id
        ORDER BY ual.timestamp DESC
        LIMIT :limit
    """), {"target_user_id": target_user_id, "limit": limit})).fetchall()
    
    return {
        "ok": True,
        "activities": [dict(r._mapping) for r in rows]
    }

@router.get("/stats/overview")
async def get_activity_statistics(user_id: int, request: Request):
    """Get activity statistics for Super Admin dashboard"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    stats = {}
    
    # Total activities
    total = (await request.app.state.db.execute(text("""
        SELECT COUNT(*) as count FROM user_activity_log
    """))).fetchone()
    stats['total_activities'] = total[0] if total else 0
    
    # Activities by type
    by_type = (await request.app.state.db.execute(text("""
        SELECT activity_type, COUNT(*) as count
        FROM user_activity_log
        GROUP BY activity_type
        ORDER BY count DESC
        LIMIT 10
    """))).fetchall()
    stats['by_type'] = [dict(r._mapping) for r in by_type]
    
    # Recent 24h
    recent = (await request.app.state.db.execute(text("""
        SELECT COUNT(*) as count
        FROM user_activity_log
        WHERE timestamp >= NOW() - INTERVAL '24 hours'
    """))).fetchone()
    stats['recent_24h'] = recent[0] if recent else 0
    
    # Active users today
    active_today = (await request.app.state.db.execute(text("""
        SELECT COUNT(DISTINCT user_id) as count
        FROM user_activity_log
        WHERE timestamp >= CURRENT_DATE
    """))).fetchone()
    stats['active_users_today'] = active_today[0] if active_today else 0
    
    return {"ok": True, "stats": stats}

@router.get("/stats/types")
async def get_activity_types(user_id: int, request: Request):
    """Get list of all activity types"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    rows = (await request.app.state.db.execute(text("""
        SELECT DISTINCT activity_type, COUNT(*) as count
        FROM user_activity_log
        GROUP BY activity_type
        ORDER BY activity_type
    """))).fetchall()
    
    return {
        "ok": True,
        "types": [dict(r._mapping) for r in rows]
    }
