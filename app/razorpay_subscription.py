"""
Razorpay Subscription & Payment Integration
Handles subscription creation, payment verification, and billing
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional
import razorpay
import hmac
import hashlib
import os
from .utils import get_current_user
from .deps import get_settings
from .invoice_generator import generate_invoice_html, convert_html_to_pdf
from .email_service import email_service

router = APIRouter(prefix="/api/razorpay", tags=["Razorpay Payment"])

# Razorpay client initialization
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None
    print("⚠️ Razorpay credentials not configured")

# Pricing plans
# NOTE: Razorpay API requires amounts in paise (₹1 = 100 paise)
# Display prices are in rupees, but sent to Razorpay in paise
PRICING_PLANS = {
    "basic": {
        "name": "Basic Plan",
        "amount": 39900,  # ₹399
        "currency": "INR",
        "duration_days": 30
    },
    "personal": {
        "name": "Personal Plan",
        "amount": 79900,  # ₹799
        "currency": "INR",
        "duration_days": 30
    },
    "family": {
        "name": "Family Plan",
        "amount": 149900,  # ₹1,499
        "currency": "INR",
        "duration_days": 30
    }
}

TRIAL_AMOUNT = 100  # ₹1 in paise
RAZORPAY_MODE = os.getenv("RAZORPAY_MODE", "test")  # test or live


class CreateOrderRequest(BaseModel):
    plan: str  # basic, personal, family
    is_trial: bool = True  # First payment is ₹1 trial


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan: str
    is_trial: bool = True


@router.post("/create-order")
async def create_razorpay_order(
    payload: CreateOrderRequest,
    request: Request,
    user = Depends(get_current_user)
):
    """
    Create Razorpay order for subscription payment
    First payment is ₹1 trial, then full amount after 24 hours
    """
    if not razorpay_client:
        raise HTTPException(500, "Razorpay not configured")
    
    if payload.plan not in PRICING_PLANS:
        raise HTTPException(400, f"Invalid plan. Choose from: {list(PRICING_PLANS.keys())}")
    
    plan_info = PRICING_PLANS[payload.plan]
    
    # Determine amount (₹1 for trial, full amount for subscription)
    amount = TRIAL_AMOUNT if payload.is_trial else plan_info["amount"]
    
    try:
        # Create Razorpay order
        order_data = {
            "amount": amount,
            "currency": plan_info["currency"],
            "receipt": f"rcpt_{user['user_id']}_{int(datetime.utcnow().timestamp())}",
            "notes": {
                "user_id": user["user_id"],
                "plan": payload.plan,
                "is_trial": str(payload.is_trial),
                "email": user.get("email", ""),
                "username": user.get("username", "")
            }
        }
        
        order = razorpay_client.order.create(data=order_data)
        
        # Store order in database
        db = request.app.state.db
        await db.execute(text("""
            INSERT INTO razorpay_orders 
            (order_id, user_id, plan, amount, currency, status, is_trial, created_at)
            VALUES (:order_id, :user_id, :plan, :amount, :currency, 'created', :is_trial, NOW())
        """), {
            "order_id": order["id"],
            "user_id": user["user_id"],
            "plan": payload.plan,
            "amount": amount / 100,  # Convert paise to rupees
            "currency": plan_info["currency"],
            "is_trial": payload.is_trial
        })
        
        return {
            "ok": True,
            "order_id": order["id"],
            "amount": amount,
            "currency": plan_info["currency"],
            "key_id": RAZORPAY_KEY_ID,
            "plan": payload.plan,
            "plan_name": plan_info["name"],
            "is_trial": payload.is_trial
        }
        
    except Exception as e:
        print(f"❌ Razorpay order creation failed: {str(e)}")
        raise HTTPException(500, f"Failed to create order: {str(e)}")


@router.post("/verify-payment")
async def verify_razorpay_payment(
    payload: VerifyPaymentRequest,
    request: Request,
    user = Depends(get_current_user)
):
    """
    Verify Razorpay payment signature and activate subscription
    """
    if not razorpay_client:
        raise HTTPException(500, "Razorpay not configured")
    
    try:
        # Verify signature
        generated_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature != payload.razorpay_signature:
            raise HTTPException(400, "Invalid payment signature")
        
        # Fetch payment details from Razorpay
        payment = razorpay_client.payment.fetch(payload.razorpay_payment_id)
        
        if payment["status"] != "captured":
            raise HTTPException(400, "Payment not captured")
        
        db = request.app.state.db
        
        # Update order status
        await db.execute(text("""
            UPDATE razorpay_orders
            SET status = 'paid', payment_id = :payment_id, updated_at = NOW()
            WHERE order_id = :order_id AND user_id = :user_id
        """), {
            "payment_id": payload.razorpay_payment_id,
            "order_id": payload.razorpay_order_id,
            "user_id": user["user_id"]
        })
        
        # If trial payment, just mark trial as started
        if payload.is_trial:
            await db.execute(text("""
                UPDATE users
                SET 
                    trial_started_at = NOW(),
                    subscription_plan = :plan,
                    subscription_status = 'trial',
                    razorpay_payment_id = :payment_id
                WHERE user_id = :user_id
            """), {
                "plan": payload.plan,
                "payment_id": payload.razorpay_payment_id,
                "user_id": user["user_id"]
            })
            
            return {
                "ok": True,
                "message": "Trial activated! You have 24 hours free access.",
                "trial_active": True,
                "plan": payload.plan,
                "next_payment_date": (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }
        
        # Full subscription payment
        plan_info = PRICING_PLANS[payload.plan]
        subscription_end = datetime.utcnow() + timedelta(days=plan_info["duration_days"])
        
        await db.execute(text("""
            UPDATE users
            SET 
                subscription_plan = :plan,
                subscription_status = 'active',
                subscription_start_date = NOW(),
                subscription_end_date = :end_date,
                razorpay_payment_id = :payment_id,
                trial_ended_at = NOW()
            WHERE user_id = :user_id
        """), {
            "plan": payload.plan,
            "end_date": subscription_end,
            "payment_id": payload.razorpay_payment_id,
            "user_id": user["user_id"]
        })
        
        # Generate invoice (async task)
        try:
            from .billing import invoice_generator
            await invoice_generator.generate_invoice(
                user_id=user["user_id"],
                plan=payload.plan,
                amount=payment["amount"] / 100,
                payment_id=payload.razorpay_payment_id,
                order_id=payload.razorpay_order_id
            )
        except Exception as e:
            print(f"⚠️ Invoice generation failed: {str(e)}")
        
        return {
            "ok": True,
            "message": f"Subscription activated! {plan_info['name']} is now active.",
            "subscription_active": True,
            "plan": payload.plan,
            "plan_name": plan_info["name"],
            "end_date": subscription_end.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Payment verification failed: {str(e)}")
        raise HTTPException(500, f"Payment verification failed: {str(e)}")


@router.post("/cancel-subscription")
async def cancel_subscription(
    request: Request,
    user = Depends(get_current_user)
):
    """
    Cancel active subscription and process refund if within 24 hours
    """
    db = request.app.state.db
    
    # Get user subscription details
    row = (await db.execute(text("""
        SELECT 
            subscription_plan,
            subscription_status,
            subscription_start_date,
            razorpay_payment_id
        FROM users
        WHERE user_id = :uid
    """), {"uid": user["user_id"]})).fetchone()
    
    if not row or row.subscription_status != "active":
        raise HTTPException(400, "No active subscription to cancel")
    
    # Check if within 24-hour refund window
    hours_since_start = (datetime.utcnow() - row.subscription_start_date).total_seconds() / 3600
    eligible_for_refund = hours_since_start <= 24
    
    # Update subscription status
    await db.execute(text("""
        UPDATE users
        SET subscription_status = 'cancelled', subscription_end_date = NOW()
        WHERE user_id = :uid
    """), {"uid": user["user_id"]})
    
    refund_initiated = False
    
    # Process refund if eligible
    if eligible_for_refund and row.razorpay_payment_id and razorpay_client:
        try:
            payment = razorpay_client.payment.fetch(row.razorpay_payment_id)
            refund = razorpay_client.payment.refund(row.razorpay_payment_id, {
                "amount": payment["amount"],
                "speed": "normal",
                "notes": {
                    "reason": "24-hour cancellation policy",
                    "user_id": user["user_id"]
                }
            })
            
            # Record refund
            await db.execute(text("""
                INSERT INTO refunds 
                (user_id, payment_id, refund_id, amount, status, reason, created_at)
                VALUES (:uid, :pay_id, :ref_id, :amount, 'processing', '24-hour cancellation', NOW())
            """), {
                "uid": user["user_id"],
                "pay_id": row.razorpay_payment_id,
                "ref_id": refund["id"],
                "amount": payment["amount"] / 100
            })
            
            refund_initiated = True
            
        except Exception as e:
            print(f"⚠️ Refund failed: {str(e)}")
    
    return {
        "ok": True,
        "message": "Subscription cancelled successfully",
        "refund_eligible": eligible_for_refund,
        "refund_initiated": refund_initiated,
        "refund_message": "Refund will be processed within 5-7 business days" if refund_initiated else None
    }


@router.get("/subscription-status")
async def get_subscription_status(
    request: Request,
    user = Depends(get_current_user)
):
    """Get detailed subscription status"""
    db = request.app.state.db
    
    row = (await db.execute(text("""
        SELECT 
            subscription_plan,
            subscription_status,
            subscription_start_date,
            subscription_end_date,
            trial_started_at,
            trial_ended_at,
            razorpay_payment_id
        FROM users
        WHERE user_id = :uid
    """), {"uid": user["user_id"]})).fetchone()
    
    if not row:
        raise HTTPException(404, "User not found")
    
    # Check trial status
    trial_active = False
    trial_hours_remaining = 0
    if row.trial_started_at and not row.trial_ended_at:
        trial_end = row.trial_started_at + timedelta(hours=24)
        trial_active = datetime.utcnow() < trial_end
        if trial_active:
            trial_hours_remaining = (trial_end - datetime.utcnow()).total_seconds() / 3600
    
    # Check subscription status
    subscription_active = (
        row.subscription_status == "active" and 
        row.subscription_end_date and 
        datetime.utcnow() < row.subscription_end_date
    )
    
    days_remaining = 0
    if subscription_active:
        days_remaining = (row.subscription_end_date - datetime.utcnow()).days
    
    return {
        "plan": row.subscription_plan or "none",
        "status": row.subscription_status or "inactive",
        "trial_active": trial_active,
        "trial_hours_remaining": round(trial_hours_remaining, 1),
        "subscription_active": subscription_active,
        "days_remaining": days_remaining,
        "start_date": row.subscription_start_date.isoformat() if row.subscription_start_date else None,
        "end_date": row.subscription_end_date.isoformat() if row.subscription_end_date else None,
        "payment_id": row.razorpay_payment_id
    }


@router.get("/plans")
async def get_razorpay_plans():
    """
    Get Razorpay pricing plans (INR for Indian users)
    Returns prices in rupees for display
    """
    return {
        "ok": True,
        "plans": {
            "basic": {
                "name": "Basic Plan",
                "price": 399,  # Display price in rupees
                "currency": "INR",
                "duration_days": 30,
                "features": ["AI Call Screening", "Trust Factor", "Scam Database Access"]
            },
            "personal": {
                "name": "Personal Plan",
                "price": 799,  # Display price in rupees
                "currency": "INR",
                "duration_days": 30,
                "features": ["Everything in Basic", "Call Recording", "Image Scanning", "WhatsApp Protection"]
            },
            "family": {
                "name": "Family Plan",
                "price": 1499,  # Display price in rupees
                "currency": "INR",
                "duration_days": 30,
                "features": ["Everything in Personal", "GPS Tracking", "Child Protection", "4 Devices"]
            }
        },
        "currency": "INR",
        "note": "Prices in Indian Rupees (₹)",
        "trial_period": "₹1 for 24 hours, then full price"
    }


@router.post("/test-live")
async def test_razorpay_live_connection():
    """
    Test Razorpay LIVE connection by creating a ₹1 test order
    BLOCK PAY-RAZOR-LIVE Section 2B
    """
    if not razorpay_client:
        return {
            "ok": False,
            "error_code": "missing_keys",
            "error_message": "Razorpay credentials not configured in environment variables"
        }
    
    try:
        # Create a ₹1 test order to verify LIVE connection
        test_order = razorpay_client.order.create({
            "amount": 100,  # ₹1 in paise
            "currency": "INR",
            "receipt": f"test_live_{int(datetime.utcnow().timestamp())}",
            "notes": {
                "purpose": "LIVE connection test",
                "mode": RAZORPAY_MODE
            }
        })
        
        # If order creation succeeded, connection is working
        return {
            "ok": True,
            "mode": RAZORPAY_MODE,
            "test_order_id": test_order["id"],
            "message": f"Razorpay {RAZORPAY_MODE.upper()} connection successful"
        }
        
    except Exception as e:
        error_message = str(e)
        return {
            "ok": False,
            "error_code": "RAZORPAY_API_ERROR",
            "error_message": error_message,
            "mode": RAZORPAY_MODE
        }


class CreateOrderLiveRequest(BaseModel):
    plan_id: str = "internal-test"
    amount: Optional[int] = None  # Will be calculated based on is_internal_test
    is_internal_test: bool = False  # True for ₹1 tests, False for real plan prices
    currency: str = "INR"
    purpose: str = "live-test"
    customer_id: str = "superadmin-live-test"


@router.post("/create-order-live")
async def create_razorpay_order_live(payload: CreateOrderLiveRequest):
    """
    Create Razorpay LIVE order for testing
    BLOCK PAY-RAZOR-LIVE Section 2C
    """
    if not razorpay_client:
        return {
            "ok": False,
            "error_code": "missing_keys",
            "error_message": "Razorpay credentials not configured"
        }
    
    try:
        # Determine amount based on is_internal_test flag
        if payload.is_internal_test:
            # Internal test: ₹1 (100 paise)
            amount = 100
            notes_mode = "internal_test"
        else:
            # Real customer: Use full plan amount
            # If amount is provided, use it; otherwise calculate from plan_id
            if payload.amount:
                amount = payload.amount
            else:
                # Default plan prices (can be extended with actual plan lookup)
                plan_prices = {
                    "basic": 39900,      # ₹399
                    "personal": 79900,   # ₹799
                    "family": 149900,    # ₹1499
                }
                amount = plan_prices.get(payload.plan_id, 100)
            notes_mode = "real_customer"
        
        order_data = {
            "amount": amount,
            "currency": payload.currency,
            "receipt": f"live_{'test' if payload.is_internal_test else 'order'}_{int(datetime.utcnow().timestamp())}",
            "notes": {
                "purpose": payload.purpose,
                "customer_id": payload.customer_id,
                "mode": notes_mode,
                "plan_id": payload.plan_id,
                "is_internal_test": str(payload.is_internal_test)
            }
        }
        
        order = razorpay_client.order.create(order_data)
        
        return {
            "ok": True,
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": RAZORPAY_KEY_ID,
            "mode": RAZORPAY_MODE
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error_code": "ORDER_CREATION_FAILED",
            "error_message": str(e)
        }


@router.post("/webhook-live")
async def razorpay_webhook_live(request: Request):
    """
    Handle Razorpay LIVE webhooks
    BLOCK S1 - Complete subscription flow
    """
    db = request.app.state.db
    
    try:
        # Get raw body for signature verification
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8')
        
        # Parse JSON payload
        import json
        payload = json.loads(body_str)
        
        # Log webhook received
        print(f"📥 Webhook received: {payload.get('event', 'unknown')}")
        
        # Validate webhook signature using Razorpay's official utility
        webhook_signature = request.headers.get("X-Razorpay-Signature", "")
        webhook_secret = RAZORPAY_WEBHOOK_SECRET
        
        if not webhook_secret:
            print("⚠️ Webhook secret not configured - skipping signature verification")
        else:
            try:
                # Use Razorpay's official verification utility
                razorpay_client.utility.verify_webhook_signature(
                    body_str,  # Raw request body as string
                    webhook_signature,
                    webhook_secret
                )
                print("✅ Webhook signature verified")
            except razorpay.errors.SignatureVerificationError as e:
                print(f"❌ Invalid webhook signature")
                print(f"   Error: {str(e)}")
                print(f"   Secret length: {len(webhook_secret) if webhook_secret else 0}")
                print(f"   Body length: {len(body_str)}")
                raise HTTPException(400, "Invalid webhook signature")
            except Exception as e:
                print(f"❌ Signature verification error: {str(e)}")
                import traceback
                traceback.print_exc()
                raise HTTPException(500, f"Signature verification failed: {str(e)}")
        
        # Handle payment.captured event
        event_type = payload.get("event")
        print(f"🔍 Event type check: '{event_type}' == 'payment.captured' ? {event_type == 'payment.captured'}")
        
        if event_type == "payment.captured":
            print("💰 Processing payment.captured event", flush=True)
            
            # Extract payment details
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            
            if not payment_entity:
                print("⚠️ No payment entity in webhook payload")
                return {"ok": True, "message": "No payment entity"}
            
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")
            amount = payment_entity.get("amount", 0)  # in paise
            currency = payment_entity.get("currency", "INR")
            email = payment_entity.get("email", "")
            notes = payment_entity.get("notes", {})
            
            # BLOCK S2: Extract user_id and plan_id from notes
            user_id_from_notes = notes.get("user_id")
            plan_id_from_notes = notes.get("plan_id")
            
            print(f"   Order ID: {order_id}", flush=True)
            print(f"   Payment ID: {payment_id}", flush=True)
            print(f"   Amount: ₹{amount/100}", flush=True)
            print(f"   Email: {email}", flush=True)
            print(f"   Notes user_id: {user_id_from_notes}", flush=True)
            print(f"   Notes plan_id: {plan_id_from_notes}", flush=True)
            
            # Determine if internal test (₹1 = 100 paise)
            is_internal_test = (amount == 100)
            print(f"   Internal Test: {is_internal_test}", flush=True)
            
            # Determine plan - Priority 1: notes.plan_id, Priority 2: amount
            if plan_id_from_notes:
                plan_name = plan_id_from_notes
                print(f"   Plan Name (from notes): {plan_name}", flush=True)
            elif amount == 39900:  # ₹399
                plan_name = "basic"
                print(f"   Plan Name (from amount): {plan_name}", flush=True)
            elif amount == 79900:  # ₹799
                plan_name = "personal"
                print(f"   Plan Name (from amount): {plan_name}", flush=True)
            elif amount == 149900:  # ₹1499
                plan_name = "family"
                print(f"   Plan Name (from amount): {plan_name}", flush=True)
            else:
                plan_name = "test"  # For internal tests or unknown amounts
                print(f"   Plan Name (fallback): {plan_name}", flush=True)
            
            # Generate unique invoice number
            now = datetime.utcnow()
            month_prefix = now.strftime("%Y%m")
            
            count_result = (await db.execute(text("""
                SELECT COUNT(*) as count 
                FROM invoices 
                WHERE invoice_number LIKE :prefix
            """), {"prefix": f"INV-{month_prefix}-%"})).fetchone()
            
            count = (count_result[0] if count_result else 0) + 1
            invoice_number = f"INV-{month_prefix}-{count:05d}"
            
            print(f"   Invoice Number: {invoice_number}", flush=True)
            
            # Generate invoice HTML
            html_content = generate_invoice_html(
                invoice_number=invoice_number,
                order_id=order_id,
                payment_id=payment_id,
                amount=amount,
                currency=currency,
                is_internal_test=is_internal_test,
                created_at=now,
                user_email=email if email else None,
                user_name=None
            )
            
            # Generate PDF
            pdf_dir = "/tmp/invoices"
            os.makedirs(pdf_dir, exist_ok=True)
            pdf_path = f"{pdf_dir}/{invoice_number}.pdf"
            pdf_generated = await convert_html_to_pdf(html_content, pdf_path)
            pdf_url = f"/invoices/{invoice_number}.pdf" if pdf_generated else None
            
            print(f"   PDF Generated: {pdf_generated}", flush=True)
            
            # BLOCK S2: Find user by notes.user_id first, then fallback to email
            user_id = 1  # Default to SuperAdmin
            
            # Priority 1: Use user_id from notes (BLOCK S2 flow)
            if user_id_from_notes:
                try:
                    user_id = int(user_id_from_notes)
                    print(f"   Using user_id from notes: {user_id}", flush=True)
                except (ValueError, TypeError):
                    print(f"   Invalid user_id in notes: {user_id_from_notes}", flush=True)
            
            # Priority 2: Fallback to email lookup
            elif email:
                try:
                    user_result = (await db.execute(text("""
                        SELECT id FROM users WHERE email = :email LIMIT 1
                    """), {"email": email})).fetchone()
                    
                    if user_result:
                        user_id = user_result[0]
                        print(f"   Found user_id: {user_id} for email: {email}", flush=True)
                    else:
                        print(f"   No user found for email: {email}, using SuperAdmin", flush=True)
                except Exception as e:
                    print(f"   Error looking up user: {str(e)}", flush=True)
            
            print("📝 Invoice creation started...", flush=True)
            
            # Insert invoice
            await db.execute(text("""
                INSERT INTO invoices 
                (invoice_id, user_id, razorpay_order_id, razorpay_payment_id, invoice_number, plan_name,
                 amount, currency, is_internal_test, status, invoice_html, file_path, created_at, updated_at)
                VALUES (:invoice_id, :user_id, :order_id, :payment_id, :invoice_number, :plan_name,
                        :amount, :currency, :is_internal_test, 'paid', :html_content, :file_path, NOW(), NOW())
            """), {
                "invoice_id": invoice_number,  # Use invoice_number as invoice_id
                "user_id": user_id,
                "order_id": order_id,
                "payment_id": payment_id,
                "invoice_number": invoice_number,
                "plan_name": plan_name,
                "amount": amount,
                "currency": currency,
                "is_internal_test": is_internal_test,
                "html_content": html_content,
                "file_path": pdf_url
            })
            
            print(f"✅ Invoice created: {invoice_number}", flush=True)
            print("📝 Invoice creation finished", flush=True)
            
            # Activate subscription (only for real payments)
            if not is_internal_test:
                print("🔄 Activating subscription...")
                
                plan_name = "unknown"
                plan_duration_days = 30
                
                if amount == 39900:
                    plan_name = "basic"
                elif amount == 79900:
                    plan_name = "personal"
                elif amount == 149900:
                    plan_name = "family"
                
                start_date = now
                end_date = now + timedelta(days=plan_duration_days)
                
                try:
                    # Create subscriptions table if not exists
                    await db.execute(text("""
                        CREATE TABLE IF NOT EXISTS subscriptions (
                            id BIGINT AUTO_INCREMENT PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            plan_id VARCHAR(50) NOT NULL,
                            status VARCHAR(50) DEFAULT 'active',
                            start_at TIMESTAMP NULL,
                            end_at TIMESTAMP NULL,
                            is_trial BOOLEAN DEFAULT FALSE,
                            razorpay_order_id VARCHAR(255) NULL,
                            razorpay_payment_id VARCHAR(255) NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            INDEX idx_user_id (user_id),
                            INDEX idx_status (status)
                        )
                    """))
                    
                    # Insert subscription
                    await db.execute(text("""
                        INSERT INTO subscriptions 
                        (user_id, plan_id, status, start_at, end_at, is_trial, 
                         razorpay_order_id, razorpay_payment_id, created_at, updated_at)
                        VALUES (:user_id, :plan_id, 'active', :start_at, :end_at, FALSE,
                                :order_id, :payment_id, NOW(), NOW())
                    """), {
                        "user_id": user_id,
                        "plan_id": plan_name,
                        "start_at": start_date,
                        "end_at": end_date,
                        "order_id": order_id,
                        "payment_id": payment_id
                    })
                    
                    print(f"✅ Subscription activated: {plan_name}")
                    
                    # BLOCK S2: Update user entitlements
                    try:
                        # Determine dashboard_type based on plan
                        dashboard_type = None
                        if plan_name == "basic":
                            dashboard_type = "basic"
                        elif plan_name == "personal":
                            dashboard_type = "personal"
                        elif plan_name == "family":
                            dashboard_type = "family_admin"
                        
                        if dashboard_type:
                            await db.execute(text("""
                                UPDATE users 
                                SET plan_id = :plan_id,
                                    subscription_status = 'active',
                                    dashboard_type = :dashboard_type,
                                    updated_at = NOW()
                                WHERE id = :user_id
                            """), {
                                "user_id": user_id,
                                "plan_id": plan_name,
                                "dashboard_type": dashboard_type
                            })
                            
                            print(f"✅ User entitlements updated: plan={plan_name}, dashboard={dashboard_type}", flush=True)
                    except Exception as e:
                        print(f"❌ Failed to update user entitlements: {str(e)}", flush=True)
                    
                except Exception as e:
                    print(f"❌ Subscription activation failed: {str(e)}")
            
            print("✅ Webhook processing complete")
            
            return {
                "ok": True,
                "message": "Payment processed successfully",
                "invoice_number": invoice_number,
                "is_internal_test": is_internal_test
            }
        
        else:
            print(f"ℹ️ Ignoring event: {payload.get('event')}")
            return {"ok": True, "message": f"Event {payload.get('event')} ignored"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Webhook processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Webhook processing failed: {str(e)}")
