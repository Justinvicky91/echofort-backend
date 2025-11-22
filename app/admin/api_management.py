from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from ..utils import is_admin

router = APIRouter(prefix="/admin/api", tags=["admin-api"])

@router.get("/endpoints")
async def get_all_endpoints(request: Request, user_id: int = None):
    """Get list of all API endpoints"""
    # Super Admin can access without user_id
    if user_id and not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    # Define all API endpoints with metadata
    endpoints = [
        # Authentication
        {"category": "Authentication", "method": "POST", "path": "/api/auth/login", "description": "User login"},
        {"category": "Authentication", "method": "POST", "path": "/api/auth/register", "description": "User registration"},
        {"category": "Authentication", "method": "POST", "path": "/api/auth/2fa/setup", "description": "Setup 2FA"},
        {"category": "Authentication", "method": "POST", "path": "/api/auth/2fa/verify", "description": "Verify 2FA"},
        
        # Mobile - Caller ID
        {"category": "Mobile - Caller ID", "method": "POST", "path": "/api/mobile/caller-id/lookup", "description": "Lookup phone number"},
        {"category": "Mobile - Caller ID", "method": "POST", "path": "/api/mobile/caller-id/report-spam", "description": "Report spam number"},
        {"category": "Mobile - Caller ID", "method": "GET", "path": "/api/mobile/caller-id/blocked-numbers", "description": "Get blocked numbers"},
        {"category": "Mobile - Caller ID", "method": "POST", "path": "/api/mobile/caller-id/block-number", "description": "Block a number"},
        
        # Mobile - SMS Detection
        {"category": "Mobile - SMS", "method": "POST", "path": "/api/mobile/sms/scan", "description": "Scan SMS for scams"},
        {"category": "Mobile - SMS", "method": "POST", "path": "/api/mobile/sms/report", "description": "Report spam SMS"},
        {"category": "Mobile - SMS", "method": "GET", "path": "/api/mobile/sms/statistics", "description": "Get SMS scan statistics"},
        
        # Mobile - URL Checker
        {"category": "Mobile - URL Checker", "method": "POST", "path": "/api/mobile/url-checker/scan", "description": "Check URL safety"},
        {"category": "Mobile - URL Checker", "method": "POST", "path": "/api/mobile/url-checker/report", "description": "Report malicious URL"},
        {"category": "Mobile - URL Checker", "method": "GET", "path": "/api/mobile/url-checker/history", "description": "Get scan history"},
        
        # Mobile - Push Notifications
        {"category": "Mobile - Notifications", "method": "POST", "path": "/api/mobile/push/register", "description": "Register device for push"},
        {"category": "Mobile - Notifications", "method": "POST", "path": "/api/mobile/push/send", "description": "Send push notification"},
        {"category": "Mobile - Notifications", "method": "GET", "path": "/api/mobile/push/settings", "description": "Get notification settings"},
        
        # Mobile - User Profile
        {"category": "Mobile - Profile", "method": "GET", "path": "/api/mobile/profile", "description": "Get user profile"},
        {"category": "Mobile - Profile", "method": "PUT", "path": "/api/mobile/profile", "description": "Update user profile"},
        {"category": "Mobile - Profile", "method": "GET", "path": "/api/mobile/profile/statistics", "description": "Get user statistics"},
        
        # Mobile - Emergency
        {"category": "Mobile - Emergency", "method": "POST", "path": "/api/mobile/emergency/sos", "description": "Trigger SOS alert"},
        {"category": "Mobile - Emergency", "method": "POST", "path": "/api/mobile/emergency/contacts", "description": "Add emergency contact"},
        {"category": "Mobile - Emergency", "method": "GET", "path": "/api/mobile/emergency/contacts", "description": "Get emergency contacts"},
        
        # Mobile - Call Analysis
        {"category": "Mobile - Call Analysis", "method": "POST", "path": "/api/mobile/call-analysis/start", "description": "Start call analysis"},
        {"category": "Mobile - Call Analysis", "method": "POST", "path": "/api/mobile/call-analysis/update", "description": "Update call analysis"},
        {"category": "Mobile - Call Analysis", "method": "GET", "path": "/api/mobile/call-analysis/results", "description": "Get analysis results"},
        
        # GPS Tracking
        {"category": "GPS Tracking", "method": "POST", "path": "/api/gps/update", "description": "Update GPS location"},
        {"category": "GPS Tracking", "method": "GET", "path": "/api/gps/history", "description": "Get location history"},
        {"category": "GPS Tracking", "method": "POST", "path": "/api/gps/geofence", "description": "Create geofence"},
        
        # Screen Time
        {"category": "Screen Time", "method": "POST", "path": "/api/screentime/log", "description": "Log screen time"},
        {"category": "Screen Time", "method": "GET", "path": "/api/screentime/stats", "description": "Get screen time stats"},
        {"category": "Screen Time", "method": "POST", "path": "/api/screentime/limits", "description": "Set screen time limits"},
        
        # Family Management
        {"category": "Family", "method": "POST", "path": "/api/family/add-member", "description": "Add family member"},
        {"category": "Family", "method": "GET", "path": "/api/family/members", "description": "Get family members"},
        {"category": "Family", "method": "DELETE", "path": "/api/family/remove/{id}", "description": "Remove family member"},
        
        # Subscriptions
        {"category": "Subscriptions", "method": "GET", "path": "/api/subscription/plans", "description": "Get subscription plans"},
        {"category": "Subscriptions", "method": "POST", "path": "/api/subscription/create-order", "description": "Create subscription order"},
        {"category": "Subscriptions", "method": "GET", "path": "/api/subscription/current", "description": "Get current subscription"},
        
        # Payments
        {"category": "Payments", "method": "POST", "path": "/api/payment/verify", "description": "Verify payment"},
        {"category": "Payments", "method": "GET", "path": "/api/payment/history", "description": "Get payment history"},
        
        # AI Assistant
        {"category": "AI Assistant", "method": "POST", "path": "/api/ai/chat", "description": "Chat with AI assistant"},
        {"category": "AI Assistant", "method": "GET", "path": "/api/ai/history", "description": "Get chat history"},
        
        # Admin - Vault
        {"category": "Admin - Vault", "method": "GET", "path": "/admin/vault/call-recordings", "description": "Get all call recordings"},
        {"category": "Admin - Vault", "method": "GET", "path": "/admin/vault/evidence", "description": "Get all evidence"},
        {"category": "Admin - Vault", "method": "GET", "path": "/admin/vault/stats", "description": "Get vault statistics"},
        
        # Admin - User Activity
        {"category": "Admin - Activity", "method": "GET", "path": "/admin/user-activity", "description": "Get all user activities"},
        {"category": "Admin - Activity", "method": "GET", "path": "/admin/user-activity/stats/overview", "description": "Get activity statistics"},
        
        # Admin - Permissions
        {"category": "Admin - Permissions", "method": "GET", "path": "/admin/permissions/overview", "description": "Get permissions overview"},
        {"category": "Admin - Permissions", "method": "GET", "path": "/admin/permissions/users", "description": "Get user permissions matrix"},
        {"category": "Admin - Permissions", "method": "GET", "path": "/admin/permissions/alerts", "description": "Get permission alerts"},
        
        # Admin - Employees
        {"category": "Admin - Employees", "method": "GET", "path": "/admin/employees", "description": "Get all employees"},
        {"category": "Admin - Employees", "method": "POST", "path": "/admin/employees/assign", "description": "Assign employee role"},
        {"category": "Admin - Employees", "method": "GET", "path": "/admin/employees/verification-queue", "description": "Get verification queue"},
    ]
    
    return {"ok": True, "endpoints": endpoints, "total": len(endpoints)}

