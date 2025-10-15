from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text
from ..utils import is_admin

router = APIRouter(prefix="/admin/audit", tags=["admin"])

@router.get("/login")
async def admin_logins(user_id: int, request: Request):
    if not is_admin(user_id):
        raise HTTPException(403, "Not admin")
    rows = (await request.app.state.db.execute(text(
        "SELECT user_id, event, ip, ua, created_at FROM employee_logins ORDER BY created_at DESC LIMIT 200"
    ))).fetchall()
    return {"items": [dict(r._mapping) for r in rows]}
