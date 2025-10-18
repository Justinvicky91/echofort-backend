# app/subscription.py
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy import text
from datetime import datetime, timedelta
from .utils import get_current_user

router = APIRouter(prefix="/subscription", tags=["subscription"])

@router.get("/status")
async def subscription_status(
    request: Request,
    user = Depends(get_current_user)
):
    """Get user's current subscription status"""
    db = request.app.state.db
    row = (await db.execute(text("""
        SELECT 
            subscription_plan,
            subscription_status,
            subscription_start_date,
            subscription_end_date,
            trial_started_at,
            trial_ended_at
        FROM users
        WHERE user_id = :uid
    """), {"uid": user["user_id"]})).fetchone()
    
    if not row:
        raise HTTPException(404, "User not found")
    
    # Check if trial is active
    trial_active = False
    if row.trial_started_at and not row.trial_ended_at:
        trial_end = row.trial_started_at + timedelta(hours=48)
        trial_active = datetime.now() < trial_end
    
    return {
        "plan": row.subscription_plan or "trial",
        "status": row.subscription_status or "trial",
        "trial_active": trial_active,
        "start_date": str(row.subscription_start_date) if row.subscription_start_date else None,
        "end_date": str(row.subscription_end_date) if row.subscription_end_date else None
    }


@router.post("/upgrade")
async def upgrade_subscription(
    payload: dict,
    request: Request,
    user = Depends(get_current_user)
):
    """
    Upgrade subscription
    Payload: {"plan": "basic|personal|family", "razorpay_payment_id": "pay_xxx"}
    """
    plan = payload.get("plan")
    payment_id = payload.get("razorpay_payment_id")
    
    if plan not in ["basic", "personal", "family"]:
        raise HTTPException(400, "Invalid plan")
    
    db = request.app.state.db
    await db.execute(text("""
        UPDATE users
        SET 
            subscription_plan = :plan,
            subscription_status = 'active',
            subscription_start_date = NOW(),
            subscription_end_date = NOW() + INTERVAL '30 days',
            razorpay_payment_id = :pay_id
        WHERE user_id = :uid
    """), {"plan": plan, "pay_id": payment_id, "uid": user["user_id"]})
    
    return {"ok": True, "message": f"Upgraded to {plan} plan"}


@router.post("/cancel")
async def cancel_subscription(
    request: Request,
    user = Depends(get_current_user)
):
    """Cancel active subscription"""
    db = request.app.state.db
    await db.execute(text("""
        UPDATE users
        SET subscription_status = 'cancelled'
        WHERE user_id = :uid
    """), {"uid": user["user_id"]})
    
    return {"ok": True, "message": "Subscription cancelled"}
