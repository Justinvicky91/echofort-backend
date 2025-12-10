"""
BLOCK S2 - User Dashboard API
Returns plan-specific dashboard data for Basic, Personal, and Family plans
Single endpoint for both web and mobile apps
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from app.deps import get_settings
import psycopg
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import jwt

router = APIRouter(prefix="/user", tags=["user-dashboard"])

def decode_jwt_token(token: str) -> dict:
    """Decode and validate JWT token"""
    settings = get_settings()
    secret_key = getattr(settings, 'JWT_SECRET_KEY', 'echofort-jwt-secret-key-change-in-production')
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_from_token(authorization: Optional[str] = Header(None)) -> dict:
    """Extract user from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    return decode_jwt_token(token)

class DashboardResponse(BaseModel):
    dashboard_type: str
    user: dict
    data: dict
    upgrade_available: bool = False

@router.get("/dashboard", response_model=DashboardResponse)
async def get_user_dashboard(current_user: dict = Depends(get_current_user_from_token)):
    """
    Get user dashboard data based on subscription plan
    Returns different data for Basic, Personal, and Family plans
    """
    settings = get_settings()
    dsn = settings.DATABASE_URL
    
    user_id = current_user.get('user_id')
    
    try:
        with psycopg.connect(dsn) as conn:
            try:
                with conn.cursor() as cur:
                    # Get user details
                    cur.execute("""
                        SELECT id, email, name, phone, plan_id, subscription_status, dashboard_type,
                               country, state, district, created_at
                        FROM users 
                        WHERE id = %s
                    """, (user_id,))
                    
                    user_row = cur.fetchone()
                    if not user_row:
                        raise HTTPException(status_code=404, detail="User not found")
                    
                    (uid, email, name, phone, plan_id, subscription_status, dashboard_type,
                     country, state, district, created_at) = user_row
                    
                    user_info = {
                        'id': uid,
                        'email': email,
                        'name': name,
                        'phone': phone,
                        'plan_id': plan_id,
                        'subscription_status': subscription_status,
                        'dashboard_type': dashboard_type,
                        'location': {
                            'country': country,
                            'state': state,
                            'district': district
                        },
                        'member_since': created_at.isoformat() if created_at else None
                    }
                    
                    # Determine dashboard data based on plan
                    if dashboard_type == 'basic':
                        dashboard_data = await get_basic_dashboard_data(cur, user_id)
                        upgrade_available = True
                    elif dashboard_type == 'personal':
                        dashboard_data = await get_personal_dashboard_data(cur, user_id)
                        upgrade_available = True  # Can upgrade to Family
                    elif dashboard_type == 'family_admin':
                        dashboard_data = await get_family_dashboard_data(cur, user_id)
                        upgrade_available = False
                    else:
                        # No subscription - show limited data
                        dashboard_data = {
                            'message': 'No active subscription',
                            'recent_alerts': await get_limited_alerts(cur, user_id, limit=3)
                        }
                        upgrade_available = True
                    
                    return DashboardResponse(
                        dashboard_type=dashboard_type or 'none',
                        user=user_info,
                        data=dashboard_data,
                        upgrade_available=upgrade_available
                    )
            except HTTPException:
                raise
            except Exception as e:
                conn.rollback()
                print(f"[DASHBOARD] Error in transaction: {str(e)}", flush=True)
                raise
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DASHBOARD] Error fetching dashboard: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data")

