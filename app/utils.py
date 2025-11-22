import jwt, hashlib
from .deps import get_settings
from fastapi import HTTPException, Header, Request

def get_current_user(authorization: str = Header(None)):
    """Extract user from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    settings = get_settings()
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return {
            "user_id": payload.get("sub"),
            "device_id": payload.get("device_id"),
            "role": payload.get("role"),
            "username": payload.get("username")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def jwt_encode(payload: dict) -> str:
    s = get_settings()
    return jwt.encode(payload, s.JWT_SECRET, algorithm="HS256")

def jwt_decode(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.JWT_SECRET, algorithms=["HS256"])

def trial_fingerprint(device_id: str, identity: str, payment_last4: str, ip_block: str) -> str:
    raw = f"{device_id}|{identity}|{payment_last4}|{ip_block}"
    return hashlib.sha256(raw.encode()).hexdigest()

def ai_cost_ok(monthly_so_far_rs: float, estimated_rs: float) -> bool:
    s = get_settings()
    return (monthly_so_far_rs + estimated_rs) <= s.AI_MONTHLY_CAP_RS

def is_admin(user_id: int) -> bool:
    s = get_settings()
    return str(user_id) in set(x.strip() for x in s.ADMIN_USER_IDS_CSV.split(","))

def get_db(request: Request):
    """Get database connection from app state"""
    return request.app.state.db

def require_super_admin(authorization: str = Header(None)):
    """Verify user is a super admin"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    settings = get_settings()
    admin_key = getattr(settings, 'ADMIN_KEY', None)
    
    # Check if token matches admin key first (before trying JWT decode)
    if admin_key and token == admin_key:
        return {"user_id": "super_admin", "role": "super_admin"}
    
    # Otherwise try to decode as JWT and check if user is admin
    try:
        import jwt
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user = {
            "user_id": payload.get("sub"),
            "role": payload.get("role"),
            "username": payload.get("username")
        }
        # Check if role is super_admin
        if user.get("role") == "super_admin":
            return user
        # OR check if user_id is in admin list (with safe fallback)
        try:
            if is_admin(int(user.get("user_id", 0))):
                return user
        except:
            pass
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        pass
    
    raise HTTPException(403, "Super admin access required")
