from fastapi import HTTPException, Request
from sqlalchemy import text
from ..utils import ai_cost_ok
from ..deps import get_settings

async def ensure_ai_budget(request: Request, estimated_rs: float = 0.25):
    s = get_settings()
    if not s.AI_ENABLED:
        raise HTTPException(503, "AI temporarily disabled")
    db = request.app.state.db
    row = (await db.execute(text("""        SELECT COALESCE(SUM(cost_rs),0) FROM ai_usage
        WHERE date_trunc('month', created_at) = date_trunc('month', NOW())
    """))).first()
    month_sum = float(row[0] or 0)
    if not ai_cost_ok(month_sum, estimated_rs):
        raise HTTPException(402, "AI cost cap reached")
    return True

async def record_ai_cost(request: Request, endpoint: str, cost_rs: float, meta: dict | None = None, user_id: int | None = None):
    db = request.app.state.db
    await db.execute(text("""        INSERT INTO ai_usage(user_id, endpoint, cost_rs, meta) VALUES (:u,:e,:c,:m)
    """), {"u": user_id, "e": endpoint, "c": cost_rs, "m": meta or {}})
