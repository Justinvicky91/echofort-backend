# app/auth/simple_login.py
"""
Simple direct login endpoint for Super Admin
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from datetime import datetime, timedelta
import bcrypt
from ..utils import jwt_encode

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/simple-login")
async def simple_login(payload: dict, request: Request):
    """
    Simple login endpoint - just username and password
    """
    username = payload.get("username", "").strip()
    password = payload.get("password", "")
    
    if not username or not password:
        raise HTTPException(400, "Username and password required")
    
    try:
        db = request.app.state.db
        
        # Get employee record
        result = (await db.execute(text("""
            SELECT id, username, password_hash, role, is_super_admin, department
            FROM employees
            WHERE username = :u
        """), {"u": username})).fetchone()
        
        if not result:
            raise HTTPException(401, "Invalid username or password")
        
        # Verify password with bcrypt
        try:
            password_match = bcrypt.checkpw(password.encode(), result['password_hash'].encode())
        except Exception as e:
            raise HTTPException(401, f"Password verification failed: {str(e)}")
        
        if not password_match:
            raise HTTPException(401, "Invalid username or password")
        
        # Create token
        token = jwt_encode({
            "sub": str(result['id']),
            "employee_id": str(result['id']),
            "user_type": "super_admin" if result['is_super_admin'] else "employee",
            "role": result['role'],
            "exp": (datetime.utcnow() + timedelta(hours=8)).timestamp()
        })
        
        return {
            "success": True,
            "token": token,
            "user": {
                "id": result['id'],
                "username": result['username'],
                "role": result['role'],
                "is_super_admin": result['is_super_admin'],
                "department": result['department']
            },
            "redirect": "/admin/dashboard"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Login error: {str(e)}")

