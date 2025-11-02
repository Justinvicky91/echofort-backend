from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from typing import Optional
from ..utils import is_admin

router = APIRouter(prefix="/admin/permissions", tags=["admin-permissions"])

@router.get("/overview")
async def get_permissions_overview(user_id: int, request: Request):
    """Get permissions statistics overview for Super Admin"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    stats = {}
    
    # Total users with app installed
    total_users = (await request.app.state.db.execute(text("""
        SELECT COUNT(DISTINCT user_id) as count
        FROM user_device_permissions
    """))).fetchone()
    stats['total_users'] = total_users[0] if total_users else 0
    
    # Permission statistics
    permissions = ['camera', 'microphone', 'location', 'sms', 'contacts', 'phone', 'storage', 'notification']
    
    for perm in permissions:
        perm_stats = (await request.app.state.db.execute(text(f"""
            SELECT 
                COUNT(CASE WHEN {perm}_permission = 'granted' THEN 1 END) as granted,
                COUNT(CASE WHEN {perm}_permission = 'denied' THEN 1 END) as denied,
                COUNT(CASE WHEN {perm}_permission = 'not_requested' THEN 1 END) as not_requested
            FROM user_device_permissions
        """))).fetchone()
        
        if perm_stats:
            total = stats['total_users']
            stats[perm] = {
                'granted': perm_stats[0] or 0,
                'denied': perm_stats[1] or 0,
                'not_requested': perm_stats[2] or 0,
                'granted_percentage': round((perm_stats[0] or 0) / total * 100, 2) if total > 0 else 0
            }
    
    # Users with all permissions granted
    all_granted = (await request.app.state.db.execute(text("""
        SELECT COUNT(*) as count
        FROM user_device_permissions
        WHERE camera_permission = 'granted'
          AND microphone_permission = 'granted'
          AND location_permission = 'granted'
          AND sms_permission = 'granted'
          AND phone_permission = 'granted'
    """))).fetchone()
    stats['all_permissions_granted'] = all_granted[0] if all_granted else 0
    
    # Users with critical permissions denied
    critical_denied = (await request.app.state.db.execute(text("""
        SELECT COUNT(*) as count
        FROM user_device_permissions
        WHERE location_permission = 'denied'
           OR phone_permission = 'denied'
           OR sms_permission = 'denied'
    """))).fetchone()
    stats['critical_permissions_denied'] = critical_denied[0] if critical_denied else 0
    
    return {"ok": True, "stats": stats}

@router.get("/users")
async def get_user_permissions(
    user_id: int,
    request: Request,
    search: Optional[str] = None,
    permission_type: Optional[str] = None,
    status: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get user permissions matrix for Super Admin"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    query = """
        SELECT 
            udp.id,
            udp.user_id,
            u.username,
            u.email,
            u.full_name,
            udp.device_id,
            udp.platform,
            udp.camera_permission,
            udp.microphone_permission,
            udp.location_permission,
            udp.sms_permission,
            udp.contacts_permission,
            udp.phone_permission,
            udp.storage_permission,
            udp.notification_permission,
            udp.location_accuracy,
            udp.location_background,
            udp.app_version,
            udp.os_version,
            udp.updated_at
        FROM user_device_permissions udp
        JOIN users u ON udp.user_id = u.id
        WHERE 1=1
    """
    
    params = {}
    
    if search:
        query += " AND (u.username ILIKE :search OR u.email ILIKE :search OR u.full_name ILIKE :search)"
        params['search'] = f"%{search}%"
    
    if platform:
        query += " AND udp.platform = :platform"
        params['platform'] = platform
    
    if permission_type and status:
        query += f" AND udp.{permission_type}_permission = :status"
        params['status'] = status
    
    query += " ORDER BY udp.updated_at DESC LIMIT :limit OFFSET :offset"
    params['limit'] = limit
    params['offset'] = offset
    
    rows = (await request.app.state.db.execute(text(query), params)).fetchall()
    
    return {
        "ok": True,
        "permissions": [dict(r._mapping) for r in rows],
        "total": len(rows),
        "limit": limit,
        "offset": offset
    }

@router.get("/users/{target_user_id}")
async def get_user_permission_details(
    user_id: int,
    target_user_id: int,
    request: Request
):
    """Get specific user's permission details"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    rows = (await request.app.state.db.execute(text("""
        SELECT 
            udp.*,
            u.username,
            u.email,
            u.full_name
        FROM user_device_permissions udp
        JOIN users u ON udp.user_id = u.id
        WHERE udp.user_id = :target_user_id
    """), {"target_user_id": target_user_id})).fetchall()
    
    # Get permission change history
    history = (await request.app.state.db.execute(text("""
        SELECT *
        FROM permission_change_history
        WHERE user_id = :target_user_id
        ORDER BY changed_at DESC
        LIMIT 50
    """), {"target_user_id": target_user_id})).fetchall()
    
    return {
        "ok": True,
        "permissions": [dict(r._mapping) for r in rows],
        "history": [dict(h._mapping) for h in history]
    }

@router.get("/alerts")
async def get_permission_alerts(user_id: int, request: Request):
    """Get permission-related alerts for Super Admin"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    alerts = []
    
    # Users who denied critical permissions
    critical_denied = (await request.app.state.db.execute(text("""
        SELECT 
            u.username,
            u.email,
            udp.camera_permission,
            udp.microphone_permission,
            udp.location_permission,
            udp.sms_permission,
            udp.phone_permission,
            udp.updated_at
        FROM user_device_permissions udp
        JOIN users u ON udp.user_id = u.id
        WHERE location_permission = 'denied'
           OR phone_permission = 'denied'
           OR sms_permission = 'denied'
        ORDER BY udp.updated_at DESC
        LIMIT 20
    """))).fetchall()
    
    for row in critical_denied:
        denied_perms = []
        if row.location_permission == 'denied':
            denied_perms.append('Location')
        if row.phone_permission == 'denied':
            denied_perms.append('Phone')
        if row.sms_permission == 'denied':
            denied_perms.append('SMS')
        
        alerts.append({
            'type': 'critical_permission_denied',
            'severity': 'high',
            'user': row.username,
            'email': row.email,
            'message': f"User denied critical permissions: {', '.join(denied_perms)}",
            'timestamp': row.updated_at
        })
    
    # Users who recently revoked permissions
    recent_changes = (await request.app.state.db.execute(text("""
        SELECT 
            pch.*,
            u.username,
            u.email
        FROM permission_change_history pch
        JOIN users u ON pch.user_id = u.id
        WHERE pch.new_status = 'denied'
          AND pch.changed_at >= NOW() - INTERVAL '7 days'
        ORDER BY pch.changed_at DESC
        LIMIT 20
    """))).fetchall()
    
    for row in recent_changes:
        alerts.append({
            'type': 'permission_revoked',
            'severity': 'medium',
            'user': row.username,
            'email': row.email,
            'message': f"User revoked {row.permission_type} permission",
            'timestamp': row.changed_at
        })
    
    return {"ok": True, "alerts": alerts}
