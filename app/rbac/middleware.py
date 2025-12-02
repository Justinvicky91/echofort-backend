"""
RBAC Middleware for Backend Route Protection
Block 24 - Part A

Provides decorators and middleware to enforce role-based access control on backend routes.
"""

from fastapi import HTTPException, Request, Depends, Header
from functools import wraps
from typing import List, Callable, Optional
from .permissions import has_permission, is_admin_role, Permission
from ..utils import jwt_decode


# FastAPI Dependencies for route protection (Legacy + New)

# Legacy guard functions (from old rbac.py) - use X-Employee-Id and X-Role headers
async def require_role(role: str, employee_id: int | None, employee_role: str | None):
    """
    Legacy role checking function.
    """
    from ..utils import is_admin
    if employee_role == role or (role != "ADMIN" and employee_role == "ADMIN"):
        return True
    raise HTTPException(403, "Insufficient role")


async def guard_support(x_employee_id: int = Header(..., alias="X-Employee-Id"),
                        x_role: str = Header(..., alias="X-Role")):
    """
    Legacy guard function for SUPPORT role.
    """
    return await require_role("SUPPORT", x_employee_id, x_role)


async def guard_marketing(x_employee_id: int = Header(..., alias="X-Employee-Id"),
                          x_role: str = Header(..., alias="X-Role")):
    """
    Legacy guard function for MARKETING role.
    """
    return await require_role("MARKETING", x_employee_id, x_role)


async def guard_accounting(x_employee_id: int = Header(..., alias="X-Employee-Id"),
                           x_role: str = Header(..., alias="X-Role")):
    """
    Legacy guard function for ACCOUNTING role.
    """
    return await require_role("ACCOUNTING", x_employee_id, x_role)


async def guard_admin_legacy(x_employee_id: int = Header(..., alias="X-Employee-Id"),
                      x_role: str = Header(..., alias="X-Role")):
    """
    Legacy guard function for ADMIN role (uses X-Employee-Id and X-Role headers).
    """
    from ..utils import is_admin
    if x_role == "ADMIN" or is_admin(x_employee_id):
        return True
    raise HTTPException(403, "Admin only")


# New guard function (uses JWT token from Authorization header)
async def guard_admin(request: Request):
    """
    FastAPI dependency that ensures the current user is an admin or super admin.
    Raises 403 if the user is not authorized.
    
    Usage:
        @router.post("/chat", dependencies=[Depends(guard_admin)])
        async def chat_endpoint(request: Request):
            ...
    """
    role = get_current_user_role(request)
    if not role:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Authentication required"
        )
    
    if not is_admin_role(role):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Admin role required. Your role: {role}"
        )
    return role


def get_current_user_role(request: Request) -> Optional[str]:
    """
    Extract the current user's role from the JWT token.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Role string if authenticated, None otherwise
    """
    try:
        # Get Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.replace("Bearer ", "")
        
        # Decode JWT
        payload = jwt_decode(token)
        if not payload:
            return None
        
        # Extract role
        role = payload.get("role")
        return role
    except Exception as e:
        print(f"[RBAC] Error extracting role from token: {e}")
        return None


def require_permission(permission: str):
    """
    Decorator to require a specific permission for a route.
    
    Usage:
        @router.get("/admin/vault")
        @require_permission("secure_vault")
        async def get_vault_data(request: Request):
            ...
    
    Args:
        permission: Required permission string (e.g., "secure_vault")
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find Request object in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request and "request" in kwargs:
                request = kwargs["request"]
            
            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Internal error: Request object not found"
                )
            
            # Get user role
            role = get_current_user_role(request)
            if not role:
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Authentication required"
                )
            
            # BLOCK 24D: Hard bypass for super_admin
            # Super admins have access to ALL permissions, no exceptions
            if role == "super_admin":
                # Super admin bypass - always allow
                return await func(*args, **kwargs)
            
            # Check permission for non-super_admin users
            if not has_permission(role, permission):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Forbidden",
                        "message": f"Your role ({role}) does not have permission to access this resource.",
                        "required_permission": permission,
                        "your_role": role
                    }
                )
            
            # Permission granted, call the original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_role(allowed_roles: List[str]):
    """
    Decorator to require one of the specified roles for a route.
    
    Usage:
        @router.get("/admin/config")
        @require_role(["super_admin", "employee_engineering"])
        async def get_config(request: Request):
            ...
    
    Args:
        allowed_roles: List of allowed role strings
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find Request object in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request and "request" in kwargs:
                request = kwargs["request"]
            
            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Internal error: Request object not found"
                )
            
            # Get user role
            role = get_current_user_role(request)
            if not role:
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Authentication required"
                )
            
            # Check if role is in allowed list
            if role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Forbidden",
                        "message": f"Your role ({role}) is not authorized to access this resource.",
                        "allowed_roles": allowed_roles,
                        "your_role": role
                    }
                )
            
            # Role authorized, call the original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_admin():
    """
    Decorator to require any admin/employee role (not end-user).
    
    Usage:
        @router.get("/admin/dashboard")
        @require_admin()
        async def get_dashboard(request: Request):
            ...
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find Request object in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request and "request" in kwargs:
                request = kwargs["request"]
            
            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Internal error: Request object not found"
                )
            
            # Get user role
            role = get_current_user_role(request)
            if not role:
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Authentication required"
                )
            
            # Check if role is admin/employee
            if not is_admin_role(role):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Forbidden",
                        "message": "This area is restricted to admin and employee accounts only.",
                        "your_role": role
                    }
                )
            
            # Admin role confirmed, call the original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_super_admin():
    """
    Decorator to require super_admin role specifically.
    
    Usage:
        @router.post("/admin/system/reset")
        @require_super_admin()
        async def reset_system(request: Request):
            ...
    
    Returns:
        Decorator function
    """
    return require_role(["super_admin"])
