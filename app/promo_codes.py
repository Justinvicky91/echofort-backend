"""
Promo Code Management System
Created: Oct 28, 2025
Purpose: Referral/Promo code system with 10% discount and commission tracking
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime, timedelta
import random
import string
from app.utils import get_current_user
from app.rbac import guard_admin

router = APIRouter(prefix="/api/promo-codes", tags=["Promo Codes"])

# ============================================================================
# MODELS
# ============================================================================

class PromoCodeCreate(BaseModel):
    code: Optional[str] = None  # Auto-generate if not provided
    discount_percentage: float = 10.00
    created_by_name: str
    expires_at: Optional[datetime] = None
    max_uses: Optional[int] = None
    applicable_plans: List[str] = ["Personal", "Family"]
    notes: Optional[str] = None
    
    @validator('discount_percentage')
    def validate_discount(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Discount must be between 0 and 100')
        return v
    
    @validator('code')
    def validate_code(cls, v):
        if v and (len(v) < 4 or len(v) > 50):
            raise ValueError('Code must be between 4 and 50 characters')
        return v.upper() if v else None

class PromoCodeValidate(BaseModel):
    code: str
    plan_name: str
    original_amount: float

class PromoCodeResponse(BaseModel):
    id: int
    code: str
    discount_percentage: float
    created_by_name: str
    created_at: datetime
    expires_at: Optional[datetime]
    max_uses: Optional[int]
    current_uses: int
    is_active: bool
    applicable_plans: List[str]
    notes: Optional[str]

class PromoCodeUsageResponse(BaseModel):
    id: int
    promo_code: str
    user_email: str
    used_at: datetime
    original_amount: float
    discount_amount: float
    final_amount: float
    commission_amount: float
    commission_paid: bool

class PromoCodeAnalytics(BaseModel):
    code: str
    total_uses: int
    total_revenue: float
    total_discount_given: float
    total_commission: float
    commission_paid: float
    commission_pending: float
    users: List[dict]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_promo_code(length=8):
    """Generate a random promo code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

async def get_db_connection():
    """Get database connection (reuse from main app)"""
    from app.main import get_db
    return await get_db()

# ============================================================================
# SUPER ADMIN ENDPOINTS
# ============================================================================

@router.post("/create", dependencies=[Depends(guard_admin)])
async def create_promo_code(data: PromoCodeCreate, current_user: dict = Depends(get_current_user)):
    """Create a new promo code (Super Admin only)"""
    conn = await get_db_connection()
    
    try:
        # Generate code if not provided
        code = data.code or generate_promo_code()
        
        # Check if code already exists
        existing = await conn.fetchrow(
            "SELECT id FROM promo_codes WHERE code = $1", code
        )
        if existing:
            raise HTTPException(status_code=400, detail="Promo code already exists")
        
        # Insert promo code
        result = await conn.fetchrow("""
            INSERT INTO promo_codes (
                code, discount_percentage, created_by_user_id, created_by_name,
                expires_at, max_uses, applicable_plans, notes
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, code, discount_percentage, created_by_name, created_at,
                      expires_at, max_uses, current_uses, is_active, applicable_plans, notes
        """, code, data.discount_percentage, current_user['id'], data.created_by_name,
            data.expires_at, data.max_uses, data.applicable_plans, data.notes)
        
        return {
            "success": True,
            "promo_code": dict(result)
        }
    
    finally:
        await conn.close()

@router.get("/list", dependencies=[Depends(guard_admin)])
async def list_promo_codes(current_user: dict = Depends(get_current_user)):
    """List all promo codes with usage stats (Super Admin only)"""
    conn = await get_db_connection()
    
    try:
        codes = await conn.fetch("""
            SELECT 
                pc.*,
                COUNT(pcu.id) as usage_count,
                COALESCE(SUM(pcu.final_amount), 0) as total_revenue,
                COALESCE(SUM(pcu.discount_amount), 0) as total_discount,
                COALESCE(SUM(pcu.commission_amount), 0) as total_commission,
                COALESCE(SUM(CASE WHEN pcu.commission_paid THEN pcu.commission_amount ELSE 0 END), 0) as commission_paid,
                COALESCE(SUM(CASE WHEN NOT pcu.commission_paid THEN pcu.commission_amount ELSE 0 END), 0) as commission_pending
            FROM promo_codes pc
            LEFT JOIN promo_code_usage pcu ON pc.id = pcu.promo_code_id
            GROUP BY pc.id
            ORDER BY pc.created_at DESC
        """)
        
        return {
            "success": True,
            "promo_codes": [dict(code) for code in codes]
        }
    
    finally:
        await conn.close()

