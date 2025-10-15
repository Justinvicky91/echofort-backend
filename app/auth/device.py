from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlalchemy import text
from datetime import datetime
from ..deps import get_settings
from ..utils import trial_fingerprint

router = APIRouter(prefix="/trial", tags=["trial"])

@router.get("/status")
async def trial_status(user_id: int, request: Request, settings=Depends(get_settings)):
    db = request.app.state.db
    row = (await db.execute(text("SELECT trial_started_at FROM users WHERE id=:uid"), {"uid": user_id})).first()
    if not row or not row[0]:
        raise HTTPException(404, "User not found or trial not started")
    elapsed = datetime.utcnow() - row[0]
    remaining = max(0, (settings.TRIAL_HOURS*3600 - int(elapsed.total_seconds())))
    return {"trial_hours": settings.TRIAL_HOURS, "remaining_seconds": remaining}

@router.post("/check")
async def trial_check(payload: dict = Body(...), request: Request = None):
    fp = trial_fingerprint(
        payload.get("device_id",""),
        payload.get("identity",""),
        payload.get("payment_last4",""),
        payload.get("ip_block","")
    )
    db = request.app.state.db
    row = (await db.execute(text("SELECT 1 FROM users WHERE trial_fingerprint=:f LIMIT 1"), {"f": fp})).first()
    if row:
        return {"ok": False, "error": "TRIAL_ALREADY_USED"}
    await db.execute(text("UPDATE users SET trial_fingerprint=:f WHERE identity=:i"), {"f": fp, "i": payload.get("identity")})
    return {"ok": True, "fingerprint": fp}
