# app/test_endpoints.py
from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(prefix="/test", tags=["testing"])

@router.get("/ping")
async def ping():
    """Simple ping test"""
    return {"ok": True, "message": "EchoFort API is working!"}

@router.get("/db-test")
async def db_test(request: Request):
    """Test database connection"""
    try:
        db = request.app.state.db
        result = await db.execute(text("SELECT COUNT(*) as count FROM users"))
        row = result.fetchone()
        user_count = row[0] if row else 0
        
        return {
            "ok": True,
            "database": "connected",
            "user_count": user_count
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/create-test-user")
async def create_test_user(request: Request):
    """Create a test user for testing endpoints"""
    try:
        db = request.app.state.db
        
        # Create test user
        await db.execute(text("""
            INSERT INTO users(identity, name, trial_started_at, created_at)
            VALUES ('test_user_123', 'Test User', NOW(), NOW())
            ON CONFLICT (identity) DO NOTHING
        """))
        
        # Get user_id
        result = await db.execute(text("""
            SELECT user_id FROM users WHERE identity = 'test_user_123'
        """))
        row = result.fetchone()
        user_id = row[0] if row else None
        
        return {
            "ok": True,
            "message": "Test user created",
            "user_id": user_id,
            "identity": "test_user_123"
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/endpoints")
async def list_endpoints():
    """List all available endpoints"""
    return {
        "ok": True,
        "endpoints": {
            "health": "/health",
            "auth": {
                "request_otp": "POST /auth/otp/request",
                "verify_otp": "POST /auth/otp/verify"
            },
            "ai": {
                "voice_score": "POST /ai/voice/score",
                "image_scan": "POST /ai/media/scan"
            },
            "gps": {
                "save_location": "POST /gps/location (requires auth)",
                "history": "GET /gps/history (requires auth)",
                "geofence": "POST /gps/geofence (requires auth)"
            },
            "screentime": {
                "log": "POST /screentime/log (requires auth)",
                "daily": "GET /screentime/daily (requires auth)",
                "weekly": "GET /screentime/weekly (requires auth)",
                "addiction_risk": "GET /screentime/addiction-risk (requires auth)"
            },
            "family": {
                "create": "POST /family/create (requires auth)",
                "add_member": "POST /family/add-member (requires auth)",
                "members": "GET /family/members (requires auth)",
                "alerts": "GET /family/alerts (requires auth)"
            },
            "subscription": {
                "status": "GET /subscription/status (requires auth)",
                "upgrade": "POST /subscription/upgrade (requires auth)",
                "cancel": "POST /subscription/cancel (requires auth)"
            }
        }
    }
