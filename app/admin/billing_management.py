"""
Admin Billing Management
Provides Super Admin access to invoices, refunds, and billing analytics
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import text
from datetime import datetime, timedelta
from ..utils import get_current_user, require_super_admin
from typing import Optional

router = APIRouter(prefix="/api/admin/billing", tags=["Admin Billing"])


@router.get("/invoices")
async def list_all_invoices(
    request: Request,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    List all invoices (Super Admin only)
    Supports filtering by status and pagination
    """
    # Verify super admin
    if not current_user.get('is_super_admin'):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    try:
        db = request.app.state.db
        
        # Build query
        query = """
            SELECT 
                i.id,
                i.invoice_number,
                i.user_id,
                u.username as customer_name,
                u.email as customer_email,
                i.razorpay_payment_id,
                i.amount,
                i.tax_amount,
                i.total_amount,
                i.subscription_plan,
                i.subscription_duration,
                i.status,
                i.invoice_date,
                i.created_at
            FROM invoices i
            LEFT JOIN users u ON i.user_id = u.id
        """
        
        params = {}
        
        if status:
            query += " WHERE i.status = :status"
            params['status'] = status
        
        query += " ORDER BY i.created_at DESC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        result = await db.execute(text(query), params)
        invoices = [dict(row._mapping) for row in result]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM invoices"
        if status:
            count_query += " WHERE status = :status"
        count_result = await db.execute(text(count_query), {'status': status} if status else {})
        total_count = count_result.scalar()
        
        return {
            "ok": True,
            "invoices": invoices,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch invoices: {str(e)}")


@router.get("/invoices/{invoice_id}")
async def get_invoice_details(
    invoice_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed invoice information (Super Admin only)
    """
    # Verify super admin
    if not current_user.get('is_super_admin'):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    try:
        db = request.app.state.db
        
        result = await db.execute(text("""
            SELECT 
                i.*,
                u.username as customer_name,
                u.email as customer_email,
                u.phone as customer_phone
            FROM invoices i
            LEFT JOIN users u ON i.user_id = u.id
            WHERE i.id = :invoice_id
        """), {"invoice_id": invoice_id})
        
        invoice = result.first()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        return {
            "ok": True,
            "invoice": dict(invoice._mapping)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch invoice: {str(e)}")


@router.get("/refunds")
async def list_all_refunds(
    request: Request,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    List all refund requests (Super Admin only)
    Supports filtering by status and pagination
    """
    # Verify super admin
    if not current_user.get('is_super_admin'):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    try:
        db = request.app.state.db
        
        # Build query
        query = """
            SELECT 
                r.id,
                r.user_id,
                u.username as customer_name,
                u.email as customer_email,
                r.razorpay_payment_id,
                r.invoice_id,
                i.invoice_number,
                r.amount,
                r.reason,
                r.status,
                r.hours_since_payment,
                r.within_24_hours,
                r.request_date,
                r.processed_date,
                r.admin_notes,
                r.razorpay_refund_id,
                r.refund_status
            FROM refund_requests r
            LEFT JOIN users u ON r.user_id = u.id
            LEFT JOIN invoices i ON r.invoice_id = i.id
        """
        
        params = {}
        
        if status:
            query += " WHERE r.status = :status"
            params['status'] = status
        
        query += " ORDER BY r.request_date DESC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        result = await db.execute(text(query), params)
        refunds = [dict(row._mapping) for row in result]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM refund_requests"
        if status:
            count_query += " WHERE status = :status"
        count_result = await db.execute(text(count_query), {'status': status} if status else {})
        total_count = count_result.scalar()
        
        return {
            "ok": True,
            "refunds": refunds,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch refunds: {str(e)}")


@router.get("/refunds/pending")
async def get_pending_refunds(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all pending refund requests (Super Admin only)
    Quick access for admin approval workflow
    """
    # Verify super admin
    if not current_user.get('is_super_admin'):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    try:
        db = request.app.state.db
        
        result = await db.execute(text("""
            SELECT 
                r.id,
                r.user_id,
                u.username as customer_name,
                u.email as customer_email,
                r.razorpay_payment_id,
                r.amount,
                r.reason,
                r.hours_since_payment,
                r.within_24_hours,
                r.request_date
            FROM refund_requests r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.status = 'pending'
            ORDER BY r.request_date ASC
        """))
        
        refunds = [dict(row._mapping) for row in result]
        
        return {
            "ok": True,
            "pending_refunds": refunds,
            "count": len(refunds)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pending refunds: {str(e)}")


@router.get("/analytics")
async def get_billing_analytics(
    request: Request,
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """
    Get billing analytics (Super Admin only)
    Revenue, invoices, refunds statistics
    """
    # Verify super admin
    if not current_user.get('is_super_admin'):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    try:
        db = request.app.state.db
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Total revenue
        revenue_result = await db.execute(text("""
            SELECT COALESCE(SUM(total_amount), 0) as total
            FROM invoices
            WHERE status = 'paid'
            AND invoice_date >= :start_date
        """), {"start_date": start_date})
        total_revenue = float(revenue_result.scalar() or 0)
        
        # Total invoices
        invoices_result = await db.execute(text("""
            SELECT COUNT(*) as total
            FROM invoices
            WHERE invoice_date >= :start_date
        """), {"start_date": start_date})
        total_invoices = invoices_result.scalar() or 0
        
        # Total refunds
        refunds_result = await db.execute(text("""
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as total
            FROM refund_requests
            WHERE status IN ('approved', 'processed')
            AND request_date >= :start_date
        """), {"start_date": start_date})
        refunds_data = refunds_result.first()
        total_refunds = refunds_data[0] if refunds_data else 0
        refunds_amount = float(refunds_data[1] if refunds_data else 0)
        
        # Pending refunds
        pending_result = await db.execute(text("""
            SELECT COUNT(*) as total
            FROM refund_requests
            WHERE status = 'pending'
        """))
        pending_refunds = pending_result.scalar() or 0
        
        # Revenue by plan
        plan_result = await db.execute(text("""
            SELECT 
                subscription_plan,
                COUNT(*) as count,
                SUM(total_amount) as revenue
            FROM invoices
            WHERE status = 'paid'
            AND invoice_date >= :start_date
            GROUP BY subscription_plan
        """), {"start_date": start_date})
        revenue_by_plan = [dict(row._mapping) for row in plan_result]
        
        # Daily revenue (last 7 days)
        daily_result = await db.execute(text("""
            SELECT 
                DATE(invoice_date) as date,
                COUNT(*) as invoices,
                SUM(total_amount) as revenue
            FROM invoices
            WHERE status = 'paid'
            AND invoice_date >= :start_date
            GROUP BY DATE(invoice_date)
            ORDER BY date DESC
            LIMIT 7
        """), {"start_date": end_date - timedelta(days=7)})
        daily_revenue = [dict(row._mapping) for row in daily_result]
        
        return {
            "ok": True,
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "summary": {
                "total_revenue": total_revenue,
                "total_invoices": total_invoices,
                "total_refunds": total_refunds,
                "refunds_amount": refunds_amount,
                "pending_refunds": pending_refunds,
                "net_revenue": total_revenue - refunds_amount,
                "refund_rate": (total_refunds / total_invoices * 100) if total_invoices > 0 else 0
            },
            "revenue_by_plan": revenue_by_plan,
            "daily_revenue": daily_revenue
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")


@router.get("/export/invoices")
async def export_invoices_csv(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Export invoices to CSV (Super Admin only)
    """
    # Verify super admin
    if not current_user.get('is_super_admin'):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    try:
        db = request.app.state.db
        
        query = """
            SELECT 
                i.invoice_number,
                i.invoice_date,
                u.username,
                u.email,
                i.subscription_plan,
                i.subscription_duration,
                i.amount,
                i.tax_amount,
                i.total_amount,
                i.status,
                i.razorpay_payment_id
            FROM invoices i
            LEFT JOIN users u ON i.user_id = u.id
        """
        
        params = {}
        conditions = []
        
        if start_date:
            conditions.append("i.invoice_date >= :start_date")
            params['start_date'] = start_date
        
        if end_date:
            conditions.append("i.invoice_date <= :end_date")
            params['end_date'] = end_date
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY i.invoice_date DESC"
        
        result = await db.execute(text(query), params)
        invoices = [dict(row._mapping) for row in result]
        
        return {
            "ok": True,
            "invoices": invoices,
            "count": len(invoices),
            "format": "csv_ready"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export invoices: {str(e)}")
