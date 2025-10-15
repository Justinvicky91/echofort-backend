from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(prefix="/marketing/push", tags=["admin"])

@router.post("/draft")
async def draft(request: Request, payload: dict):
    await request.app.state.db.execute(text(
      "INSERT INTO marketing_push(title, payload, status) VALUES (:t, :p, 'DRAFT')"
    ), {"t": payload.get("title","Untitled"), "p": payload})
    return {"ok": True}

@router.post("/approve/{mid}")
async def approve(mid: int, request: Request, user_id: int):
    await request.app.state.db.execute(text(
      "UPDATE marketing_push SET status='APPROVED', approver_id=:u, approved_at=NOW() WHERE id=:id"
    ), {"u": user_id, "id": mid})
    return {"ok": True}

@router.post("/send/{mid}")
async def send(mid: int, request: Request):
    await request.app.state.db.execute(text(
      "UPDATE marketing_push SET status='SENT', sent_at=NOW() WHERE id=:id"
    ), {"id": mid})
    return {"ok": True}
