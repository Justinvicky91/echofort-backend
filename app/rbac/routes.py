"""
RBAC API Routes
Block 24 - Part A

Provides endpoints for the frontend to query user permissions and sidebar items.
"""

from fastapi import APIRouter, Request, HTTPException
from .middleware import get_current_user_role
from .permissions import (
    get_permissions,
    get_sidebar_items_for_role,
    has_permission,
    is_admin_role,
    ROLE_PERMISSIONS,
)

router = APIRouter(prefix="/rbac", tags=["rbac"])


@router.get("/me/permissions")
async def get_my_permissions(request: Request):
    """
    Get the current user's permissions and sidebar items.
    
    Returns:
        {
            "role": "super_admin",
            "permissions": ["command_center", "secure_vault", ...],
            "sidebar_items": ["Command Center", "Secure Vault", ...],
            "is_admin": true
        }
    """
    role = get_current_user_role(request)
    if not role:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Authentication required"
        )
    
    return {
        "role": role,
        "permissions": get_permissions(role),
        "sidebar_items": get_sidebar_items_for_role(role),
        "is_admin": is_admin_role(role)
    }


@router.get("/permissions/check")
async def check_permission(request: Request, permission: str):
    """
    Check if the current user has a specific permission.
    
    Query params:
        permission: Permission to check (e.g., "secure_vault")
    
    Returns:
        {
            "role": "admin",
            "permission": "secure_vault",
            "has_permission": false
        }
    """
    role = get_current_user_role(request)
    if not role:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Authentication required"
        )
    
    return {
        "role": role,
        "permission": permission,
        "has_permission": has_permission(role, permission)
    }


@router.get("/roles/matrix")
async def get_roles_matrix(request: Request):
    """
    Get the complete roles and permissions matrix.
    Only accessible to super_admin.
    
    Returns:
        {
            "super_admin": ["command_center", "secure_vault", ...],
            "admin": ["command_center", "customer_hub", ...],
            ...
        }
    """
    role = get_current_user_role(request)
    if not role:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Authentication required"
        )
    
    if role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only super_admin can view the complete permissions matrix"
        )
    
    # Convert enum-based matrix to string-based for JSON response
    matrix = {}
    for role_enum, permissions_set in ROLE_PERMISSIONS.items():
        matrix[role_enum.value] = [p.value for p in permissions_set]
    
    return matrix
