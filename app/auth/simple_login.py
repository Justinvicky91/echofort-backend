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
        
        # Debug: Log the username being searched
        print(f"[DEBUG] simple_login: Looking for username='{username}'")
        
        # Get employee record
        result = (await db.execute(text("""
            SELECT id, username, password_hash, role, is_super_admin, department
            FROM employees
            WHERE username = :u
        """), {"u": username})).fetchone()
        
        print(f"[DEBUG] simple_login: Query result={result}")
        
        if not result:
            # Check if table exists
            try:
                table_check = (await db.execute(text("SELECT COUNT(*) FROM employees"))).fetchone()
                print(f"[DEBUG] simple_login: Total employees in table: {table_check[0]}")
            except Exception as e:
                print(f"[DEBUG] simple_login: Table check error: {e}")
            raise HTTPException(401, "Invalid username or password")
        
        # Unpack tuple result
        emp_id, emp_username, password_hash, emp_role, is_super, dept = result
        
        # Verify password with bcrypt
        try:
            password_match = bcrypt.checkpw(password.encode(), password_hash.encode())
        except Exception as e:
            raise HTTPException(401, f"Password verification failed: {str(e)}")
        
        if not password_match:
            raise HTTPException(401, "Invalid username or password")
        
        # Create token
        token = jwt_encode({
            "sub": str(emp_id),
            "employee_id": str(emp_id),
            "user_type": "super_admin" if is_super else "employee",
            "role": emp_role,
            "exp": (datetime.utcnow() + timedelta(hours=8)).timestamp()
        })
        
        return {
            "success": True,
            "token": token,
            "user": {
                "id": emp_id,
                "username": emp_username,
                "role": emp_role,
                "is_super_admin": is_super,
                "department": dept
            },
            "redirect": "/admin/dashboard"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Login error: {str(e)}")

