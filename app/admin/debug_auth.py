"""
Debug endpoint to test JWT authentication
"""
from fastapi import APIRouter, Header, HTTPException
from ..deps import get_settings
from datetime import datetime, timedelta
import jwt

router = APIRouter(prefix="/admin/debug", tags=["Debug"])

@router.get("/test-jwt")
async def test_jwt_decode(authorization: str = Header(None)):
    """Test JWT decoding and role extraction"""
    if not authorization or not authorization.startswith("Bearer "):
        return {"error": "Missing or invalid authorization header"}
    
    token = authorization.replace("Bearer ", "")
    settings = get_settings()
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user = {
            "user_id": payload.get("sub"),
            "role": payload.get("role"),
            "username": payload.get("username")
        }
        
        return {
            "ok": True,
            "payload": payload,
            "user": user,
            "role_check": user.get("role") == "super_admin",
            "role_value": user.get("role"),
            "expected": "super_admin"
        }
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired"}
    except jwt.InvalidTokenError as e:
        return {"error": f"Invalid token: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@router.get("/generate-super-admin-jwt")
async def generate_super_admin_jwt():
    """Generate a new JWT for Super Admin (for testing)"""
    settings = get_settings()
    
    payload = {
        "sub": "1",
        "username": "EchofortSuperAdmin91",
        "role": "super_admin",
        "exp": int((datetime.utcnow() + timedelta(days=365)).timestamp())
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    
    return {
        "ok": True,
        "token": token,
        "payload": payload,
        "note": "This token is valid for 1 year"
    }
