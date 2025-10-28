# app/auth/debug_employees.py
"""
Debug endpoint to check employees table
"""

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(prefix="/auth/debug", tags=["debug"])

@router.get("/employees-check")
async def check_employees_table(request: Request):
    """
    Debug endpoint to check employees table status
    """
    try:
        db = request.app.state.db
        
        # Check if table exists
        try:
            result = (await db.execute(text("SHOW TABLES LIKE 'employees'"))).fetchone()
            table_exists = result is not None
        except Exception as e:
            return {
                "table_exists": False,
                "error": f"Table check failed: {str(e)}"
            }
        
        if not table_exists:
            return {
                "table_exists": False,
                "message": "employees table does not exist"
            }
        
        # Count employees
        count_result = (await db.execute(text("SELECT COUNT(*) FROM employees"))).fetchone()
        total_count = count_result[0] if count_result else 0
        
        # Get all employees
        employees_result = await db.execute(text("""
            SELECT id, username, email, role, is_super_admin, active
            FROM employees
        """))
        employees = []
        for row in employees_result:
            employees.append({
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "role": row[3],
                "is_super_admin": bool(row[4]),
                "active": bool(row[5])
            })
        
        return {
            "table_exists": True,
            "total_employees": total_count,
            "employees": employees
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__
        }
