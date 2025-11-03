"""
Mobile App Authentication Endpoints
Simple login and registration for mobile app users
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from datetime import datetime, timedelta
import bcrypt
from ..utils import jwt_encode

router = APIRouter(prefix="/api/auth", tags=["Mobile Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    phone: str


@router.post("/login")
async def mobile_login(payload: LoginRequest, request: Request):
    """
    Simple login endpoint for mobile app users
    """
    try:
        db = request.app.state.db
        
        # Get user record from users table
        result = (await db.execute(text("""
            SELECT id, username, email, password_hash, phone_number, active
            FROM users
            WHERE username = :u OR email = :u
        """), {"u": payload.username})).fetchone()
        
        if not result:
            raise HTTPException(401, "Invalid username or password")
        
        user_id, username, email, password_hash, phone, active = result
        
        # Check if user is active
        if not active:
            raise HTTPException(403, "Account is inactive")
        
        # Verify password
        if not bcrypt.checkpw(payload.password.encode('utf-8'), password_hash.encode('utf-8')):
            raise HTTPException(401, "Invalid username or password")
        
        # Generate JWT token
        token = jwt_encode({
            "userId": user_id,
            "username": username,
            "email": email,
            "type": "user",
            "exp": (datetime.utcnow() + timedelta(days=30)).timestamp()
        })
        
        return {
            "ok": True,
            "token": token,
            "userId": user_id,
            "username": username,
            "email": email,
            "phone": phone
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] mobile_login: {e}")
        raise HTTPException(500, f"Login failed: {str(e)}")


@router.post("/register")
async def mobile_register(payload: RegisterRequest, request: Request):
    """
    Registration endpoint for mobile app users
    """
    try:
        db = request.app.state.db
        
        # Check if username already exists
        username_check = (await db.execute(text("""
            SELECT id FROM users WHERE username = :u LIMIT 1
        """), {"u": payload.username})).fetchone()
        
        if username_check:
            raise HTTPException(400, "Username already exists")
        
        # Check if email already exists
        email_check = (await db.execute(text("""
            SELECT id FROM users WHERE email = :e LIMIT 1
        """), {"e": payload.email})).fetchone()
        
        if email_check:
            raise HTTPException(400, "Email already exists")
        
        # Hash password
        password_hash = bcrypt.hashpw(payload.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user record
        result = (await db.execute(text("""
            INSERT INTO users 
            (username, email, password_hash, phone_number, active, created_at, updated_at)
            VALUES (:username, :email, :password_hash, :phone, true, NOW(), NOW())
            RETURNING id, username, email, phone_number
        """), {
            "username": payload.username,
            "email": payload.email,
            "password_hash": password_hash,
            "phone": payload.phone
        })).fetchone()
        
        user_id, username, email, phone = result
        
        return {
            "ok": True,
            "message": "Registration successful",
            "userId": user_id,
            "username": username,
            "email": email,
            "phone": phone
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] mobile_register: {e}")
        raise HTTPException(500, f"Registration failed: {str(e)}")
