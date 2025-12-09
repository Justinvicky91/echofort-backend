"""
Test endpoint to simulate subscription activation
Used for QA testing the subscription flow without real Razorpay payments
"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text
from datetime import datetime

router = APIRouter(prefix="/api/test", tags=["Test"])

@router.post("/activate-subscription/{user_id}/{plan_id}")
async def test_activate_subscription(user_id: int, plan_id: str, request: Request):
    """
    Test endpoint to simulate subscription activation
    Simulates what Razorpay webhook would do after successful payment
    
    Args:
        user_id: User ID to activate subscription for
        plan_id: Plan ID (basic, personal, family)
    """
    try:
        db = request.app.state.db
        
        # Validate plan_id
        valid_plans = {
            'basic': {'amount': 399.00, 'dashboard_type': 'basic'},
            'personal': {'amount': 799.00, 'dashboard_type': 'personal'},
            'family': {'amount': 1499.00, 'dashboard_type': 'family_admin'}
        }
        
        if plan_id not in valid_plans:
            raise HTTPException(status_code=400, detail=f"Invalid plan_id. Must be one of: {list(valid_plans.keys())}")
        
        plan_info = valid_plans[plan_id]
        
        # Update users table
        await db.execute(text("""
            UPDATE users 
            SET plan_id = :plan_id,
                subscription_status = 'active',
                dashboard_type = :dashboard_type,
                updated_at = NOW()
            WHERE id = :user_id
        """), {
            'plan_id': plan_id,
            'dashboard_type': plan_info['dashboard_type'],
            'user_id': user_id
        })
        
        # Insert subscription record
        await db.execute(text("""
            INSERT INTO subscriptions (user_id, plan, status, amount, razorpay_subscription_id, started_at, created_at, updated_at)
            VALUES (:user_id, :plan, 'active', :amount, :razorpay_id, NOW(), NOW(), NOW())
            ON CONFLICT (user_id, plan) 
            DO UPDATE SET 
                status = 'active',
                amount = EXCLUDED.amount,
                razorpay_subscription_id = EXCLUDED.razorpay_subscription_id,
                started_at = NOW(),
                updated_at = NOW()
        """), {
            'user_id': user_id,
            'plan': plan_id,
            'amount': plan_info['amount'],
            'razorpay_id': f'pay_test_{plan_id}_user{user_id}'
        })
        
        await db.commit()
        
        # Fetch updated user
        result = await db.execute(text("""
            SELECT id, email, plan_id, subscription_status, dashboard_type
            FROM users
            WHERE id = :user_id
        """), {'user_id': user_id})
        
        user = result.fetchone()
        
        return {
            "success": True,
            "message": f"Subscription activated for user {user_id} with plan {plan_id}",
            "user": {
                "id": user[0],
                "email": user[1],
                "plan_id": user[2],
                "subscription_status": user[3],
                "dashboard_type": user[4]
            }
        }
        
    except Exception as e:
        await db.rollback()
        import traceback
        return {
            "success": False,
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
