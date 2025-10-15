from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(prefix="/user", tags=["privacy"])

@router.delete("/data")
async def delete_user_data(identity: str, request: Request):
    await request.app.state.db.execute(text("DELETE FROM ai_usage WHERE user_id IN (SELECT id FROM users WHERE identity=:i)"), {"i": identity})
    await request.app.state.db.execute(text("DELETE FROM users WHERE identity=:i"), {"i": identity})
    return {"ok": True, "message": "Data deleted as requested."}
