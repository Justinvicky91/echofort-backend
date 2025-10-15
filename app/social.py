from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(prefix="/social", tags=["family"])

@router.post("/minutes/add")
async def add_minutes(request: Request, payload: dict):
    user_id = int(payload["user_id"])
    minutes = int(payload["minutes"])
    date = payload.get("date")
    q = text("""      INSERT INTO social_time(user_id,date,minutes)
      VALUES(:u, :d, :m)
      ON CONFLICT(user_id,date) DO UPDATE SET minutes = social_time.minutes + EXCLUDED.minutes
    """)
    await request.app.state.db.execute(q, {"u": user_id, "d": date, "m": minutes})
    return {"ok": True}

@router.get("/minutes/status")
async def status(request: Request, user_id: int, date: str, threshold: int = 120):
    row = (await request.app.state.db.execute(text(
        "SELECT minutes FROM social_time WHERE user_id=:u AND date=:d"
    ), {"u": user_id, "d": date})).first()
    minutes = int(row[0]) if row else 0
    alert = minutes > threshold
    return {"minutes": minutes, "threshold": threshold, "alert": alert}
