"""
TEMPORARY DEV MODE: Disable TOTP for Founder account via API endpoint
"""

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/admin/temp-dev-mode")
async def temp_dev_mode(request: Request):
    """
    TEMPORARY: Disable TOTP for Founder and set known password
    This is for testing purposes only - will re-enable 2FA in Block 24B
    """
    db = request.app.state.db
    
    try:
        # Hash the password
        hashed_password = pwd_context.hash("SecureAdmin@2025")
        
        # Update the employee record
        update_query = text("""
            UPDATE employees 
            SET 
                totp_enabled = false,
                totp_secret = NULL,
                password_hash = :password_hash
            WHERE id = 1 
            AND username = 'EchofortSuperAdmin91'
            AND role = 'super_admin'
            RETURNING id, username, role, totp_enabled, is_super_admin
        """)
        
        result = await db.execute(update_query, {"password_hash": hashed_password})
        await db.commit()
        
        row = result.fetchone()
        
        if row:
            return {
                "success": True,
                "message": "TEMPORARY DEV MODE: TOTP disabled for Founder",
                "account": {
                    "id": row[0],
                    "username": row[1],
                    "role": row[2],
                    "totp_enabled": row[3],
                    "is_super_admin": row[4]
                },
                "warning": "This is TEMPORARY - will re-enable 2FA in Block 24B"
            }
        else:
            raise HTTPException(status_code=404, detail="Founder account not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
