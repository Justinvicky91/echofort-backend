# app/subscription_enhanced.py - Enhanced Subscription Management
"""
Enhanced Subscription Management
- Auto-charge after 48-hour trial
- Recurring monthly billing
- Razorpay/Stripe subscription integration
- Email verification requirement
"""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr
from .utils import get_current_user
import os

router = APIRouter(prefix="/api/subscription", tags=["Subscription Enhanced"])

# Subscription pricing (excluding GST)
SUBSCRIPTION_PLANS = {
    "basic": {
        "name": "Basic Protection",
        "price": 349,
        "currency": "INR",
        "features": ["1 member", "Basic scam protection", "No call recording", "No dashboard"],
        "device_limit": 1
    },
    "personal": {
        "name": "Premium Plus",
        "price": 799,
        "currency": "INR",
        "features": ["1 member", "Advanced scam protection", "Call recording", "Full dashboard access"],
        "device_limit": 1
    },
    "family": {
        "name": "Family Pack",
        "price": 1299,
        "currency": "INR",
        "features": ["3 members", "All features", "Call recording", "Full dashboard access", "Family management"],
        "device_limit": 4
    }
}


class SubscriptionUpgrade(BaseModel):
    plan: Literal["basic", "personal", "family"]
    payment_method: Literal["razorpay", "stripe"]
    payment_id: Optional[str] = None  # For one-time payment
    subscription_id: Optional[str] = None  # For recurring subscription
    auto_renew: bool = True


class TrialConversion(BaseModel):
    plan: Literal["basic", "personal", "family"]
    payment_method: Literal["razorpay", "stripe"]
    razorpay_subscription_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None


async def check_trial_expiry(user_id: int, db) -> dict:
    """
    Check if trial has expired and needs conversion
    Returns: {trial_active, trial_expired, hours_remaining}
    """
    user_query = text("""
        SELECT trial_started_at, trial_ended_at, subscription_status
        FROM users
        WHERE id = :uid
    """)
    
    user = (await db.execute(user_query, {"uid": user_id})).fetchone()
    
    if not user or not user[0]:
        return {"trial_active": False, "trial_expired": False, "hours_remaining": 0}
    
    trial_start = user[0]
    trial_end_time = trial_start + timedelta(hours=48)
    now = datetime.now()
    
    if user[2] == "active":
        return {"trial_active": False, "trial_expired": False, "hours_remaining": 0, "status": "subscribed"}
    
    if now < trial_end_time:
        hours_remaining = (trial_end_time - now).total_seconds() / 3600
        return {"trial_active": True, "trial_expired": False, "hours_remaining": round(hours_remaining, 1)}
    else:
        return {"trial_active": False, "trial_expired": True, "hours_remaining": 0}


async def create_razorpay_subscription(plan: str, user_email: str) -> dict:
    """
    Create Razorpay subscription for recurring billing
    In production, integrate with Razorpay API
    """
    # This is a placeholder - integrate with actual Razorpay API
    plan_details = SUBSCRIPTION_PLANS[plan]
    
    # Razorpay subscription creation would happen here
    # For now, return mock subscription ID
    subscription_id = f"sub_razorpay_{plan}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "subscription_id": subscription_id,
        "plan_id": plan,
        "amount": plan_details["price"],
        "currency": plan_details["currency"],
        "status": "created"
    }


async def create_stripe_subscription(plan: str, user_email: str) -> dict:
    """
    Create Stripe subscription for recurring billing
    In production, integrate with Stripe API
    """
    # This is a placeholder - integrate with actual Stripe API
    plan_details = SUBSCRIPTION_PLANS[plan]
    
    # Stripe subscription creation would happen here
    subscription_id = f"sub_stripe_{plan}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "subscription_id": subscription_id,
        "plan_id": plan,
        "amount": plan_details["price"],
        "currency": plan_details["currency"],
        "status": "active"
    }


@router.get("/plans")
async def get_subscription_plans():
    """
    Get all available subscription plans with pricing
    """
    return {
        "ok": True,
        "plans": SUBSCRIPTION_PLANS,
        "currency": "INR",
        "note": "Prices exclude GST (18%)",
        "trial_period": "48 hours free trial"
    }


