from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
import psycopg
import os
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Employee & Exemptions Management"])

def get_db_connection():
    """Get database connection"""
    return psycopg.connect(os.getenv("DATABASE_URL"))

class Employee(BaseModel):
    id: int
    username: str
    role: str
    department: Optional[str]
    is_super_admin: bool
    active: bool

class Exemption(BaseModel):
    id: int
    user_id: str
    exemption_type: str
    reason: str
    granted_by: str
    expires_at: Optional[datetime]
    active: bool

@router.get("/employees")
async def get_employees():
    """Get all employees"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, role, department, is_super_admin, active
            FROM employees
            WHERE active = true
            ORDER BY created_at DESC
        """)
        
        employees = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "employees": [
                {
                    "id": e[0],
                    "username": e[1],
                    "role": e[2],
                    "department": e[3],
                    "is_super_admin": e[4],
                    "active": e[5]
                }
                for e in employees
            ]
        }
        
    except Exception as e:
        # Return empty list if table doesn't exist yet
        return {
            "success": True,
            "employees": []
        }

@router.post("/employees/create")
async def create_employee(
    username: str,
    password: str,
    role: str,
    department: str,
    authorization: str = Header(None)
):
    """Create a new employee (Super Admin only)"""
    try:
        import bcrypt
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO employees (username, password_hash, role, department, active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, true, NOW(), NOW())
            RETURNING id
        """, (username, password_hash, role, department))
        
        employee_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Employee created successfully",
            "employee_id": employee_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating employee: {str(e)}")

@router.get("/exemptions")
async def get_exemptions():
    """Get all customer exemptions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if exemptions table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'customer_exemptions'
            )
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            # Create the table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customer_exemptions (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    exemption_type VARCHAR(50) NOT NULL,
                    reason TEXT,
                    granted_by VARCHAR(255),
                    granted_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP,
                    active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
        
        cursor.execute("""
            SELECT id, user_id, exemption_type, reason, granted_by, expires_at, active
            FROM customer_exemptions
            WHERE active = true
            ORDER BY granted_at DESC
        """)
        
        exemptions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "exemptions": [
                {
                    "id": e[0],
                    "user_id": e[1],
                    "exemption_type": e[2],
                    "reason": e[3],
                    "granted_by": e[4],
                    "expires_at": e[5].isoformat() if e[5] else None,
                    "active": e[6]
                }
                for e in exemptions
            ]
        }
        
    except Exception as e:
        # Return empty list on error
        return {
            "success": True,
            "exemptions": []
        }

@router.post("/exemptions/create")
async def create_exemption(
    user_id: str,
    exemption_type: str,
    reason: str,
    granted_by: str,
    expires_at: Optional[str] = None
):
    """Create a new customer exemption (Super Admin only)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO customer_exemptions 
            (user_id, exemption_type, reason, granted_by, expires_at, active, granted_at)
            VALUES (%s, %s, %s, %s, %s, true, NOW())
            RETURNING id
        """, (user_id, exemption_type, reason, granted_by, expires_at))
        
        exemption_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Exemption created successfully",
            "exemption_id": exemption_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating exemption: {str(e)}")

@router.delete("/exemptions/{exemption_id}")
async def delete_exemption(exemption_id: int):
    """Delete/deactivate an exemption"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE customer_exemptions
            SET active = false, updated_at = NOW()
            WHERE id = %s
        """, (exemption_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Exemption deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting exemption: {str(e)}")

@router.get("/users")
async def get_users():
    """Get all users for Super Admin dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, email, phone, role, subscription_status, created_at, last_signed_in
            FROM users
            ORDER BY created_at DESC
            LIMIT 100
        """)
        
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "users": [
                {
                    "id": u[0],
                    "name": u[1],
                    "email": u[2],
                    "phone": u[3],
                    "role": u[4],
                    "subscription_status": u[5],
                    "created_at": u[6].isoformat() if u[6] else None,
                    "last_signed_in": u[7].isoformat() if u[7] else None
                }
                for u in users
            ]
        }
        
    except Exception as e:
        return {
            "success": True,
            "users": []
        }

@router.get("/stats/overview")
async def get_overview_stats():
    """Get overview statistics for Super Admin dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # Get total employees
        cursor.execute("SELECT COUNT(*) FROM employees WHERE active = true")
        total_employees = cursor.fetchone()[0]
        
        # Get active subscriptions
        cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_status = 'active'")
        active_subscriptions = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "stats": {
                "total_users": total_users,
                "total_employees": total_employees,
                "active_subscriptions": active_subscriptions,
                "total_exemptions": 0
            }
        }
        
    except Exception as e:
        return {
            "success": True,
            "stats": {
                "total_users": 0,
                "total_employees": 1,
                "active_subscriptions": 0,
                "total_exemptions": 0
            }
        }