async def get_basic_dashboard_data(cur, user_id: int) -> dict:
    """
    Basic Plan Dashboard
    - Limited recent alerts
    - Basic statistics
    - Upgrade CTA
    """
    # Get recent scam alerts (last 7 days, limited to 5)
    cur.execute("""
        SELECT id, title, description, severity, created_at
        FROM scam_alerts
        WHERE created_at >= NOW() - INTERVAL '7 days'
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    alerts = []
    for row in cur.fetchall():
        alerts.append({
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'severity': row[3],
            'created_at': row[4].isoformat() if row[4] else None
        })
    
    # Basic statistics
    cur.execute("""
        SELECT COUNT(*) FROM scam_alerts
        WHERE created_at >= NOW() - INTERVAL '30 days'
    """)
    total_alerts_30d = cur.fetchone()[0]
    
    return {
        'plan': 'basic',
        'features': {
            'scam_alerts': True,
            'call_protection': False,
            'recordings': False,
            'family_protection': False
        },
        'recent_alerts': alerts,
        'statistics': {
            'total_alerts_30d': total_alerts_30d
        },
        'upgrade_message': 'Upgrade to Personal for call protection and recordings',
        'upgrade_benefits': [
            'Real-time call protection',
            'Call recordings and analysis',
            'Advanced scam detection',
            'Priority support'
        ]
    }

async def get_personal_dashboard_data(cur, user_id: int) -> dict:
    """
    Personal Plan Dashboard
    - Full scam alerts
    - Call logs
    - Recordings
    - Statistics
    """
    # Get scam alerts (last 30 days)
    cur.execute("""
        SELECT id, title, description, severity, created_at
        FROM scam_alerts
        WHERE created_at >= NOW() - INTERVAL '30 days'
        ORDER BY created_at DESC
        LIMIT 20
    """)
    
    alerts = []
    for row in cur.fetchall():
        alerts.append({
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'severity': row[3],
            'created_at': row[4].isoformat() if row[4] else None
        })
    
    # Get call logs (if table exists)
    try:
        cur.execute("""
            SELECT id, phone_number, call_type, duration, blocked, created_at
            FROM call_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (user_id,))
        
        call_logs = []
        for row in cur.fetchall():
            call_logs.append({
                'id': row[0],
                'phone_number': row[1],
                'call_type': row[2],
                'duration': row[3],
                'blocked': row[4],
                'created_at': row[5].isoformat() if row[5] else None
            })
    except:
        call_logs = []
    
    # Get recordings (if table exists)
    try:
        cur.execute("""
            SELECT id, call_id, duration, file_path, created_at
            FROM call_recordings
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 5
        """, (user_id,))
        
        recordings = []
        for row in cur.fetchall():
            recordings.append({
                'id': row[0],
                'call_id': row[1],
                'duration': row[2],
                'file_path': row[3],
                'created_at': row[4].isoformat() if row[4] else None
            })
    except:
        recordings = []
    
    # Statistics
    cur.execute("""
        SELECT COUNT(*) FROM scam_alerts
        WHERE created_at >= NOW() - INTERVAL '30 days'
    """)
    total_alerts = cur.fetchone()[0]
    
    try:
        cur.execute("""
            SELECT COUNT(*) FROM call_history
            WHERE user_id = %s AND blocked = TRUE
        """, (user_id,))
        blocked_calls = cur.fetchone()[0]
    except:
        blocked_calls = 0
    
    return {
        'plan': 'personal',
        'features': {
            'scam_alerts': True,
            'call_protection': True,
            'recordings': True,
            'family_protection': False
        },
        'scam_alerts': alerts,
        'call_logs': call_logs,
        'recordings': recordings,
        'statistics': {
            'total_alerts_30d': total_alerts,
            'blocked_calls': blocked_calls,
            'total_recordings': len(recordings)
        },
        'upgrade_message': 'Upgrade to Family to protect your loved ones',
        'upgrade_benefits': [
            'Protect up to 5 family members',
            'Real-time location tracking',
            'Family-wide scam alerts',
            'Centralized management'
        ]
    }

async def get_family_dashboard_data(cur, user_id: int) -> dict:
    """
    Family Plan Dashboard
    - All Personal features
    - Family members management
    - GPS locations
    - Aggregated statistics
    """
    # Get Personal dashboard data first
    personal_data = await get_personal_dashboard_data(cur, user_id)
    
    # Get family members (if table exists)
    try:
        cur.execute("""
            SELECT id, name, phone, relationship, added_at
            FROM family_members
            WHERE owner_id = %s
            ORDER BY added_at DESC
        """, (user_id,))
        
        family_members = []
        for row in cur.fetchall():
            family_members.append({
                'id': row[0],
                'name': row[1],
                'phone': row[2],
                'relationship': row[3],
                'added_at': row[4].isoformat() if row[4] else None
            })
    except:
        family_members = []
    
    # Get GPS locations (if table exists)
    try:
        cur.execute("""
            SELECT fm.name, gl.latitude, gl.longitude, gl.updated_at
            FROM gps_locations gl
            JOIN family_members fm ON gl.member_id = fm.id
            WHERE fm.owner_id = %s
            ORDER BY gl.updated_at DESC
            LIMIT 10
        """, (user_id,))
        
        locations = []
        for row in cur.fetchall():
            locations.append({
                'member_name': row[0],
                'latitude': float(row[1]) if row[1] else None,
                'longitude': float(row[2]) if row[2] else None,
                'updated_at': row[3].isoformat() if row[3] else None
            })
    except:
        locations = []
    
    return {
        'plan': 'family',
        'features': {
            'scam_alerts': True,
            'call_protection': True,
            'recordings': True,
            'family_protection': True
        },
        'scam_alerts': personal_data['scam_alerts'],
        'call_logs': personal_data['call_logs'],
        'recordings': personal_data['recordings'],
        'family_members': family_members,
        'gps_locations': locations,
        'statistics': {
            **personal_data['statistics'],
            'family_members_count': len(family_members),
            'protected_members': len(family_members) + 1  # +1 for owner
        }
    }

async def get_limited_alerts(cur, user_id: int, limit: int = 3) -> list:
    """Get limited alerts for users without subscription"""
    cur.execute("""
        SELECT id, title, severity, created_at
        FROM scam_alerts
        WHERE created_at >= NOW() - INTERVAL '7 days'
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))
    
    alerts = []
    for row in cur.fetchall():
        alerts.append({
            'id': row[0],
            'title': row[1],
            'severity': row[2],
            'created_at': row[3].isoformat() if row[3] else None
        })
    
    return alerts