@router.get("/status")
async def get_subscription_status(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Get user's subscription status with trial information
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Get subscription from subscriptions table
        sub_query = text("""
            SELECT 
                plan, status, started_at, ends_at, trial_ends_at,
                auto_renew, payment_method, amount
            FROM subscriptions
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        subscription = (await db.execute(sub_query, {"uid": user_id})).fetchone()
        
        if not subscription:
            # Check trial status from users table
            trial_info = await check_trial_expiry(user_id, db)
            
            return {
                "ok": True,
                "subscription_status": "trial",
                "plan": None,
                "trial_active": trial_info.get("trial_active", False),
                "trial_expired": trial_info.get("trial_expired", False),
                "hours_remaining": trial_info.get("hours_remaining", 0),
                "message": "Free trial active" if trial_info.get("trial_active") else "Trial expired - please subscribe"
            }
        
        # Check if subscription is active
        now = datetime.now()
        is_active = subscription[1] == "active" and (not subscription[3] or subscription[3] > now)
        
        return {
            "ok": True,
            "subscription_status": subscription[1],
            "plan": subscription[0],
            "plan_details": SUBSCRIPTION_PLANS.get(subscription[0], {}),
            "started_at": str(subscription[2]),
            "ends_at": str(subscription[3]) if subscription[3] else None,
            "auto_renew": subscription[5],
            "payment_method": subscription[6],
            "amount": float(subscription[7]) if subscription[7] else 0,
            "is_active": is_active,
            "days_remaining": (subscription[3] - now).days if subscription[3] and subscription[3] > now else 0
        }
    
    except Exception as e:
        raise HTTPException(500, f"Status check error: {str(e)}")


@router.post("/upgrade")
async def upgrade_subscription(
    request: Request,
    payload: SubscriptionUpgrade,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Upgrade to paid subscription with recurring billing
    """
    try:
        user_id = current_user["id"]
        user_email = current_user.get("email", "")
        db = request.app.state.db
        
        # Get plan details
        plan_details = SUBSCRIPTION_PLANS.get(payload.plan)
        if not plan_details:
            raise HTTPException(400, "Invalid plan")
        
        # Create recurring subscription
        if payload.payment_method == "razorpay":
            subscription_info = await create_razorpay_subscription(payload.plan, user_email)
            subscription_id = subscription_info["subscription_id"]
        else:  # stripe
            subscription_info = await create_stripe_subscription(payload.plan, user_email)
            subscription_id = subscription_info["subscription_id"]
        
        # Save subscription to database
        insert_query = text("""
            INSERT INTO subscriptions (
                user_id, plan, status, started_at, ends_at,
                auto_renew, payment_method, razorpay_subscription_id,
                stripe_subscription_id, amount, currency, created_at
            ) VALUES (
                :uid, :plan, 'active', NOW(), NOW() + INTERVAL '30 days',
                :renew, :method, :razorpay_sub, :stripe_sub, :amount, 'INR', NOW()
            ) RETURNING subscription_id
        """)
        
        result = await db.execute(insert_query, {
            "uid": user_id,
            "plan": payload.plan,
            "renew": payload.auto_renew,
            "method": payload.payment_method,
            "razorpay_sub": subscription_id if payload.payment_method == "razorpay" else None,
            "stripe_sub": subscription_id if payload.payment_method == "stripe" else None,
            "amount": plan_details["price"]
        })
        
        sub_id = result.fetchone()[0]
        
        # Update user subscription status
        await db.execute(text("""
            UPDATE users
            SET 
                subscription_plan = :plan,
                subscription_status = 'active',
                subscription_start_date = NOW(),
                subscription_end_date = NOW() + INTERVAL '30 days',
                trial_ended_at = NOW()
            WHERE id = :uid
        """), {"plan": payload.plan, "uid": user_id})
        
        # Send confirmation email (background task)
        # background_tasks.add_task(send_subscription_confirmation_email, user_email, payload.plan)
        
        return {
            "ok": True,
            "subscription_id": sub_id,
            "plan": payload.plan,
            "plan_details": plan_details,
            "status": "active",
            "auto_renew": payload.auto_renew,
            "next_billing_date": str(datetime.now() + timedelta(days=30)),
            "message": f"Successfully subscribed to {plan_details['name']}",
            "payment_method": payload.payment_method
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Upgrade error: {str(e)}")


@router.post("/convert-trial")
async def convert_trial_to_paid(
    request: Request,
    payload: TrialConversion,
    current_user: dict = Depends(get_current_user)
):
    """
    Convert trial to paid subscription (auto-charge after trial)
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Check trial status
        trial_info = await check_trial_expiry(user_id, db)
        
        if not trial_info.get("trial_expired"):
            raise HTTPException(400, "Trial not expired yet")
        
        # Create subscription (same as upgrade)
        plan_details = SUBSCRIPTION_PLANS.get(payload.plan)
        
        # Create recurring subscription
        if payload.payment_method == "razorpay":
            subscription_id = payload.razorpay_subscription_id
        else:
            subscription_id = payload.stripe_subscription_id
        
        # Save subscription
        insert_query = text("""
            INSERT INTO subscriptions (
                user_id, plan, status, started_at, ends_at,
                auto_renew, payment_method, razorpay_subscription_id,
                stripe_subscription_id, amount, currency, created_at
            ) VALUES (
                :uid, :plan, 'active', NOW(), NOW() + INTERVAL '30 days',
                TRUE, :method, :razorpay_sub, :stripe_sub, :amount, 'INR', NOW()
            ) RETURNING subscription_id
        """)
        
        result = await db.execute(insert_query, {
            "uid": user_id,
            "plan": payload.plan,
            "method": payload.payment_method,
            "razorpay_sub": subscription_id if payload.payment_method == "razorpay" else None,
            "stripe_sub": subscription_id if payload.payment_method == "stripe" else None,
            "amount": plan_details["price"]
        })
        
        sub_id = result.fetchone()[0]
        
        # Update user
        await db.execute(text("""
            UPDATE users
            SET 
                subscription_plan = :plan,
                subscription_status = 'active',
                subscription_start_date = NOW(),
                subscription_end_date = NOW() + INTERVAL '30 days',
                trial_ended_at = NOW()
            WHERE id = :uid
        """), {"plan": payload.plan, "uid": user_id})
        
        return {
            "ok": True,
            "subscription_id": sub_id,
            "plan": payload.plan,
            "status": "active",
            "message": "Trial converted to paid subscription",
            "next_billing_date": str(datetime.now() + timedelta(days=30))
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Conversion error: {str(e)}")


@router.post("/cancel")
async def cancel_subscription(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Cancel subscription (stops auto-renewal)
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Update subscription status
        await db.execute(text("""
            UPDATE subscriptions
            SET status = 'cancelled', auto_renew = FALSE
            WHERE user_id = :uid AND status = 'active'
        """), {"uid": user_id})
        
        await db.execute(text("""
            UPDATE users
            SET subscription_status = 'cancelled'
            WHERE id = :uid
        """), {"uid": user_id})
        
        return {
            "ok": True,
            "message": "Subscription cancelled. Access will continue until end of billing period.",
            "note": "You can reactivate anytime before the period ends"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Cancellation error: {str(e)}")


@router.post("/reactivate")
async def reactivate_subscription(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Reactivate cancelled subscription
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Check if subscription exists and is cancelled
        sub_query = text("""
            SELECT subscription_id, plan, ends_at
            FROM subscriptions
            WHERE user_id = :uid AND status = 'cancelled'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        subscription = (await db.execute(sub_query, {"uid": user_id})).fetchone()
        
        if not subscription:
            raise HTTPException(404, "No cancelled subscription found")
        
        # Check if still within billing period
        if subscription[2] and subscription[2] < datetime.now():
            raise HTTPException(400, "Subscription expired. Please create a new subscription.")
        
        # Reactivate
        await db.execute(text("""
            UPDATE subscriptions
            SET status = 'active', auto_renew = TRUE
            WHERE subscription_id = :sid
        """), {"sid": subscription[0]})
        
        await db.execute(text("""
            UPDATE users
            SET subscription_status = 'active'
            WHERE id = :uid
        """), {"uid": user_id})
        
        return {
            "ok": True,
            "message": "Subscription reactivated successfully",
            "plan": subscription[1],
            "next_billing_date": str(subscription[2])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Reactivation error: {str(e)}")


@router.get("/billing-history")
async def get_billing_history(request: Request, current_user: dict = Depends(get_current_user), limit: int = 12):
    """
    Get user's billing history
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        history_query = text("""
            SELECT 
                subscription_id, plan, amount, currency,
                started_at, ends_at, status, payment_method
            FROM subscriptions
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT :lim
        """)
        
        history = (await db.execute(history_query, {"uid": user_id, "lim": limit})).fetchall()
        
        return {
            "ok": True,
            "total": len(history),
            "billing_history": [
                {
                    "subscription_id": h[0],
                    "plan": h[1],
                    "amount": float(h[2]) if h[2] else 0,
                    "currency": h[3],
                    "period_start": str(h[4]),
                    "period_end": str(h[5]) if h[5] else None,
                    "status": h[6],
                    "payment_method": h[7]
                }
                for h in history
            ]
        }
    
    except Exception as e:
        raise HTTPException(500, f"Billing history error: {str(e)}")

