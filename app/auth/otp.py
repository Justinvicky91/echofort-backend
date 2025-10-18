# app/auth/otp.py
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timedelta
from sqlalchemy import text
import random
from ..deps import get_settings
from ..utils import jwt_encode
from ..email_service import email_service

router = APIRouter(prefix="/auth/otp", tags=["auth"])

@router.post("/request")
async def request_otp(payload: dict, request: Request, settings=Depends(get_settings)):
    """
    Request OTP via email
    Payload: {"email": "user@example.com", "phone": "+919876543210"}
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
    
    # Send OTP via email
    email_sent = email_service.send_otp(email, otp_code, phone)
    
    return {
        "ok": True, 
        "message": f"OTP sent to {email}",
        "email_sent": email_sent
    }

@router.post("/verify")
async def verify_otp(payload: dict, request: Request, settings=Depends(get_settings)):
    """Verify OTP and create user session"""
    email = payload.get("email")
    otp = payload.get("otp")
    device_id = payload.get("device_id", "web")
    name = payload.get("name", "User")
    
    if not all([email, otp]):
        raise HTTPException(400, "Email and OTP required")
    
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
    
    # Create or update user
    result = await db.execute(text("""
        INSERT INTO users(identity, email, name, last_login, device_id, trial_started_at, created_at)
        VALUES (:e, :e, :n, NOW(), :d, NOW(), NOW())
        ON CONFLICT (identity) DO UPDATE 
        SET last_login=NOW(), device_id=:d, email=:e, name=:n
        RETURNING user_id
    """), {"e": email, "n": name, "d": device_id})
    
    user_id = result.fetchone()[0]
    
    # Send welcome email (async, don't block)
    try:
        email_service.send_welcome_email(email, name)
    except:
        pass  # Don't fail if welcome email fails
    
    # Generate JWT token
    token = jwt_encode({
        "sub": email, 
        "user_id": user_id,
        "device_id": device_id, 
        "iat": int(datetime.utcnow().timestamp())
    })
    
    return {"ok": True, "token": token, "user_id": user_id}
