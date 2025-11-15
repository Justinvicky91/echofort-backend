"""
Stripe Subscription & Payment Integration
Handles global payments via Stripe for international users
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from datetime import datetime
import stripe
import os
from .utils import get_current_user

router = APIRouter(prefix="/api/stripe", tags=["Stripe Payment"])

# Stripe API key initialization
STRIPE_API_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")

if STRIPE_API_KEY:
    stripe.api_key = STRIPE_API_KEY
else:
    print("⚠️ Stripe credentials not configured")

# Pricing plans (in USD for international users)
PRICING_PLANS_USD = {
    "basic": {
        "name": "Basic Plan",
        "amount": 5,  # $5/month
        "currency": "USD",
        "duration_days": 30
    },
    "personal": {
        "name": "Personal Plan",
        "amount": 10,  # $10/month
        "currency": "USD",
        "duration_days": 30
    },
    "family": {
        "name": "Family Plan",
        "amount": 18,  # $18/month
        "currency": "USD",
        "duration_days": 30
    }
}


class CreateCheckoutRequest(BaseModel):
    plan: str  # basic, personal, family
    success_url: str
    cancel_url: str


class VerifyPaymentRequest(BaseModel):
    session_id: str
    plan: str


@router.get("/config")
async def get_stripe_config():
    """
    Get Stripe publishable key for frontend
    """
    return {
        "ok": True,
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "currency": "USD"
    }


@router.post("/create-checkout-session")
async def create_checkout_session(
    payload: CreateCheckoutRequest,
    request: Request,
    user = Depends(get_current_user)
):
    """
    Create Stripe Checkout session for subscription payment
    """
    if not STRIPE_API_KEY:
        raise HTTPException(500, "Stripe not configured")
    
    if payload.plan not in PRICING_PLANS_USD:
        raise HTTPException(400, f"Invalid plan: {payload.plan}")
    
    plan_details = PRICING_PLANS_USD[payload.plan]
    
    try:
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': plan_details['currency'].lower(),
                    'product_data': {
                        'name': plan_details['name'],
                        'description': f'EchoFort {plan_details["name"]} - Monthly Subscription',
                    },
                    'unit_amount': plan_details['amount'] * 100,  # Stripe uses cents
                    'recurring': {
                        'interval': 'month',
                        'interval_count': 1
                    }
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=payload.success_url + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=payload.cancel_url,
            client_reference_id=str(user["id"]),
            customer_email=user.get("email"),
            metadata={
                'user_id': user["id"],
                'plan': payload.plan,
                'platform': 'echofort'
            }
        )
        
        # Log checkout session creation
        db = request.app.state.db
        await db.execute(text("""
            INSERT INTO payment_logs (
                user_id, payment_gateway, transaction_type, 
                amount, currency, status, gateway_session_id, created_at
            ) VALUES (
                :user_id, 'stripe', 'checkout_created',
                :amount, :currency, 'pending', :session_id, NOW()
            )
        """), {
            "user_id": user["id"],
            "amount": plan_details['amount'],
            "currency": plan_details['currency'],
            "session_id": checkout_session.id
        })
        
        return {
            "ok": True,
            "session_id": checkout_session.id,
            "checkout_url": checkout_session.url,
            "plan": payload.plan,
            "amount": plan_details['amount'],
            "currency": plan_details['currency']
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(500, f"Stripe error: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Payment error: {str(e)}")


@router.post("/verify-payment")
async def verify_stripe_payment(
    payload: VerifyPaymentRequest,
    request: Request,
    user = Depends(get_current_user)
):
    """
    Verify Stripe payment and activate subscription
    """
    if not STRIPE_API_KEY:
        raise HTTPException(500, "Stripe not configured")
    
    try:
        # Retrieve checkout session
        session = stripe.checkout.Session.retrieve(payload.session_id)
        
        if session.payment_status != 'paid':
            raise HTTPException(400, "Payment not completed")
        
        # Get subscription details
        subscription = stripe.Subscription.retrieve(session.subscription)
        
        db = request.app.state.db
        
        # Activate user subscription
        await db.execute(text("""
            UPDATE users
            SET 
                subscription_plan = :plan,
                subscription_status = 'active',
                subscription_start_date = NOW(),
                subscription_end_date = NOW() + INTERVAL '30 days',
                stripe_customer_id = :customer_id,
                stripe_subscription_id = :subscription_id,
                updated_at = NOW()
            WHERE id = :user_id
        """), {
            "user_id": user["id"],
            "plan": payload.plan,
            "customer_id": session.customer,
            "subscription_id": subscription.id
        })
        
        # Log successful payment
        await db.execute(text("""
            UPDATE payment_logs
            SET status = 'completed', updated_at = NOW()
            WHERE gateway_session_id = :session_id
        """), {"session_id": payload.session_id})
        
        # Create subscription record
        await db.execute(text("""
            INSERT INTO subscriptions (
                user_id, plan_name, amount, currency, 
                payment_gateway, gateway_subscription_id,
                status, start_date, end_date, created_at
            ) VALUES (
                :user_id, :plan, :amount, :currency,
                'stripe', :subscription_id,
                'active', NOW(), NOW() + INTERVAL '30 days', NOW()
            )
        """), {
            "user_id": user["id"],
            "plan": payload.plan,
            "amount": PRICING_PLANS_USD[payload.plan]['amount'],
            "currency": "USD",
            "subscription_id": subscription.id
        })
        
        return {
            "ok": True,
            "message": "Subscription activated successfully",
            "plan": payload.plan,
            "subscription_id": subscription.id,
            "status": "active",
            "next_billing_date": datetime.fromtimestamp(subscription.current_period_end).isoformat()
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(500, f"Stripe verification error: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Verification error: {str(e)}")


@router.post("/cancel-subscription")
async def cancel_stripe_subscription(
    request: Request,
    user = Depends(get_current_user)
):
    """
    Cancel Stripe subscription
    """
    if not STRIPE_API_KEY:
        raise HTTPException(500, "Stripe not configured")
    
    try:
        db = request.app.state.db
        
        # Get user's Stripe subscription ID
        user_query = text("""
            SELECT stripe_subscription_id
            FROM users
            WHERE id = :user_id
        """)
        result = (await db.execute(user_query, {"user_id": user["id"]})).fetchone()
        
        if not result or not result[0]:
            raise HTTPException(404, "No active Stripe subscription found")
        
        subscription_id = result[0]
        
        # Cancel subscription in Stripe
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        
        # Update database
        await db.execute(text("""
            UPDATE users
            SET 
                subscription_status = 'cancelled',
                updated_at = NOW()
            WHERE id = :user_id
        """), {"user_id": user["id"]})
        
        return {
            "ok": True,
            "message": "Subscription will be cancelled at period end",
            "subscription_id": subscription_id,
            "cancel_at": datetime.fromtimestamp(subscription.cancel_at).isoformat()
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(500, f"Stripe cancellation error: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Cancellation error: {str(e)}")


@router.get("/plans")
async def get_stripe_plans():
    """
    Get Stripe pricing plans (USD for international users)
    """
    return {
        "ok": True,
        "plans": PRICING_PLANS_USD,
        "currency": "USD",
        "note": "Prices in USD for international users"
    }
