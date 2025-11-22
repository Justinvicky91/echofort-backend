"""
Debug endpoint to test JWT authentication
"""
from fastapi import APIRouter, Header, HTTPException
from ..deps import get_settings
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
