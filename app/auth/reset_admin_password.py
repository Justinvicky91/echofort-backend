# app/auth/reset_admin_password.py
"""
Temporary endpoint to reset super admin password
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
import bcrypt

router = APIRouter(prefix="/auth/admin", tags=["auth"])

@router.post("/reset-password")
async def reset_admin_password(payload: dict, request: Request):
    """
    Reset super admin password - TEMPORARY ENDPOINT
    """
    username = payload.get("username", "").strip()
    new_password = payload.get("new_password", "")
    
    if not username or not new_password:
        raise HTTPException(400, "Username and new_password required")
    
    try:
        db = request.app.state.db
        
        # Check if user exists and is super admin
        result = (await db.execute(text("""
            SELECT id, is_super_admin
            FROM employees
            WHERE username = :u
        """), {"u": username})).fetchone()
        
        if not result:
            raise HTTPException(404, "User not found")
        
        emp_id, is_super = result
        
        if not is_super:
            raise HTTPException(403, "Only super admin password can be reset via this endpoint")
        
        # Hash new password
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Update password
        await db.execute(text("""
            UPDATE employees
            SET password_hash = :ph
            WHERE id = :id
        """), {"ph": password_hash, "id": emp_id})
        await db.commit()
        
        return {
            "success": True,
            "message": f"Password reset successfully for {username}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Password reset error: {str(e)}")
