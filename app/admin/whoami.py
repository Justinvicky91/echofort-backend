"""
WHO AM I Endpoint

Provides current user's role and permissions for debugging.
"""

from fastapi import APIRouter, Request, HTTPException
from ..utils import jwt_decode

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/whoami")
async def whoami(request: Request):
    """
    Returns current user's identity, role, and permissions.
    Useful for debugging RBAC issues.
    """
    # Get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        # Decode JWT token
        payload = jwt_decode(token)
        
        # Get user details from token
        employee_id = payload.get("employee_id")
        user_type = payload.get("user_type")
        role = payload.get("role")
        
        # Get user from database
        db = request.app.state.db
        from sqlalchemy import text
        user_row = await db.execute(
            text("SELECT id, username, role, is_super_admin, department FROM employees WHERE id = :employee_id"),
            {"employee_id": int(employee_id)}
        )
        user_row = user_row.first()
        
        if not user_row:
            raise HTTPException(404, "User not found in database")
        
        # Get permissions for this role
        from ..rbac import get_permissions, get_sidebar_items_for_role
        
        permissions = get_permissions(role)
        sidebar_items = get_sidebar_items_for_role(role)
        
        return {
            "success": True,
            "user": {
                "id": user_row["id"],
                "username": user_row["username"],
                "role": user_row["role"],
                "is_super_admin": user_row["is_super_admin"],
                "department": user_row["department"],
            },
            "token_payload": {
                "employee_id": employee_id,
                "user_type": user_type,
                "role": role,
            },
            "rbac": {
                "permissions": permissions,
                "sidebar_items": sidebar_items,
            },
            "has_command_center_permission": "command_center" in permissions,
            "is_super_admin_role": role == "super_admin",
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error decoding token or fetching user: {str(e)}")
