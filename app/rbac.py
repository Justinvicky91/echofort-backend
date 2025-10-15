from fastapi import Header, HTTPException
from .utils import is_admin

async def require_role(role: str, employee_id: int | None, employee_role: str | None):
    if employee_role == role or (role != "ADMIN" and employee_role == "ADMIN"):
        return True
    raise HTTPException(403, "Insufficient role")

async def guard_support(x_employee_id: int = Header(..., alias="X-Employee-Id"),
                        x_role: str = Header(..., alias="X-Role")):
    return await require_role("SUPPORT", x_employee_id, x_role)

async def guard_marketing(x_employee_id: int = Header(..., alias="X-Employee-Id"),
                          x_role: str = Header(..., alias="X-Role")):
    return await require_role("MARKETING", x_employee_id, x_role)

async def guard_accounting(x_employee_id: int = Header(..., alias="X-Employee-Id"),
                           x_role: str = Header(..., alias="X-Role")):
    return await require_role("ACCOUNTING", x_employee_id, x_role)

async def guard_admin(x_employee_id: int = Header(..., alias="X-Employee-Id"),
                      x_role: str = Header(..., alias="X-Role")):
    if x_role == "ADMIN" or is_admin(x_employee_id):
        return True
    raise HTTPException(403, "Admin only")
