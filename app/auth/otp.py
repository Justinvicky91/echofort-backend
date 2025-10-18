# app/auth/otp.py
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timedelta
from sqlalchemy import text
import random
from ..deps import get_settings
from ..utils import jwt_encode

router = APIRouter(prefix="/auth/otp", tags=["auth"])

@router.post("/request")
async def request_otp(payload: dict, request: Request, settings=Depends(get_settings)):
    """
    Request OTP via email
    OTP is returned in response for MVP (email sending disabled temporarily)
    """
    email = payload.get("email")
    phone = payload.get("phone", "")
    
    if not email:
        raise HTTPException(400, "Email required")
    
    # Generate random 6-digit OTP
    otp_code = str(random.randint(100000, 999999))
    
    db = request.app.state.db
    await db.execute(text("""
        INSERT INTO otps(identity, code, expires_at, created_at)
        VALUES (:i, :c, :e, NOW())
    """), {
        "i": email, 
        "c": otp_code, 
        "e": datetime.utcnow() + timedelta(minutes=5)
    })
    
    # MVP: Return OTP in response (replace with email later)
    return {
        "ok": True, 
        "message": f"OTP generated (check response)",
        "otp": otp_code,  # For testing - remove in production
        "email": email
    }

@router.post("/verify")
async def verify_otp(payload: dict, request: Request, settings=Depends(get_settings)):
    """
    Verify OTP and create user session with device binding
    Security: Prevents account sharing across multiple devices
    """
    email = payload.get("email")
    otp = payload.get("otp")
    device_id = payload.get("device_id")
    device_name = payload.get("device_name", "Unknown Device")
    name = payload.get("name", "User")
    
    if not all([email, otp, device_id]):
        raise HTTPException(400, "Email, OTP, and device_id required")
    
    db = request.app.state.db
    
    # Verify OTP
    otp_row = (await db.execute(text("""
        SELECT code, expires_at FROM otps 
        WHERE identity = :i 
        ORDER BY created_at DESC LIMIT 1
    """), {"i": email})).fetchone()
    
    if not otp_row or otp_row.code != otp:
        raise HTTPException(400, "Invalid OTP")
    
    if datetime.utcnow() > otp_row.expires_at:
        raise HTTPException(400, "OTP expired")
    
    # Check if user exists
    user_row = (await db.execute(text("""
        SELECT user_id, subscription_plan FROM users WHERE identity = :i
    """), {"i": email})).fetchone()
    
    if user_row:
        user_id = user_row[0]
        plan = user_row[1] or "trial"
        
        # Check device limit based on plan
        device_limit = 4 if plan == "family" else 1
        
        # Count active devices
        active_devices = (await db.execute(text("""
            SELECT COUNT(DISTINCT device_id) as count 
            FROM users 
            WHERE identity = :i AND device_bound = TRUE
        """), {"i": email})).fetchone()[0]
        
        # Check if this device is already registered
        device_exists = (await db.execute(text("""
            SELECT user_id FROM users 
            WHERE identity = :i AND device_id = :d
        """), {"i": email, "d": device_id})).fetchone()
        
        if not device_exists and active_devices >= device_limit:
            raise HTTPException(403, 
                f"Device limit reached. {plan.title()} plan allows {device_limit} device(s). "
                f"You have {active_devices} active device(s). "
                f"Please upgrade to Family plan for 4 devices or unbind a device."
            )
    
    # Create or update user with device binding
    result = await db.execute(text("""
        INSERT INTO users(
            identity, email, name, last_login, device_id, device_name, 
            device_bound, trial_started_at, created_at
        )
        VALUES (:e, :e, :n, NOW(), :d, :dn, TRUE, NOW(), NOW())
        ON CONFLICT (identity) DO UPDATE 
        SET last_login=NOW(), device_id=:d, device_name=:dn, 
            device_bound=TRUE, email=:e, name=:n
        RETURNING user_id
    """), {
        "e": email, 
        "n": name, 
        "d": device_id, 
        "dn": device_name
    })
    
    user_id = result.fetchone()[0]
    
    # Generate JWT token
    token = jwt_encode({
        "sub": email, 
        "user_id": user_id,
        "device_id": device_id, 
        "iat": int(datetime.utcnow().timestamp())
    })
    
    return {
        "ok": True, 
        "token": token, 
        "user_id": user_id,
        "device_id": device_id,
        "device_bound": True
    }

@router.post("/unbind-device")
async def unbind_device(payload: dict, request: Request):
    """
    Unbind a device to free up device slot
    Requires valid JWT token
    """
    from ..utils import get_current_user
    from fastapi import Header
    
    authorization = payload.get("authorization") or ""
    if not authorization:
        raise HTTPException(401, "Authorization header required")
    
    try:
        user = get_current_user(authorization)
    except:
        raise HTTPException(401, "Invalid token")
    
    device_id_to_unbind = payload.get("device_id")
    if not device_id_to_unbind:
        raise HTTPException(400, "device_id required")
    
    db = request.app.state.db
    
    # Unbind device
    await db.execute(text("""
        UPDATE users 
        SET device_bound = FALSE, device_id = NULL
        WHERE identity = :i AND device_id = :d
    """), {"i": user["sub"], "d": device_id_to_unbind})
    
    return {"ok": True, "message": "Device unbound successfully"}

@router.get("/devices")
async def list_devices(request: Request, authorization: str = Header(None)):
    """List all bound devices for user"""
    from ..utils import get_current_user
    
    if not authorization:
        raise HTTPException(401, "Authorization header required")
    
    try:
        user = get_current_user(authorization)
    except:
        raise HTTPException(401, "Invalid token")
    
    db = request.app.state.db
    
    devices = (await db.execute(text("""
        SELECT device_id, device_name, last_login, device_bound
        FROM users
        WHERE identity = :i AND device_bound = TRUE
        ORDER BY last_login DESC
    """), {"i": user["sub"]})).fetchall()
    
    return {
        "devices": [dict(d._mapping) for d in devices],
        "count": len(devices)
    }
