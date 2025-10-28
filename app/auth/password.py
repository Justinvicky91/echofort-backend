"""Password-based authentication endpoints"""
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import text
from datetime import datetime
import bcrypt
import random
from ..utils import jwt_encode
from ..deps import get_settings
from ..email_service import email_service

router = APIRouter(prefix="/auth/password", tags=["auth"])

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

@router.post("/set")
async def set_password(payload: dict, request: Request):
    """Set password for user (during signup or profile update)"""
    email = payload.get("email", "").lower().strip()
    password = payload.get("password")
    
    if not email or not password:
        raise HTTPException(400, "Email and password required")
    
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    
    db = request.app.state.db
    
    # Check if user exists
    user = (await db.execute(text("""
        SELECT user_id FROM users WHERE LOWER(identity) = :e LIMIT 1
    """), {"e": email})).fetchone()
    
    if not user:
        raise HTTPException(404, "User not found. Please sign up first.")
    
    # Hash and store password
    hashed = hash_password(password)
    await db.execute(text("""
        UPDATE users SET password_hash = :h WHERE LOWER(identity) = :e
    """), {"h": hashed, "e": email})
    await db.commit()
    
    return {"ok": True, "message": "Password set successfully"}

@router.post("/login")
async def login_with_password(payload: dict, request: Request):
    """Login with email and password"""
    email = payload.get("email", "").lower().strip()
    password = payload.get("password")
    device_id = payload.get("device_id")
    
    if not all([email, password, device_id]):
        raise HTTPException(400, "Email, password, and device_id required")
    
    db = request.app.state.db
    
    # Get user
    user = (await db.execute(text("""
        SELECT user_id, password_hash, role, name FROM users 
        WHERE LOWER(identity) = :e LIMIT 1
    """), {"e": email})).fetchone()
    
    if not user or not user.password_hash:
        raise HTTPException(401, "Invalid email or password")
    
    # Verify password
    if not verify_password(password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    
    # Update last login
    await db.execute(text("""
        UPDATE users SET last_login = NOW(), device_id = :d 
        WHERE user_id = :uid
    """), {"d": device_id, "uid": user.user_id})
    await db.commit()
    
    # Generate JWT
    token = jwt_encode({
        "sub": email,
        "user_id": user.user_id,
        "role": user.role or "customer",
        "device_id": device_id,
        "iat": int(datetime.utcnow().timestamp())
    })
    
    return {
        "ok": True,
        "token": token,
        "user_id": user.user_id,
        "role": user.role or "customer",
        "name": user.name
    }

@router.post("/forgot")
async def forgot_password(payload: dict, request: Request, settings=Depends(get_settings)):
    """Send OTP for password reset"""
    email = payload.get("email", "").lower().strip()
    
    if not email:
        raise HTTPException(400, "Email required")
    
    db = request.app.state.db
    
    # Check if user exists
    user = (await db.execute(text("""
        SELECT user_id, name FROM users WHERE LOWER(identity) = :e LIMIT 1
    """), {"e": email})).fetchone()
    
    if not user:
        # Don't reveal if user exists or not (security)
        return {"ok": True, "message": "If the email exists, an OTP has been sent"}
    
    # Invalidate old OTPs
    await db.execute(text("""
        DELETE FROM otps WHERE LOWER(identity) = :e
    """), {"e": email})
    
    # Generate OTP
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow().replace(microsecond=0)
    expires_at = expires_at.replace(minute=expires_at.minute + 10)
    
    # Store OTP
    await db.execute(text("""
        INSERT INTO otps(identity, code, expires_at, created_at)
        VALUES (:i, :c, :e, NOW())
    """), {"i": email, "c": otp_code, "e": expires_at})
    await db.commit()
    
    # Send email
    try:
        email_service.send_password_reset_otp(email, user.name, otp_code)
    except Exception as e:
        print(f"Failed to send password reset email: {e}")
    
    return {"ok": True, "message": "If the email exists, an OTP has been sent"}

@router.post("/reset")
async def reset_password(payload: dict, request: Request):
    """Reset password using OTP"""
    email = payload.get("email", "").lower().strip()
    otp = payload.get("otp")
    new_password = payload.get("new_password")
    
    if not all([email, otp, new_password]):
        raise HTTPException(400, "Email, OTP, and new password required")
    
    if len(new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    
    db = request.app.state.db
    
    # Verify OTP
    otp_row = (await db.execute(text("""
        SELECT code, expires_at FROM otps 
        WHERE LOWER(identity) = :i AND expires_at > NOW()
        ORDER BY created_at DESC LIMIT 1
    """), {"i": email})).fetchone()
    
    if not otp_row or otp_row.code != otp:
        raise HTTPException(400, "Invalid or expired OTP")
    
    # Hash new password
    hashed = hash_password(new_password)
    
    # Update password
    await db.execute(text("""
        UPDATE users SET password_hash = :h WHERE LOWER(identity) = :e
    """), {"h": hashed, "e": email})
    
    # Delete used OTP
    await db.execute(text("""
        DELETE FROM otps WHERE LOWER(identity) = :e
    """), {"e": email})
    await db.commit()
    
    return {"ok": True, "message": "Password reset successfully"}
