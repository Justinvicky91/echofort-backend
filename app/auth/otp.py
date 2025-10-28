# app/auth/otp.py
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from datetime import datetime, timedelta
from sqlalchemy import text
import random
from ..deps import get_settings
from ..utils import jwt_encode
from ..email_service_sendgrid import send_otp_email

router = APIRouter(prefix="/auth/otp", tags=["auth"])

@router.post("/request")
async def request_otp(payload: dict, request: Request, settings=Depends(get_settings)):
    """Request OTP via email (SendGrid)"""
    email = payload.get("email", "").lower().strip()
    phone = payload.get("phone", "")
    
    if not email:
        raise HTTPException(400, "Email required")
    
    db = request.app.state.db
    
    # Check if OTP was sent in the last 60 seconds (resend cooldown)
    last_otp = (await db.execute(text("""
        SELECT created_at FROM otps 
        WHERE LOWER(identity) = :i 
        ORDER BY created_at DESC LIMIT 1
    """), {"i": email})).fetchone()
    
    if last_otp:
        time_since_last = (datetime.utcnow() - last_otp.created_at).total_seconds()
        if time_since_last < 60:
            remaining = int(60 - time_since_last)
            raise HTTPException(429, f"Please wait {remaining} seconds before requesting a new OTP")
    
    # Invalidate all previous OTPs for this email
    await db.execute(text("""
        DELETE FROM otps WHERE LOWER(identity) = :i
    """), {"i": email})
    
    # Generate random 6-digit OTP
    otp_code = str(random.randint(100000, 999999))
    
    # Insert new OTP
    await db.execute(text("""
        INSERT INTO otps(identity, code, expires_at, created_at)
        VALUES (:i, :c, :e, NOW())
    """), {
        "i": email, 
        "c": otp_code, 
        "e": datetime.utcnow() + timedelta(minutes=5)
    })
    
    # Send OTP via email (Resend API)
    email_sent = send_otp_email(email, otp_code)
    
    return {
        "ok": True, 
        "message": f"OTP sent to {email}",
        "email_sent": email_sent
    }

@router.post("/verify")
async def verify_otp(payload: dict, request: Request, settings=Depends(get_settings)):
    """Verify OTP and create user session with device binding"""
    email = payload.get("email", "").lower().strip()
    otp = payload.get("otp")
    device_id = payload.get("device_id")
    device_name = payload.get("device_name", "Unknown Device")
    name = payload.get("name", "User")
    
    if not all([email, otp, device_id]):
        raise HTTPException(400, "Email, OTP, and device_id required")
    
    db = request.app.state.db
    
    # Verify OTP (get latest valid one)
    otp_row = (await db.execute(text("""
        SELECT code, expires_at FROM otps 
        WHERE LOWER(identity) = :i AND expires_at > NOW()
        ORDER BY created_at DESC LIMIT 1
    """), {"i": email})).fetchone()
    
    if not otp_row or otp_row.code != otp:
        raise HTTPException(400, "Invalid OTP")
    
    if datetime.utcnow() > otp_row.expires_at:
        raise HTTPException(400, "OTP expired")
    
    # Check device limit (1 for Basic, 4 for Family)
    user_row = (await db.execute(text("""
        SELECT user_id, subscription_plan FROM users WHERE identity = :i LIMIT 1
    """), {"i": email})).fetchone()
    
    if user_row:
        plan = user_row[1] or "trial"
        device_limit = 4 if plan == "family" else 1
        
        # Count active devices
        active_count = (await db.execute(text("""
            SELECT COUNT(DISTINCT device_id) FROM users 
            WHERE identity = :i AND device_bound = TRUE
        """), {"i": email})).scalar()
        
        # Check if THIS device already registered
        device_exists = (await db.execute(text("""
            SELECT 1 FROM users WHERE identity = :i AND device_id = :d
        """), {"i": email, "d": device_id})).fetchone()
        
        if not device_exists and active_count >= device_limit:
            raise HTTPException(403, f"Device limit reached. {plan.title()} plan allows {device_limit} device(s).")
    
    # Create or update user
    result = await db.execute(text("""
        INSERT INTO users(identity, email, name, last_login, device_id, device_name, device_bound, trial_started_at, created_at)
        VALUES (:e, :e, :n, NOW(), :d, :dn, TRUE, NOW(), NOW())
        ON CONFLICT (identity) DO UPDATE 
        SET last_login=NOW(), device_id=:d, device_name=:dn, device_bound=TRUE, email=:e, name=:n
        RETURNING user_id, role
    """), {"e": email, "n": name, "d": device_id, "dn": device_name})
    
    row = result.fetchone()
    user_id = row[0]
    role = row[1] if len(row) > 1 else 'customer'
    
    # Send welcome email (async, don't block)
    try:
        email_service.send_welcome_email(email, name)
    except:
        pass
    
    # Generate JWT token
    token = jwt_encode({
        "sub": email, 
        "user_id": user_id,
        "role": role,
        "device_id": device_id, 
        "iat": int(datetime.utcnow().timestamp())
    })
    
    return {
        "ok": True, 
        "token": token, 
        "user_id": user_id,
        "role": role,
        "device_id": device_id,
        "device_bound": True
    }
