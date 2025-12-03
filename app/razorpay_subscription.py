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
        
        # Validate webhook signature
        webhook_signature = request.headers.get("X-Razorpay-Signature", "")
        webhook_secret = RAZORPAY_KEY_SECRET
        
        if not webhook_secret:
            print("⚠️ Webhook secret not configured - skipping signature verification")
        else:
            try:
                # Verify signature
                expected_signature = hmac.new(
                    str(webhook_secret).encode('utf-8'),
                    body_bytes,
                    hashlib.sha256
                ).hexdigest()
                
                if webhook_signature != expected_signature:
                    print(f"❌ Invalid webhook signature")
                    print(f"   Expected: {expected_signature}")
                    print(f"   Received: {webhook_signature}")
                    raise HTTPException(400, "Invalid webhook signature")
                
                print("✅ Webhook signature verified")
            except Exception as e:
                print(f"❌ Signature verification error: {str(e)}")
                import traceback
                traceback.print_exc()
                raise HTTPException(500, f"Signature verification failed: {str(e)}")
        
        # Handle payment.captured event
        if payload.get("event") == "payment.captured":
            print("💰 Processing payment.captured event")
            
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
            
            print(f"   Order ID: {order_id}")
            print(f"   Payment ID: {payment_id}")
            print(f"   Amount: ₹{amount/100}")
            print(f"   Email: {email}")
            
            # Determine if internal test (₹1 = 100 paise)
            is_internal_test = (amount == 100)
            print(f"   Internal Test: {is_internal_test}")
            
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
            
            print(f"   Invoice Number: {invoice_number}")
            
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
            
            print(f"   PDF Generated: {pdf_generated}")
            
            # Determine user_id
            user_id = 1  # SuperAdmin for now
            
            print("📝 Invoice creation started...")
            
            # Insert invoice
            await db.execute(text("""
                INSERT INTO invoices 
                (user_id, razorpay_order_id, razorpay_payment_id, invoice_number,
                 amount, currency, is_internal_test, status, invoice_html, pdf_url, created_at, updated_at)
                VALUES (:user_id, :order_id, :payment_id, :invoice_number,
                        :amount, :currency, :is_internal_test, 'paid', :html_content, :pdf_url, NOW(), NOW())
            """), {
                "user_id": user_id,
                "order_id": order_id,
                "payment_id": payment_id,
                "invoice_number": invoice_number,
                "amount": amount,
                "currency": currency,
                "is_internal_test": is_internal_test,
                "html_content": html_content,
                "pdf_url": pdf_url
            })
            
            print(f"✅ Invoice created: {invoice_number}")
            print("📝 Invoice creation finished")
            
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