@router.get("/analytics/{code}", dependencies=[Depends(guard_admin)])
async def get_promo_code_analytics(code: str, current_user: dict = Depends(get_current_user)):
    """Get detailed analytics for a specific promo code (Super Admin only)"""
    conn = await get_db_connection()
    
    try:
        # Get promo code details
        promo = await conn.fetchrow(
            "SELECT * FROM promo_codes WHERE code = $1", code.upper()
        )
        if not promo:
            raise HTTPException(status_code=404, detail="Promo code not found")
        
        # Get usage details
        usages = await conn.fetch("""
            SELECT 
                pcu.*,
                u.email as user_email,
                u.full_name as user_name
            FROM promo_code_usage pcu
            JOIN users u ON pcu.user_id = u.id
            WHERE pcu.promo_code_id = $1
            ORDER BY pcu.used_at DESC
        """, promo['id'])
        
        # Calculate totals
        total_revenue = sum(u['final_amount'] for u in usages)
        total_discount = sum(u['discount_amount'] for u in usages)
        total_commission = sum(u['commission_amount'] for u in usages)
        commission_paid = sum(u['commission_amount'] for u in usages if u['commission_paid'])
        commission_pending = total_commission - commission_paid
        
        return {
            "success": True,
            "analytics": {
                "code": code,
                "total_uses": len(usages),
                "total_revenue": float(total_revenue),
                "total_discount_given": float(total_discount),
                "total_commission": float(total_commission),
                "commission_paid": float(commission_paid),
                "commission_pending": float(commission_pending),
                "users": [
                    {
                        "email": u['user_email'],
                        "name": u['user_name'],
                        "used_at": u['used_at'].isoformat(),
                        "amount_paid": float(u['final_amount']),
                        "commission": float(u['commission_amount']),
                        "commission_paid": u['commission_paid']
                    }
                    for u in usages
                ]
            }
        }
    
    finally:
        await conn.close()

@router.get("/commission-report", dependencies=[Depends(guard_admin)])
async def get_commission_report(current_user: dict = Depends(get_current_user)):
    """Get commission report grouped by referrer (Super Admin only)"""
    conn = await get_db_connection()
    
    try:
        report = await conn.fetch("""
            SELECT 
                pc.created_by_name as referrer_name,
                pc.code,
                COUNT(pcu.id) as total_referrals,
                COALESCE(SUM(pcu.commission_amount), 0) as total_commission,
                COALESCE(SUM(CASE WHEN pcu.commission_paid THEN pcu.commission_amount ELSE 0 END), 0) as commission_paid,
                COALESCE(SUM(CASE WHEN NOT pcu.commission_paid THEN pcu.commission_amount ELSE 0 END), 0) as commission_pending
            FROM promo_codes pc
            LEFT JOIN promo_code_usage pcu ON pc.id = pcu.promo_code_id
            WHERE pc.created_by_name IS NOT NULL
            GROUP BY pc.created_by_name, pc.code
            ORDER BY total_commission DESC
        """)
        
        return {
            "success": True,
            "commission_report": [dict(r) for r in report]
        }
    
    finally:
        await conn.close()

# ============================================================================
# PUBLIC ENDPOINTS (for signup/payment)
# ============================================================================

@router.post("/validate")
async def validate_promo_code(data: PromoCodeValidate):
    """Validate a promo code and calculate discount (Public endpoint for signup)"""
    conn = await get_db_connection()
    
    try:
        # Get promo code
        promo = await conn.fetchrow("""
            SELECT * FROM promo_codes 
            WHERE code = $1 AND is_active = TRUE
        """, data.code.upper())
        
        if not promo:
            raise HTTPException(status_code=404, detail="Invalid promo code")
        
        # Check expiry
        if promo['expires_at'] and promo['expires_at'] < datetime.now():
            raise HTTPException(status_code=400, detail="Promo code has expired")
        
        # Check max uses
        if promo['max_uses'] and promo['current_uses'] >= promo['max_uses']:
            raise HTTPException(status_code=400, detail="Promo code usage limit reached")
        
        # Check if applicable to this plan
        if data.plan_name not in promo['applicable_plans']:
            raise HTTPException(
                status_code=400, 
                detail=f"This promo code is only valid for: {', '.join(promo['applicable_plans'])}"
            )
        
        # Calculate discount
        discount_amount = (data.original_amount * promo['discount_percentage']) / 100
        final_amount = data.original_amount - discount_amount
        commission_amount = final_amount * 0.10  # 10% commission to referrer
        
        return {
            "success": True,
            "valid": True,
            "code": promo['code'],
            "discount_percentage": float(promo['discount_percentage']),
            "original_amount": data.original_amount,
            "discount_amount": float(discount_amount),
            "final_amount": float(final_amount),
            "savings": float(discount_amount),
            "commission_amount": float(commission_amount)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        await conn.close()

@router.post("/apply")
async def apply_promo_code(
    promo_code: str,
    user_id: int,
    subscription_id: int,
    original_amount: float,
    current_user: dict = Depends(get_current_user)
):
    """Apply promo code to a subscription (called during payment)"""
    conn = await get_db_connection()
    
    try:
        # Get promo code
        promo = await conn.fetchrow("""
            SELECT * FROM promo_codes 
            WHERE code = $1 AND is_active = TRUE
        """, promo_code.upper())
        
        if not promo:
            raise HTTPException(status_code=404, detail="Invalid promo code")
        
        # Calculate amounts
        discount_amount = (original_amount * promo['discount_percentage']) / 100
        final_amount = original_amount - discount_amount
        commission_amount = final_amount * 0.10
        
        # Record usage
        usage = await conn.fetchrow("""
            INSERT INTO promo_code_usage (
                promo_code_id, user_id, subscription_id,
                original_amount, discount_amount, final_amount, commission_amount
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """, promo['id'], user_id, subscription_id,
            original_amount, discount_amount, final_amount, commission_amount)
        
        # Update promo code usage count
        await conn.execute("""
            UPDATE promo_codes 
            SET current_uses = current_uses + 1
            WHERE id = $1
        """, promo['id'])
        
        # Update subscription with promo code
        await conn.execute("""
            UPDATE subscriptions 
            SET promo_code_id = $1, discount_applied = $2
            WHERE id = $3
        """, promo['id'], discount_amount, subscription_id)
        
        return {
            "success": True,
            "usage_id": usage['id'],
            "final_amount": float(final_amount),
            "discount_applied": float(discount_amount)
        }
    
    finally:
        await conn.close()
