"""
Financial Management API
BLOCK S1-PDF-AND-REVENUE-FIX Phase 3
Provides endpoints for Financial Center with real revenue from invoices table
"""
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from typing import Optional

router = APIRouter(prefix="/admin/profit-loss", tags=["Financial"])


@router.get("/statement")
async def get_financial_overview(request: Request):
    """
    Get overall financial statement with revenue, expenses, and profit/loss
    """
    try:
        db = request.app.state.db
        
        # Get total revenue from paid invoices (excluding internal tests)
        revenue_query = text("""
            SELECT 
                COALESCE(SUM(amount), 0) as total_revenue,
                COUNT(*) as invoice_count
            FROM invoices
            WHERE status = 'paid'
              AND is_internal_test = false
        """)
        
        revenue_result = (await db.execute(revenue_query)).fetchone()
        total_revenue = float(revenue_result[0]) if revenue_result else 0.0
        invoice_count = revenue_result[1] if revenue_result else 0
        
        # Convert from paise to rupees
        total_revenue_inr = total_revenue / 100
        
        # Sample expenses (can be moved to a separate expenses table later)
        total_expenses = 4150  # Railway + OpenAI + SendGrid + Payment gateways
        
        # Calculate profit/loss
        net_profit = total_revenue_inr - total_expenses
        profit_margin_percent = (net_profit / total_revenue_inr * 100) if total_revenue_inr > 0 else 0
        
        return {
            "ok": True,
            "revenue": {
                "total": total_revenue_inr,
                "invoice_count": invoice_count
            },
            "expenses": {
                "total": total_expenses,
                "breakdown": {
                    "infra_railway": 2500,
                    "infra_openai": 850,
                    "infra_sendgrid": 500,
                    "infra_razorpay": 200,
                    "infra_stripe": 100
                }
            },
            "profit_loss": {
                "net_profit": round(net_profit, 2),
                "profit_margin_percent": round(profit_margin_percent, 2),
                "status": "profit" if net_profit >= 0 else "loss"
            }
        }
    
    except Exception as e:
        print(f"❌ Error fetching financial overview: {str(e)}")
        raise HTTPException(500, f"Failed to fetch financial overview: {str(e)}")


@router.get("/revenue")
async def get_revenue_breakdown(
    request: Request, 
    month: Optional[int] = None, 
    year: Optional[int] = None
):
    """
    Get revenue breakdown by plan for a specific month/year
    """
    try:
        db = request.app.state.db
        
        # Build query with optional month/year filter
        where_clause = "WHERE status = 'paid' AND is_internal_test = false"
        params = {}
        
        if month and year:
            where_clause += " AND EXTRACT(MONTH FROM created_at) = :month AND EXTRACT(YEAR FROM created_at) = :year"
            params = {"month": month, "year": year}
        
        # Get total revenue
        total_query = text(f"""
            SELECT COALESCE(SUM(amount), 0) as total_revenue
            FROM invoices
            {where_clause}
        """)
        
        total_result = (await db.execute(total_query, params)).fetchone()
        total_revenue = float(total_result[0]) if total_result else 0.0
        
        # Convert from paise to rupees
        total_revenue_inr = total_revenue / 100
        
        # Get revenue breakdown by plan
        breakdown_query = text(f"""
            SELECT 
                COALESCE(plan_name, 'Unknown') as plan,
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as revenue
            FROM invoices
            {where_clause}
            GROUP BY plan_name
            ORDER BY revenue DESC
        """)
        
        breakdown_results = (await db.execute(breakdown_query, params)).fetchall()
        
        revenue_by_plan = []
        for row in breakdown_results:
            revenue_by_plan.append({
                "plan": row[0],
                "count": row[1],
                "revenue": float(row[2]) / 100  # Convert to rupees
            })
        
        return {
            "ok": True,
            "total_revenue": total_revenue_inr,
            "revenue_by_plan": revenue_by_plan
        }
    
    except Exception as e:
        print(f"❌ Error fetching revenue breakdown: {str(e)}")
        raise HTTPException(500, f"Failed to fetch revenue breakdown: {str(e)}")


@router.get("/expenses")
async def get_expense_breakdown(
    request: Request,
    month: Optional[int] = None,
    year: Optional[int] = None
):
    """
    Get expense breakdown by category for a specific month/year
    """
    try:
        # For now, return static expenses
        # TODO: Move to a separate expenses table in the future
        expenses_by_category = [
            {"category": "Railway Hosting", "total_amount": 2500},
            {"category": "OpenAI API", "total_amount": 850},
            {"category": "SendGrid Email", "total_amount": 500},
            {"category": "Razorpay Fees", "total_amount": 200},
            {"category": "Stripe Fees", "total_amount": 100}
        ]
        
        total_expenses = sum(e["total_amount"] for e in expenses_by_category)
        
        return {
            "ok": True,
            "total_expenses": total_expenses,
            "expenses_by_category": expenses_by_category
        }
    
    except Exception as e:
        print(f"❌ Error fetching expense breakdown: {str(e)}")
        raise HTTPException(500, f"Failed to fetch expense breakdown: {str(e)}")
