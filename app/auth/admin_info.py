"""
Temporary endpoint to retrieve super admin info
DELETE THIS FILE after successful login
"""
from fastapi import APIRouter
from sqlalchemy import text
from app.deps import get_db
import bcrypt

router = APIRouter(prefix="/admin", tags=["admin-temp"])

@router.get("/info")
async def get_admin_info(db = get_db()):
    """Get super admin username - TEMPORARY ENDPOINT"""
    result = (await db.execute(text("""
        SELECT e.id, e.username, e.role, e.is_super_admin, e.user_id
        FROM employees e
        WHERE e.is_super_admin = true
        LIMIT 1
    """))).fetchone()
    
    if not result:
        return {"error": "No super admin found"}
    
    return {
        "id": result['id'],
        "username": result['username'],
        "role": result['role'],
        "is_super_admin": result['is_super_admin'],
        "user_id": result['user_id']
    }

@router.post("/reset-password")
async def reset_admin_password(new_password: str, db = get_db()):
    """Reset super admin password - TEMPORARY ENDPOINT"""
    # Hash the new password
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Update password
    await db.execute(text("""
        UPDATE employees
        SET password_hash = :ph
        WHERE is_super_admin = true
    """), {"ph": password_hash})
    
    return {"success": True, "message": "Password reset successfully"}
