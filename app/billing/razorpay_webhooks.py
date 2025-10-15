from fastapi import APIRouter, Request, HTTPException, Depends
import hmac, hashlib, json
from sqlalchemy import text
from ..deps import get_settings

router = APIRouter(prefix="/webhooks", tags=["billing"])

def verify_sig(body_bytes: bytes, sig_header: str, secret: str) -> bool:
    digest = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, sig_header or "")

@router.post("/razorpay")
async def razorpay_hook(request: Request, settings=Depends(get_settings)):
    body = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")
    if settings.RAZORPAY_WEBHOOK_SECRET and not verify_sig(body, sig, settings.RAZORPAY_WEBHOOK_SECRET):
        raise HTTPException(400, "Bad signature")
    event = json.loads(body.decode() or "{}")
    await request.app.state.db.execute(text(
        "INSERT INTO webhook_logs(provider, event, ok) VALUES ('razorpay', :evt, TRUE)"
    ), {"evt": json.dumps(event)})
    return {"ok": True}
