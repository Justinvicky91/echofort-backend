"""
Super Admin Initialization Endpoint
One-time use endpoint to create the Super Admin account
"""

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime
import os
from sqlalchemy import text

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# One-time initialization key (should match ADMIN_KEY in environment)
INIT_KEY = os.getenv("ADMIN_KEY", "")


class SuperAdminInit(BaseModel):
    username: str
    password: str
    email: str
    name: str


@router.post("/initialize-super-admin")
async def initialize_super_admin(
    request: Request,
    init_data: SuperAdminInit,
    authorization: str = Header(None)
):
    """
    One-time endpoint to create the Super Admin account.
    Requires ADMIN_KEY in Authorization header.
    
    Expected credentials:
    - Username: Echofort$Super$Admin
    - Password: Echo$9176$007$#
    - Email: EchofortAI@gmail.com
    - Name: Vigneshwaran J
    """
    
    # Verify authorization
    if not authorization or authorization != f"Bearer {INIT_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid ADMIN_KEY")
    
    try:
        db = request.app.state.db
        
        # Check if Super Admin already exists
        check_query = text("""
            SELECT id, username FROM employees 
            WHERE is_super_admin = true OR role = 'super_admin'
            LIMIT 1
        """)
        result = await db.execute(check_query)
        existing = result.fetchone()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="Super Admin already exists. Cannot create duplicate."
            )
        
        # Check if username already exists
        username_check = text("""
            SELECT id FROM employees WHERE username = :username LIMIT 1
        """)
        result = await db.execute(username_check, {"username": init_data.username})
        if result.fetchone():
            raise HTTPException(
                status_code=400, 
                detail="Username already exists"
            )
        
        # Hash the password
        hashed_password = pwd_context.hash(init_data.password)
        
        # Create Super Admin employee record
        insert_query = text("""
            INSERT INTO employees 
            (username, password_hash, role, department, is_super_admin, active, created_at, updated_at)
            VALUES (:username, :password_hash, 'super_admin', 'Administration', true, true, NOW(), NOW())
            RETURNING id, username, role, department, created_at
        """)
        
        result = await db.execute(insert_query, {
            "username": init_data.username,
            "password_hash": hashed_password
        })
        
        super_admin = result.fetchone()
        
        return {
            "success": True,
            "message": "Super Admin account created successfully",
            "super_admin": {
                "id": super_admin[0],
                "username": super_admin[1],
                "email": init_data.email,
                "name": init_data.name,
                "role": super_admin[2],
                "department": super_admin[3],
                "created_at": super_admin[4].isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Super Admin: {str(e)}")

