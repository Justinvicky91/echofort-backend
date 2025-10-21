# app/admin/customer_exemptions.py
"""
Customer Exemption System
- Super Admin can mark users as VIP/Exempt
- Exempt users get free access (no payment required)
- Bypass auto-charge after trial
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import text
from datetime import datetime, timedelta
from ..utils import get_current_user

router = APIRouter(prefix="/admin/exemptions", tags=["admin"])

@router.post("/grant")
async def grant_exemption(payload: dict, request: Request, current_user=Depends(get_current_user)):
    """
    Grant exemption to a customer (Super Admin only)
    User will get free access without payment
    """
    db = request.app.state.db
    
    # Verify super admin
    employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee or not employee['is_super_admin']:
        raise HTTPException(403, "Only super admin can grant exemptions")
    
    user_id = payload.get("user_id")
    user_email = payload.get("user_email")
    exemption_type = payload.get("exemption_type", "vip")  # vip, partner, test, other
    reason = payload.get("reason", "")
    duration_days = payload.get("duration_days")  # None = permanent
    subscription_tier = payload.get("subscription_tier", "family_pack")  # Which tier to grant
    
    if not user_id and not user_email:
        raise HTTPException(400, "User ID or email required")
    
    # Get user
    if user_email:
        user = await db.fetch_one(text("""
            SELECT id FROM users WHERE email = :e
        """), {"e": user_email})
        if not user:
            raise HTTPException(404, "User not found")
        user_id = user['id']
    
    # Check if user exists
    user = await db.fetch_one(text("""
        SELECT id, email, name FROM users WHERE id = :id
    """), {"id": user_id})
    
    if not user:
        raise HTTPException(404, "User not found")
    
    # Calculate expiry
    expires_at = None
    if duration_days:
        expires_at = datetime.utcnow() + timedelta(days=duration_days)
    
    # Create exemption record
    await db.execute(text("""
        INSERT INTO customer_exemptions (
            user_id, exemption_type, reason, subscription_tier,
            granted_by, granted_at, expires_at, active
        )
        VALUES (:uid, :type, :reason, :tier, :by, NOW(), :exp, true)
        ON CONFLICT (user_id) DO UPDATE
        SET exemption_type = :type,
            reason = :reason,
            subscription_tier = :tier,
            granted_by = :by,
            granted_at = NOW(),
            expires_at = :exp,
            active = true
    """), {
        "uid": user_id,
        "type": exemption_type,
        "reason": reason,
        "tier": subscription_tier,
        "by": current_user['user_id'],
        "exp": expires_at
    })
    
    # Create or update subscription
    await db.execute(text("""
        INSERT INTO subscriptions (
            user_id, plan, status, is_exempt, exempt_reason,
            start_date, end_date, created_at
        )
        VALUES (:uid, :plan, 'active', true, :reason, NOW(), :end, NOW())
        ON CONFLICT (user_id) DO UPDATE
        SET plan = :plan,
            status = 'active',
            is_exempt = true,
            exempt_reason = :reason,
            end_date = :end,
            updated_at = NOW()
    """), {
        "uid": user_id,
        "plan": subscription_tier,
        "reason": reason,
        "end": expires_at
    })
    
    return {
        "ok": True,
        "message": "Exemption granted successfully",
        "user": {
            "id": user['id'],
            "email": user['email'],
            "name": user['name']
        },
        "exemption": {
            "type": exemption_type,
            "tier": subscription_tier,
            "duration": f"{duration_days} days" if duration_days else "Permanent",
            "expires_at": expires_at.isoformat() if expires_at else None
        }
    }

@router.get("/list")
async def list_exemptions(request: Request, current_user=Depends(get_current_user)):
    """
    List all exempt customers (Super Admin only)
    """
    db = request.app.state.db
    
    # Verify super admin
    employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee or not employee['is_super_admin']:
        raise HTTPException(403, "Only super admin can view exemptions")
    
    # Get all exemptions
    exemptions = await db.fetch_all(text("""
        SELECT 
            ce.id,
            ce.user_id,
            ce.exemption_type,
            ce.reason,
            ce.subscription_tier,
            ce.granted_at,
            ce.expires_at,
            ce.active,
            u.email,
            u.name,
            u.phone,
            grantor.name as granted_by_name
        FROM customer_exemptions ce
        JOIN users u ON ce.user_id = u.id
        LEFT JOIN users grantor ON ce.granted_by = grantor.id
        WHERE ce.active = true
        ORDER BY ce.granted_at DESC
    """))
    
    return {
        "total": len(exemptions),
        "exemptions": [dict(e) for e in exemptions]
    }

@router.post("/revoke/{user_id}")
async def revoke_exemption(user_id: int, request: Request, current_user=Depends(get_current_user)):
    """
    Revoke exemption from a customer (Super Admin only)
    User will need to pay for subscription
    """
    db = request.app.state.db
    
    # Verify super admin
    employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee or not employee['is_super_admin']:
        raise HTTPException(403, "Only super admin can revoke exemptions")
    
    # Deactivate exemption
    await db.execute(text("""
        UPDATE customer_exemptions
        SET active = false, revoked_at = NOW(), revoked_by = :by
        WHERE user_id = :uid
    """), {"uid": user_id, "by": current_user['user_id']})
    
    # Update subscription
    await db.execute(text("""
        UPDATE subscriptions
        SET is_exempt = false,
            status = 'trial',
            trial_end_at = NOW() + INTERVAL '24 hours',
            updated_at = NOW()
        WHERE user_id = :uid
    """), {"uid": user_id})
    
    return {
        "ok": True,
        "message": "Exemption revoked successfully",
        "note": "User will need to pay within 24 hours or subscription will be cancelled"
    }

@router.get("/check/{user_id}")
async def check_exemption(user_id: int, request: Request):
    """
    Check if a user is exempt (used by payment system)
    """
    db = request.app.state.db
    
    # Get exemption
    exemption = await db.fetch_one(text("""
        SELECT * FROM customer_exemptions
        WHERE user_id = :uid AND active = true
        AND (expires_at IS NULL OR expires_at > NOW())
    """), {"uid": user_id})
    
    if exemption:
        return {
            "is_exempt": True,
            "exemption_type": exemption['exemption_type'],
            "subscription_tier": exemption['subscription_tier'],
            "expires_at": exemption['expires_at'].isoformat() if exemption['expires_at'] else None
        }
    else:
        return {
            "is_exempt": False
        }

@router.put("/extend/{user_id}")
async def extend_exemption(
    user_id: int,
    payload: dict,
    request: Request,
    current_user=Depends(get_current_user)
):
    """
    Extend exemption duration (Super Admin only)
    """
    db = request.app.state.db
    
    # Verify super admin
    employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee or not employee['is_super_admin']:
        raise HTTPException(403, "Only super admin can extend exemptions")
    
    additional_days = payload.get("additional_days")
    if not additional_days or additional_days < 1:
        raise HTTPException(400, "Additional days must be at least 1")
    
    # Get current exemption
    exemption = await db.fetch_one(text("""
        SELECT expires_at FROM customer_exemptions
        WHERE user_id = :uid AND active = true
    """), {"uid": user_id})
    
    if not exemption:
        raise HTTPException(404, "No active exemption found for this user")
    
    # Calculate new expiry
    if exemption['expires_at']:
        new_expiry = exemption['expires_at'] + timedelta(days=additional_days)
    else:
        new_expiry = datetime.utcnow() + timedelta(days=additional_days)
    
    # Update exemption
    await db.execute(text("""
        UPDATE customer_exemptions
        SET expires_at = :exp, updated_at = NOW()
        WHERE user_id = :uid
    """), {"exp": new_expiry, "uid": user_id})
    
    # Update subscription
    await db.execute(text("""
        UPDATE subscriptions
        SET end_date = :exp, updated_at = NOW()
        WHERE user_id = :uid
    """), {"exp": new_expiry, "uid": user_id})
    
    return {
        "ok": True,
        "message": "Exemption extended successfully",
        "new_expiry": new_expiry.isoformat()
    }

