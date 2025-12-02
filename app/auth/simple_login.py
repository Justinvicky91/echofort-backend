# app/auth/simple_login.py
"""
Simple direct login endpoint for Super Admin
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from datetime import datetime, timedelta
import bcrypt
from ..utils import jwt_encode
from ..deps import get_settings
# Temporarily disabled RBAC imports to debug Railway crash
# from ..rbac import get_permissions, get_sidebar_items_for_role

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/simple-login")
async def simple_login(payload: dict, request: Request):
    """
    Simple login endpoint - just username and password
    """
    settings = get_settings()
    username = payload.get("username", "").strip()
    password = payload.get("password", "")
    
    # DEV MODE: Skip password check if DEV_AUTH_DISABLED
    if not settings.DEV_AUTH_DISABLED:
        if not username or not password:
            raise HTTPException(400, "Username and password required")
    else:
        if not username:
            raise HTTPException(400, "Username required")
        print(f"[DEV MODE] Auth disabled - accepting username-only login for: {username}")
    
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
        
        # Verify password with bcrypt (skip if DEV_AUTH_DISABLED)
        if not settings.DEV_AUTH_DISABLED:
            try:
                password_match = bcrypt.checkpw(password.encode(), password_hash.encode())
            except Exception as e:
                raise HTTPException(401, f"Password verification failed: {str(e)}")
            
            if not password_match:
                raise HTTPException(401, "Invalid username or password")
        else:
            print(f"[DEV MODE] Skipping password verification for: {username}")
        
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
            # Temporarily disabled RBAC response fields
            # "permissions": get_permissions(emp_role),
            # "sidebar_items": get_sidebar_items_for_role(emp_role),
            "redirect": "/admin/dashboard"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Login error: {str(e)}")

