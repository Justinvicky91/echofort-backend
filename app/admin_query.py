"""
Temporary admin query endpoint for super admin setup
"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text

router = APIRouter(prefix="/admin/query", tags=["admin-query"])

@router.get("/super-admin")
async def get_super_admin(request: Request):
    """Get super admin details (username, email, name)"""
    db = request.app.state.db
    
    result = await db.execute(text("""
        SELECT id, username, email, name, phone, is_super_admin, created_at
        FROM employees
        WHERE is_super_admin = true
        LIMIT 1
    """))
    
    super_admin = result.fetchone()
    
    if not super_admin:
        return {"exists": False, "message": "No super admin found"}
    
    return {
        "exists": True,
        "id": super_admin[0],
        "username": super_admin[1],
        "email": super_admin[2],
        "name": super_admin[3],
        "phone": super_admin[4],
        "is_super_admin": super_admin[5],
        "created_at": str(super_admin[6])
    }

@router.put("/super-admin/update")
async def update_super_admin(payload: dict, request: Request):
    """Update super admin credentials"""
    db = request.app.state.db
    
    username = payload.get("username")
    password = payload.get("password")
    email = payload.get("email")
    name = payload.get("name")
    phone = payload.get("phone")
    
    if not all([username, password, email, name]):
        raise HTTPException(400, "All fields required")
    
    # Hash password
    import bcrypt
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    # Update super admin
    await db.execute(text("""
        UPDATE employees
        SET username = :username,
            password = :password,
            email = :email,
            name = :name,
            phone = :phone
        WHERE is_super_admin = true
    """), {
        "username": username,
        "password": hashed_password,
        "email": email,
        "name": name,
        "phone": phone
    })
    
    await db.commit()
    
    return {"success": True, "message": "Super admin updated successfully"}
