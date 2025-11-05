from fastapi import APIRouter, Request, HTTPException, Depends
import hmac, hashlib, json
from sqlalchemy import text
from ..deps import get_settings
from decimal import Decimal
from .invoice_generator import create_invoice

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
    event_type = event.get("event", "")
    
    # Log webhook
    await request.app.state.db.execute(text(
        "INSERT INTO webhook_logs(provider, event, ok) VALUES ('razorpay', :evt, TRUE)"
    ), {"evt": json.dumps(event)})
    
    # Generate invoice on payment success
    if event_type == "payment.captured":
        try:
            payment = event.get("payload", {}).get("payment", {}).get("entity", {})
            
            payment_id = payment.get("id")
            order_id = payment.get("order_id")
            amount = Decimal(payment.get("amount", 0)) / 100  # Convert paise to rupees
            customer_email = payment.get("email")
            customer_phone = payment.get("contact")
            
            # Get user details from notes or database
            notes = payment.get("notes", {})
            user_id = notes.get("user_id")
            plan_name = notes.get("plan_name", "Subscription")
            customer_name = notes.get("customer_name", "Customer")
            
            if user_id and customer_email:
                # Generate invoice
                invoice = await create_invoice(
                    request=request,
                    user_id=int(user_id),
                    plan_name=plan_name,
                    amount=amount,
                    transaction_id=payment_id,
                    razorpay_payment_id=payment_id,
                    razorpay_order_id=order_id,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone or ""
                )
                
                print(f"[SUCCESS] Invoice generated: {invoice['invoice_id']} for payment {payment_id}")
            else:
                print(f"[WARNING] Missing user_id or email in payment {payment_id}")
                
        except Exception as e:
            print(f"[ERROR] Failed to generate invoice: {e}")
            # Don't fail the webhook, just log the error
    
    return {"ok": True}
