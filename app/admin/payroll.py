# app/admin/payroll.py
"""
EchoFort Payroll Management System
Handles employee salaries, payments, and payroll reports
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel
from ..rbac import guard_admin

router = APIRouter(prefix="/admin/payroll", tags=["Payroll Management"])

# Pydantic models for request validation
class EmployeeSalaryCreate(BaseModel):
    emp_id: int
    base_salary: float
    allowances: float = 0.0
    deductions: float = 0.0
    effective_from: date

class PayrollGenerate(BaseModel):
    month: int
    year: int

class SalaryDisbursement(BaseModel):
    payroll_id: int
    payment_method: str  # bank_transfer, upi, cash
    transaction_id: Optional[str] = None

# 1. Add/Update Employee Salary
@router.post("/salary", dependencies=[Depends(guard_admin)])
async def set_employee_salary(request: Request, payload: EmployeeSalaryCreate):
    """Set or update employee salary"""
    try:
        net_salary = payload.base_salary + payload.allowances - payload.deductions
        
        query = text("""
            INSERT INTO employee_salaries 
            (emp_id, base_salary, allowances, deductions, net_salary, effective_from, created_at)
            VALUES (:emp_id, :base, :allow, :deduct, :net, :effective, NOW())
            ON CONFLICT (emp_id) 
            DO UPDATE SET 
                base_salary = :base,
                allowances = :allow,
                deductions = :deduct,
                net_salary = :net,
                effective_from = :effective,
                updated_at = NOW()
            RETURNING salary_id
        """)
        
        result = await request.app.state.db.execute(query, {
            "emp_id": payload.emp_id,
            "base": payload.base_salary,
            "allow": payload.allowances,
            "deduct": payload.deductions,
            "net": net_salary,
            "effective": payload.effective_from
        })
        
        salary_id = result.fetchone()[0]
        
        return {
            "ok": True,
            "salary_id": salary_id,
            "net_salary": net_salary,
            "message": "Salary updated successfully"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to update salary: {str(e)}")

# 2. Get All Employee Salaries
@router.get("/salaries", dependencies=[Depends(guard_admin)])
async def list_employee_salaries(request: Request):
    """Get all employee salaries with employee details"""
    try:
        query = text("""
            SELECT 
                es.salary_id, es.emp_id, e.name as employee_name,
                e.department, e.role, es.base_salary, es.allowances,
                es.deductions, es.net_salary, es.effective_from,
                es.created_at, es.updated_at
            FROM employee_salaries es
            JOIN employees e ON es.emp_id = e.emp_id
            WHERE e.is_active = TRUE
            ORDER BY e.department, e.name
        """)
        
        rows = (await request.app.state.db.execute(query)).fetchall()
        salaries = [dict(r._mapping) for r in rows]
        
        return {"ok": True, "count": len(salaries), "salaries": salaries}
    
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch salaries: {str(e)}")

# 3. Generate Monthly Payroll
@router.post("/generate", dependencies=[Depends(guard_admin)])
async def generate_monthly_payroll(request: Request, payload: PayrollGenerate):
    """Generate payroll for all employees for a specific month"""
    try:
        check_query = text("""
            SELECT COUNT(*) FROM payroll_records 
            WHERE month = :month AND year = :year
        """)
        
        existing = (await request.app.state.db.execute(check_query, {
            "month": payload.month, "year": payload.year
        })).fetchone()[0]
        
        if existing > 0:
            return {
                "ok": False,
                "message": f"Payroll for {payload.month}/{payload.year} already exists"
            }
        
        generate_query = text("""
            INSERT INTO payroll_records 
            (emp_id, month, year, base_salary, allowances, deductions, net_salary, status, created_at)
            SELECT 
                es.emp_id, :month, :year,
                es.base_salary, es.allowances, es.deductions, es.net_salary,
                'pending', NOW()
            FROM employee_salaries es
            JOIN employees e ON es.emp_id = e.emp_id
            WHERE e.is_active = TRUE
            RETURNING payroll_id
        """)
        
        result = await request.app.state.db.execute(generate_query, {
            "month": payload.month, "year": payload.year
        })
        
        payroll_ids = [r[0] for r in result.fetchall()]
        
        return {
            "ok": True,
            "month": payload.month,
            "year": payload.year,
            "records_generated": len(payroll_ids),
            "message": f"Payroll generated for {len(payroll_ids)} employees"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to generate payroll: {str(e)}")

# 4. Get Payroll Records (Month-wise)
@router.get("/records", dependencies=[Depends(guard_admin)])
async def get_payroll_records(request: Request, month: int, year: int):
    """Get payroll records for a specific month"""
    try:
        query = text("""
            SELECT 
                pr.payroll_id, pr.emp_id, e.name as employee_name,
                e.department, pr.base_salary, pr.allowances, pr.deductions,
                pr.net_salary, pr.status, pr.paid_on, pr.payment_method,
                pr.transaction_id
            FROM payroll_records pr
            JOIN employees e ON pr.emp_id = e.emp_id
            WHERE pr.month = :month AND pr.year = :year
            ORDER BY e.department, e.name
        """)
        
        rows = (await request.app.state.db.execute(query, {
            "month": month, "year": year
        })).fetchall()
        
        records = [dict(r._mapping) for r in rows]
        total_salary = sum(r['net_salary'] for r in records)
        paid_count = sum(1 for r in records if r['status'] == 'paid')
        pending_count = len(records) - paid_count
        
        return {
            "ok": True, "month": month, "year": year,
            "total_employees": len(records),
            "paid_count": paid_count, "pending_count": pending_count,
            "total_salary": total_salary, "records": records
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch payroll records: {str(e)}")

# 5. Disburse Salary
@router.post("/disburse", dependencies=[Depends(guard_admin)])
async def disburse_salary(request: Request, payload: SalaryDisbursement):
    """Mark salary as paid"""
    try:
        query = text("""
            UPDATE payroll_records 
            SET status = 'paid', paid_on = NOW(),
                payment_method = :method, transaction_id = :txn_id
            WHERE payroll_id = :payroll_id
            RETURNING emp_id, net_salary
        """)
        
        result = await request.app.state.db.execute(query, {
            "payroll_id": payload.payroll_id,
            "method": payload.payment_method,
            "txn_id": payload.transaction_id
        })
        
        row = result.fetchone()
        if not row:
            raise HTTPException(404, "Payroll record not found")
        
        return {
            "ok": True, "payroll_id": payload.payroll_id,
            "emp_id": row[0], "amount_paid": row[1],
            "message": "Salary disbursed successfully"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to disburse salary: {str(e)}")

# 6. Get Payroll Summary (Annual)
@router.get("/summary", dependencies=[Depends(guard_admin)])
async def get_payroll_summary(request: Request, year: int):
    """Get annual payroll summary"""
    try:
        query = text("""
            SELECT 
                month, COUNT(*) as employee_count,
                SUM(net_salary) as total_salary,
                SUM(CASE WHEN status = 'paid' THEN net_salary ELSE 0 END) as paid_amount,
                SUM(CASE WHEN status = 'pending' THEN net_salary ELSE 0 END) as pending_amount
            FROM payroll_records
            WHERE year = :year
            GROUP BY month
            ORDER BY month
        """)
        
        rows = (await request.app.state.db.execute(query, {"year": year})).fetchall()
        monthly_summary = [dict(r._mapping) for r in rows]
        
        annual_total = sum(r['total_salary'] for r in monthly_summary)
        annual_paid = sum(r['paid_amount'] for r in monthly_summary)
        annual_pending = sum(r['pending_amount'] for r in monthly_summary)
        
        return {
            "ok": True, "year": year,
            "annual_total": annual_total,
            "annual_paid": annual_paid,
            "annual_pending": annual_pending,
            "monthly_breakdown": monthly_summary
        }
    
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch payroll summary: {str(e)}")
