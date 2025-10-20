# app/admin/infra_costs.py
"""
EchoFort Infrastructure Cost Monitoring System
Tracks hosting, database, email, API costs and provides scaling recommendations
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel
from ..rbac import guard_admin

router = APIRouter(prefix="/admin/infra-costs", tags=["Infrastructure Costs"])

class CostRecord(BaseModel):
    service: str  # railway, sendgrid, openai, razorpay, stripe
    amount: float
    billing_period: str  # daily, monthly
    date: date
    details: Optional[dict] = None

# 1. Record Infrastructure Cost
@router.post("/record", dependencies=[Depends(guard_admin)])
async def record_infrastructure_cost(request: Request, payload: CostRecord):
    """Record infrastructure cost from external services"""
    try:
        import json
        
        query = text("""
            INSERT INTO infrastructure_costs 
            (service, amount, billing_period, date, details, created_at)
            VALUES (:service, :amount, :period, :date, :details, NOW())
            RETURNING cost_id
        """)
        
        result = await request.app.state.db.execute(query, {
            "service": payload.service,
            "amount": payload.amount,
            "period": payload.billing_period,
            "date": payload.date,
            "details": json.dumps(payload.details) if payload.details else None
        })
        
        cost_id = result.fetchone()[0]
        
        return {"ok": True, "cost_id": cost_id, "message": "Infrastructure cost recorded"}
    
    except Exception as e:
        raise HTTPException(500, f"Failed to record cost: {str(e)}")

# 2. Get Current Month Costs
@router.get("/current-month", dependencies=[Depends(guard_admin)])
async def get_current_month_costs(request: Request):
    """Get all infrastructure costs for current month"""
    try:
        query = text("""
            SELECT 
                service,
                SUM(amount) as total_cost,
                COUNT(*) as billing_count,
                MIN(date) as first_billing,
                MAX(date) as last_billing
            FROM infrastructure_costs
            WHERE EXTRACT(MONTH FROM date) = EXTRACT(MONTH FROM NOW())
            AND EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM NOW())
            GROUP BY service
            ORDER BY total_cost DESC
        """)
        
        rows = (await request.app.state.db.execute(query)).fetchall()
        
        costs_breakdown = [dict(r._mapping) for r in rows]
        total_infra_cost = sum(r['total_cost'] for r in costs_breakdown)
        
        return {
            "ok": True,
            "month": datetime.now().month,
            "year": datetime.now().year,
            "total_infrastructure_cost": total_infra_cost,
            "breakdown": costs_breakdown
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch costs: {str(e)}")

# 3. Get Service-wise Costs (Historical)
@router.get("/service/{service_name}", dependencies=[Depends(guard_admin)])
async def get_service_costs(request: Request, service_name: str, months: int = 6):
    """Get historical costs for a specific service"""
    try:
        query = text("""
            SELECT 
                EXTRACT(MONTH FROM date) as month,
                EXTRACT(YEAR FROM date) as year,
                SUM(amount) as total_cost,
                AVG(amount) as avg_cost,
                COUNT(*) as billing_count
            FROM infrastructure_costs
            WHERE service = :service
            AND date >= NOW() - INTERVAL '6 months'
            GROUP BY EXTRACT(MONTH FROM date), EXTRACT(YEAR FROM date)
            ORDER BY year DESC, month DESC
            LIMIT :months
        """)
        
        rows = (await request.app.state.db.execute(query, {
            "service": service_name,
            "months": months
        })).fetchall()
        
        historical_data = [dict(r._mapping) for r in rows]
        
        return {
            "ok": True,
            "service": service_name,
            "period_months": months,
            "historical_costs": historical_data
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch service costs: {str(e)}")

# 4. Calculate Per-User Cost
@router.get("/per-user", dependencies=[Depends(guard_admin)])
async def calculate_per_user_cost(request: Request):
    """Calculate infrastructure cost per active user"""
    try:
        # Get current month total infra cost
        cost_query = text("""
            SELECT COALESCE(SUM(amount), 0) as total_cost
            FROM infrastructure_costs
            WHERE EXTRACT(MONTH FROM date) = EXTRACT(MONTH FROM NOW())
            AND EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM NOW())
        """)
        
        cost_result = await request.app.state.db.execute(cost_query)
        total_cost = cost_result.fetchone()[0]
        
        # Get active user count
        user_query = text("""
            SELECT COUNT(*) as user_count
            FROM subscriptions
            WHERE status = 'active'
        """)
        
        user_result = await request.app.state.db.execute(user_query)
        user_count = user_result.fetchone()[0] or 1
        
        # Calculate per-user cost
        cost_per_user = total_cost / user_count if user_count > 0 else 0
        
        # Calculate profit margin
        avg_revenue_per_user = (399 + 799 + 1499) / 3  # Average of plans
        margin = avg_revenue_per_user - cost_per_user
        margin_percent = (margin / avg_revenue_per_user * 100) if avg_revenue_per_user > 0 else 0
        
        return {
            "ok": True,
            "month": datetime.now().month,
            "year": datetime.now().year,
            "total_infrastructure_cost": total_cost,
            "active_users": user_count,
            "cost_per_user": round(cost_per_user, 2),
            "avg_revenue_per_user": round(avg_revenue_per_user, 2),
            "profit_margin_per_user": round(margin, 2),
            "profit_margin_percent": round(margin_percent, 2)
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to calculate per-user cost: {str(e)}")

# 5. Get Scaling Recommendations
@router.get("/recommendations", dependencies=[Depends(guard_admin)])
async def get_scaling_recommendations(request: Request):
    """AI-powered scaling recommendations based on usage"""
    try:
        # Get user count
        user_query = text("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
        user_count = (await request.app.state.db.execute(user_query)).fetchone()[0] or 0
        
        # Get current month cost
        cost_query = text("""
            SELECT COALESCE(SUM(amount), 0) FROM infrastructure_costs
            WHERE EXTRACT(MONTH FROM date) = EXTRACT(MONTH FROM NOW())
        """)
        current_cost = (await request.app.state.db.execute(cost_query)).fetchone()[0]
        
        recommendations = []
        
        # Railway scaling
        if user_count > 1000:
            recommendations.append({
                "service": "Railway",
                "recommendation": "Upgrade to Pro plan (₹2,000/month)",
                "reason": "User count > 1000, need better performance",
                "priority": "high",
                "estimated_cost_increase": 1000
            })
        elif user_count > 500:
            recommendations.append({
                "service": "Railway",
                "recommendation": "Consider upgrading to Hobby plan",
                "reason": "Growing user base, prepare for scale",
                "priority": "medium",
                "estimated_cost_increase": 500
            })
        
        # SendGrid scaling
        if user_count > 500:
            recommendations.append({
                "service": "SendGrid",
                "recommendation": "Upgrade to paid plan",
                "reason": "Free tier limit approaching",
                "priority": "high",
                "estimated_cost_increase": 300
            })
        
        # Database scaling
        if user_count > 2000:
            recommendations.append({
                "service": "PostgreSQL",
                "recommendation": "Add read replicas",
                "reason": "High user count requires database optimization",
                "priority": "critical",
                "estimated_cost_increase": 1500
            })
        
        # Cost optimization
        if current_cost > 5000:
            recommendations.append({
                "service": "General",
                "recommendation": "Review unused services and optimize",
                "reason": "Infrastructure cost exceeding ₹5,000/month",
                "priority": "medium",
                "estimated_cost_savings": current_cost * 0.15  # 15% potential savings
            })
        
        return {
            "ok": True,
            "current_users": user_count,
            "current_monthly_cost": current_cost,
            "recommendations_count": len(recommendations),
            "recommendations": recommendations
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to generate recommendations: {str(e)}")

# 6. Get Cost Projection
@router.get("/projection", dependencies=[Depends(guard_admin)])
async def get_cost_projection(request: Request, target_users: int):
    """Project infrastructure costs for target user count"""
    try:
        # Get current metrics
        current_users_query = text("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
        current_users = (await request.app.state.db.execute(current_users_query)).fetchone()[0] or 1
        
        current_cost_query = text("""
            SELECT COALESCE(SUM(amount), 0) FROM infrastructure_costs
            WHERE EXTRACT(MONTH FROM date) = EXTRACT(MONTH FROM NOW())
        """)
        current_cost = (await request.app.state.db.execute(current_cost_query)).fetchone()[0]
        
        # Calculate cost per user
        cost_per_user = current_cost / current_users if current_users > 0 else 0
        
        # Project costs
        projected_cost = cost_per_user * target_users
        
        # Add scaling overhead
        if target_users > 2000:
            projected_cost *= 1.3  # 30% overhead for enterprise infrastructure
        elif target_users > 1000:
            projected_cost *= 1.2  # 20% overhead for scaled infrastructure
        elif target_users > 500:
            projected_cost *= 1.1  # 10% overhead for growing infrastructure
        
        # Calculate projected revenue
        avg_plan_price = (399 + 799 + 1499) / 3
        projected_revenue = avg_plan_price * target_users
        
        # Calculate projected profit
        projected_profit = projected_revenue - projected_cost
        profit_margin = (projected_profit / projected_revenue * 100) if projected_revenue > 0 else 0
        
        return {
            "ok": True,
            "current_users": current_users,
            "target_users": target_users,
            "current_monthly_cost": round(current_cost, 2),
            "projected_monthly_cost": round(projected_cost, 2),
            "cost_increase": round(projected_cost - current_cost, 2),
            "projected_monthly_revenue": round(projected_revenue, 2),
            "projected_monthly_profit": round(projected_profit, 2),
            "projected_profit_margin_percent": round(profit_margin, 2),
            "is_profitable": projected_profit > 0
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to project costs: {str(e)}")
