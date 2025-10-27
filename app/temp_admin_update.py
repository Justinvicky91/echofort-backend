"""
Temporary endpoint to update super admin credentials
DELETE THIS FILE AFTER USE FOR SECURITY!
"""
from fastapi import APIRouter, HTTPException
import bcrypt
from app.database import get_db_connection

router = APIRouter(prefix="/temp-admin", tags=["Temporary Admin"])

@router.post("/update-super-admin-NOW")
async def update_super_admin_credentials():
    """
    TEMPORARY ENDPOINT - DELETE AFTER USE!
    Updates the super admin credentials to the new values
    """
    try:
        conn = await get_db_connection()
        
        # Check existing super admin
        existing = await conn.fetchrow("""
            SELECT id, user_id, username FROM employees WHERE is_super_admin = true
        """)
        
        if not existing:
            raise HTTPException(status_code=404, detail="No super admin found")
        
        # New credentials
        new_username = "EchofortSuperAdmin91"
        new_password = "Echo$9176$007$#"
        new_email = "EchofortAI@gmail.com"
        new_name = "Vigneshwaran J"
        new_phone = "+919361440568"
        
        # Hash password
        hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        
        # Update user record
        await conn.execute("""
            UPDATE users
            SET email = $1, name = $2
            WHERE id = $3
        """, new_email, new_name, existing['user_id'])
        
        # Update employee record
        await conn.execute("""
            UPDATE employees
            SET username = $1,
                password_hash = $2,
                phone = $3
            WHERE is_super_admin = true
        """, new_username, hashed_password, new_phone)
        
        await conn.close()
        
        return {
            "success": True,
            "message": "Super admin updated successfully!",
            "old_username": existing['username'],
            "new_username": new_username,
            "new_email": new_email,
            "new_name": new_name,
            "new_phone": new_phone
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

