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
    
    # Generate invoice and activate subscription on payment success
    if event_type == "payment.captured":
        try:
            payment = event.get("payload", {}).get("payment", {}).get("entity", {})
            
            payment_id = payment.get("id")
            order_id = payment.get("order_id")
            amount_paise = payment.get("amount", 0)
            amount = Decimal(amount_paise) / 100  # Convert paise to rupees
            customer_email = payment.get("email")
            customer_phone = payment.get("contact")
            
            # Get user details from notes
            notes = payment.get("notes", {})
            user_id = notes.get("user_id")
            plan_id = notes.get("plan_id", "")
            customer_name = notes.get("customer_name", "Customer")
            
            # Determine plan_id from amount if not in notes
            if not plan_id:
                if amount_paise == 39900:
                    plan_id = "basic"
                elif amount_paise == 79900:
                    plan_id = "personal"
                elif amount_paise == 149900:
                    plan_id = "family"
                else:
                    plan_id = "unknown"
            
            # Determine dashboard_type from plan_id
            dashboard_type = None
            if plan_id == "basic":
                dashboard_type = "basic"
            elif plan_id == "personal":
                dashboard_type = "personal"
            elif plan_id == "family":
                dashboard_type = "family_admin"
            
            if user_id and customer_email:
                # Activate subscription in users table
                await request.app.state.db.execute(text("""
                    UPDATE users 
                    SET plan_id = :plan_id,
                        subscription_status = 'active',
                        dashboard_type = :dashboard_type,
                        updated_at = NOW()
                    WHERE id = :user_id
                """), {
                    "user_id": int(user_id),
                    "plan_id": plan_id,
                    "dashboard_type": dashboard_type
                })
                
                # Insert subscription record
                await request.app.state.db.execute(text("""
                    INSERT INTO subscriptions (user_id, plan, status, amount, razorpay_subscription_id, started_at)
                    VALUES (:user_id, :plan, 'active', :amount, :payment_id, NOW())
                    ON CONFLICT (user_id, plan) 
                    DO UPDATE SET 
                        status = 'active',
                        amount = EXCLUDED.amount,
                        razorpay_subscription_id = EXCLUDED.razorpay_subscription_id,
                        started_at = NOW(),
                        updated_at = NOW()
                """), {
                    "user_id": int(user_id),
                    "plan": plan_id,
                    "amount": amount,
                    "payment_id": payment_id
                })
                
                print(f"[SUBSCRIPTION] Subscription activated for user_id={user_id}, plan={plan_id}, dashboard_type={dashboard_type}")
                
                # Generate invoice
                invoice = await create_invoice(
                    request=request,
                    user_id=int(user_id),
                    plan_name=plan_id.capitalize(),
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
            print(f"[ERROR] Failed to process payment webhook: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail the webhook, just log the error
    
    return {"ok": True}