@router.get("/health")
async def get_api_health(request: Request, user_id: int = None):
    """Get API health status"""
    # Super Admin can access without user_id
    if user_id and not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    # Check database connection
    try:
        await request.app.state.db.execute(text("SELECT 1"))
        db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    return {
        "ok": True,
        "status": "operational",
        "database": db_status,
        "timestamp": "CURRENT_TIMESTAMP"
    }

@router.get("/stats")
async def get_api_statistics(request: Request, user_id: int = None):
    """Get API usage statistics"""
    # Super Admin can access without user_id
    if user_id and not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    stats = {}
    
    # Total users
    total_users = (await request.app.state.db.execute(text("""
        SELECT COUNT(*) as count FROM users
    """))).fetchone()
    stats['total_users'] = total_users[0] if total_users else 0
    
    # Active users (logged in last 7 days)
    active_users = (await request.app.state.db.execute(text("""
        SELECT COUNT(DISTINCT user_id) as count
        FROM user_activity_log
        WHERE timestamp >= NOW() - INTERVAL '7 days'
    """))).fetchone()
    stats['active_users_7d'] = active_users[0] if active_users else 0
    
    # Total API calls (from activity log)
    total_calls = (await request.app.state.db.execute(text("""
        SELECT COUNT(*) as count FROM user_activity_log
    """))).fetchone()
    stats['total_api_calls'] = total_calls[0] if total_calls else 0
    
    # API calls today
    calls_today = (await request.app.state.db.execute(text("""
        SELECT COUNT(*) as count
        FROM user_activity_log
        WHERE timestamp >= CURRENT_DATE
    """))).fetchone()
    stats['api_calls_today'] = calls_today[0] if calls_today else 0
    
    return {"ok": True, "stats": stats}
