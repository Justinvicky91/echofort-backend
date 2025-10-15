from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timedelta
from sqlalchemy import text
from ..deps import get_settings
from ..utils import jwt_encode

router = APIRouter(prefix="/auth/otp", tags=["auth"])

@router.post("/request")
async def request_otp(identity: str, request: Request, settings=Depends(get_settings)):
    db = request.app.state.db
    await db.execute(text(
        "INSERT INTO otps(identity, code, expires_at) VALUES (:i, :c, :e)"
    ), {"i": identity, "c": "123456", "e": datetime.utcnow() + timedelta(minutes=5)})
    return {"ok": True, "message": "OTP sent (mocked 123456)"}

@router.post("/verify")
async def verify_otp(payload: dict, request: Request, settings=Depends(get_settings)):
    identity = payload.get("identity")
    otp = payload.get("otp")
    device_id = payload.get("device_id")
    if otp != "123456":
        raise HTTPException(400, "Invalid OTP")
    db = request.app.state.db
    await db.execute(text("""        INSERT INTO users(identity, last_login, device_id, device_bound, trial_started_at)
        VALUES (:i, NOW(), :d, TRUE, NOW())
        ON CONFLICT (identity) DO UPDATE SET last_login=NOW(), device_id=:d, device_bound=TRUE
    """), {"i": identity, "d": device_id})
    token = jwt_encode({"sub": identity, "device_id": device_id, "iat": int(datetime.utcnow().timestamp())})
    return {"ok": True, "token": token}
