from fastapi import APIRouter, Request
import json
from sqlalchemy import text

router = APIRouter(prefix="/webhooks", tags=["billing"])

@router.post("/stripe")
async def stripe_hook(request: Request):
    event = json.loads((await request.body()).decode() or "{}")
    await request.app.state.db.execute(text(
        "INSERT INTO webhook_logs(provider, event, ok) VALUES ('stripe', :evt, TRUE)"
    ), {"evt": json.dumps(event)})
    return {"ok": True}
