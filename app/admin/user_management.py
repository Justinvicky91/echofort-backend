"""
Admin User Management Endpoints
Provides Super Admin with user and employee management capabilities
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..utils import require_super_admin

router = APIRouter()

# Response models
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    subscription_status: Optional[str] = None
    subscription_plan: Optional[str] = None
    kyc_status: Optional[str] = None
    created_at: datetime
    
class EmployeeResponse(BaseModel):
    id: str
    name: str
    email: str
    role: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    created_at: datetime

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    admin=Depends(require_super_admin)
):
    """
    Get all users in the system
    Requires Super Admin authentication
    """
    try:
        db = request.app.state.db
        result = await db.fetch_all(text("""
            SELECT 
                id::text,
                username,
                email,
                full_name,
                phone,
                subscription_status,
                subscription_plan,
                kyc_status,
                created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :skip
        """), {"limit": limit, "skip": skip})
        
        users = []
        for row in result:
            users.append({
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "full_name": row[3],
                "phone": row[4],
                "subscription_status": row[5],
                "subscription_plan": row[6],
                "kyc_status": row[7],
                "created_at": row[8]
            })
        
        return users
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")

@router.get("/users/{user_id}")
async def get_user_by_id(
    user_id: str,
    request: Request,
    admin=Depends(require_super_admin)
):
    """
    Get specific user details by ID
    Requires Super Admin authentication
    """
    try:
        db = request.app.state.db
        result = await db.fetch_one(text("""
            SELECT 
                id::text,
                username,
                email,
                full_name,
                phone,
                subscription_status,
                subscription_plan,
                kyc_status,
                address_line1,
                address_line2,
                city,
                state,
                country,
                pincode,
                id_type,
                id_number,
                id_verified,
                created_at,
                updated_at
            FROM users
            WHERE id = :user_id::uuid
        """), {"user_id": user_id})
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": result[0],
            "username": result[1],
            "email": result[2],
            "full_name": result[3],
            "phone": result[4],
            "subscription_status": result[5],
            "subscription_plan": result[6],
            "kyc_status": result[7],
            "address": {
                "line1": result[8],
                "line2": result[9],
                "city": result[10],
                "state": result[11],
                "country": result[12],
                "pincode": result[13]
            },
            "id_verification": {
                "type": result[14],
                "number": result[15],
                "verified": result[16]
            },
            "created_at": result[17],
            "updated_at": result[18]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user: {str(e)}")

@router.get("/employees", response_model=List[EmployeeResponse])
async def get_all_employees(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    admin=Depends(require_super_admin)
):
    """
    Get all employees in the system
    Requires Super Admin authentication
    """
    try:
        db = request.app.state.db
        result = await db.fetch_all(text("""
            SELECT 
                id::text,
                name,
                email,
                role,
                department,
                status,
                created_at
            FROM employees
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :skip
        """), {"limit": limit, "skip": skip})
        
        employees = []
        for row in result:
            employees.append({
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "role": row[3],
                "department": row[4],
                "status": row[5],
                "created_at": row[6]
            })
        
        return employees
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch employees: {str(e)}")

@router.get("/employees/{employee_id}")
async def get_employee_by_id(
    employee_id: str,
    request: Request,
    admin=Depends(require_super_admin)
):
    """
    Get specific employee details by ID
    Requires Super Admin authentication
    """
    try:
        db = request.app.state.db
        result = await db.fetch_one(text("""
            SELECT 
                id::text,
                name,
                email,
                role,
                department,
                status,
                created_at,
                updated_at
            FROM employees
            WHERE id = :employee_id::uuid
        """), {"employee_id": employee_id})
        
        if not result:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        return {
            "id": result[0],
            "name": result[1],
            "email": result[2],
            "role": result[3],
            "department": result[4],
            "status": result[5],
            "created_at": result[6],
            "updated_at": result[7]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch employee: {str(e)}")

@router.get("/stats")
async def get_system_stats(
    request: Request,
    admin=Depends(require_super_admin)
):
    """
    Get system statistics
    Requires Super Admin authentication
    """
    try:
        db = request.app.state.db
        
        # Count users
        user_count = await db.fetch_val(text("SELECT COUNT(*) FROM users"))
        
        # Count employees
        employee_count = await db.fetch_val(text("SELECT COUNT(*) FROM employees"))
        
        # Count active subscriptions
        active_subs = await db.fetch_val(text("""
            SELECT COUNT(*) FROM users 
            WHERE subscription_status = 'active'
        """))
        
        # Count pending KYC
        pending_kyc = await db.fetch_val(text("""
            SELECT COUNT(*) FROM users 
            WHERE kyc_status = 'pending' OR kyc_status IS NULL
        """))
        
        return {
            "total_users": user_count,
            "total_employees": employee_count,
            "active_subscriptions": active_subs,
            "pending_kyc": pending_kyc
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")
