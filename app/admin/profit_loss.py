# app/admin/profit_loss.py
"""
EchoFort Profit & Loss Management System
Tracks revenue, expenses, and calculates P&L
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel
from ..rbac import guard_admin

router = APIRouter(prefix="/admin/profit-loss", tags=["Profit & Loss"])

class ExpenseCreate(BaseModel):
    category: str  # infrastructure, marketing, operations, salary, misc
    amount: float
    description: str
    date: date

# 1. Record Expense
@router.post("/expense", dependencies=[Depends(guard_admin)])
async def record_expense(request: Request, payload: ExpenseCreate):
    """Record a business expense"""
    try:
        query = text("""
            INSERT INTO expenses 
            (category, amount, description, date, created_at)
            VALUES (:category, :amount, :desc, :date, NOW())
            RETURNING expense_id
        """)
        
        result = await request.app.state.db.execute(query, {
            "category": payload.category,
            "amount": payload.amount,
            "desc": payload.description,
            "date": payload.date
        })
        
        expense_id = result.fetchone()[0]
        
        return {
            "ok": True,
            "expense_id": expense_id,
            "message": "Expense recorded successfully"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to record expense: {str(e)}")

# 2. Calculate Monthly Revenue
@router.get("/revenue", dependencies=[Depends(guard_admin)])
async def calculate_revenue(request: Request, month: int, year: int):
    """Calculate total revenue for a month from subscriptions"""
    try:
        query = text("""
            SELECT 
                plan,
                COUNT(*) as subscriber_count,
                CASE 
                    WHEN plan = 'basic' THEN 399
                    WHEN plan = 'personal' THEN 799
                    WHEN plan = 'family' THEN 1499
                    ELSE 0
                END as plan_price,
                COUNT(*) * CASE 
                    WHEN plan = 'basic' THEN 399
                    WHEN plan = 'personal' THEN 799
                    WHEN plan = 'family' THEN 1499
                    ELSE 0
                END as total_revenue
            FROM subscriptions
            WHERE status = 'active'
            AND EXTRACT(MONTH FROM started_at) = :month
            AND EXTRACT(YEAR FROM started_at) = :year
            GROUP BY plan
        """)
        
        rows = (await request.app.state.db.execute(query, {
            "month": month, "year": year
        })).fetchall()
        
        revenue_breakdown = [dict(r._mapping) for r in rows]
        total_revenue = sum(r['total_revenue'] for r in revenue_breakdown)
        total_subscribers = sum(r['subscriber_count'] for r in revenue_breakdown)
        
        return {
            "ok": True, "month": month, "year": year,
            "total_revenue": total_revenue,
            "total_subscribers": total_subscribers,
            "breakdown": revenue_breakdown
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to calculate revenue: {str(e)}")

# 3. Calculate Monthly Expenses
@router.get("/expenses", dependencies=[Depends(guard_admin)])
async def calculate_expenses(request: Request, month: int, year: int):
    """Calculate total expenses for a month"""
    try:
        query = text("""
            SELECT 
                category,
                COUNT(*) as transaction_count,
                SUM(amount) as total_amount
            FROM expenses
            WHERE EXTRACT(MONTH FROM date) = :month
            AND EXTRACT(YEAR FROM date) = :year
            GROUP BY category
            ORDER BY total_amount DESC
        """)
        
        rows = (await request.app.state.db.execute(query, {
            "month": month, "year": year
        })).fetchall()
        
        expense_breakdown = [dict(r._mapping) for r in rows]
        total_expenses = sum(r['total_amount'] for r in expense_breakdown)
        
        return {
            "ok": True, "month": month, "year": year,
            "total_expenses": total_expenses,
            "breakdown": expense_breakdown
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to calculate expenses: {str(e)}")

# 4. Get Monthly P&L Statement
@router.get("/statement", dependencies=[Depends(guard_admin)])
async def get_pl_statement(request: Request, month: int, year: int):
    """Generate complete P&L statement for a month"""
    try:
        # Calculate Revenue
        revenue_query = text("""
            SELECT 
                COALESCE(SUM(CASE 
                    WHEN plan = 'basic' THEN 399
                    WHEN plan = 'personal' THEN 799
                    WHEN plan = 'family' THEN 1499
                    ELSE 0
                END), 0) as revenue
            FROM subscriptions
            WHERE status = 'active'
            AND EXTRACT(MONTH FROM started_at) = :month
            AND EXTRACT(YEAR FROM started_at) = :year
        """)
        
        revenue_result = await request.app.state.db.execute(revenue_query, {
            "month": month, "year": year
        })
        total_revenue = revenue_result.fetchone()[0]
        
        # Calculate Expenses by Category
        expense_query = text("""
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE EXTRACT(MONTH FROM date) = :month
            AND EXTRACT(YEAR FROM date) = :year
            GROUP BY category
        """)
        
        expense_result = await request.app.state.db.execute(expense_query, {
            "month": month, "year": year
        })
        expense_rows = expense_result.fetchall()
        expense_breakdown = {r[0]: r[1] for r in expense_rows}
        total_expenses = sum(expense_breakdown.values())
        
        # Calculate Profit/Loss
        net_profit = total_revenue - total_expenses
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            "ok": True, "month": month, "year": year,
            "revenue": {"total": total_revenue},
            "expenses": {
                "total": total_expenses,
                "breakdown": expense_breakdown
            },
            "profit_loss": {
                "net_profit": net_profit,
                "profit_margin_percent": round(profit_margin, 2),
                "status": "profit" if net_profit >= 0 else "loss"
            }
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to generate P&L statement: {str(e)}")

# 5. Get Annual P&L Summary
@router.get("/annual", dependencies=[Depends(guard_admin)])
async def get_annual_pl(request: Request, year: int):
    """Get annual P&L summary with month-by-month breakdown"""
    try:
        # Monthly revenue
        revenue_query = text("""
            SELECT 
                EXTRACT(MONTH FROM started_at) as month,
                SUM(CASE 
                    WHEN plan = 'basic' THEN 399
                    WHEN plan = 'personal' THEN 799
                    WHEN plan = 'family' THEN 1499
                    ELSE 0
                END) as revenue
            FROM subscriptions
            WHERE status = 'active'
            AND EXTRACT(YEAR FROM started_at) = :year
            GROUP BY EXTRACT(MONTH FROM started_at)
            ORDER BY month
        """)
        
        revenue_rows = (await request.app.state.db.execute(revenue_query, {"year": year})).fetchall()
        monthly_revenue = {int(r[0]): r[1] for r in revenue_rows}
        
        # Monthly expenses
        expense_query = text("""
            SELECT 
                EXTRACT(MONTH FROM date) as month,
                SUM(amount) as expenses
            FROM expenses
            WHERE EXTRACT(YEAR FROM date) = :year
            GROUP BY EXTRACT(MONTH FROM date)
            ORDER BY month
        """)
        
        expense_rows = (await request.app.state.db.execute(expense_query, {"year": year})).fetchall()
        monthly_expenses = {int(r[0]): r[1] for r in expense_rows}
        
        # Build monthly breakdown
        monthly_data = []
        for month in range(1, 13):
            rev = monthly_revenue.get(month, 0)
            exp = monthly_expenses.get(month, 0)
            profit = rev - exp
            
            monthly_data.append({
                "month": month,
                "revenue": rev,
                "expenses": exp,
                "profit": profit
            })
        
        # Calculate annual totals
        annual_revenue = sum(monthly_revenue.values())
        annual_expenses = sum(monthly_expenses.values())
        annual_profit = annual_revenue - annual_expenses
        
        return {
            "ok": True, "year": year,
            "annual_summary": {
                "total_revenue": annual_revenue,
                "total_expenses": annual_expenses,
                "net_profit": annual_profit,
                "profit_margin_percent": round((annual_profit / annual_revenue * 100) if annual_revenue > 0 else 0, 2)
            },
            "monthly_breakdown": monthly_data
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch annual P&L: {str(e)}")

# 6. Get Expense Trends
@router.get("/expense-trends", dependencies=[Depends(guard_admin)])
async def get_expense_trends(request: Request, year: int):
    """Analyze expense trends by category"""
    try:
        query = text("""
            SELECT 
                category,
                EXTRACT(MONTH FROM date) as month,
                SUM(amount) as total
            FROM expenses
            WHERE EXTRACT(YEAR FROM date) = :year
            GROUP BY category, EXTRACT(MONTH FROM date)
            ORDER BY category, month
        """)
        
        rows = (await request.app.state.db.execute(query, {"year": year})).fetchall()
        
        # Group by category
        trends = {}
        for row in rows:
            category = row[0]
            month = int(row[1])
            amount = row[2]
            
            if category not in trends:
                trends[category] = []
            
            trends[category].append({"month": month, "amount": amount})
        
        return {"ok": True, "year": year, "expense_trends": trends}
    
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch expense trends: {str(e)}")
