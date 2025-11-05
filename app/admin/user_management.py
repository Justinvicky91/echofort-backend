"""
Admin User Management Endpoints
Provides Super Admin with user and employee management capabilities
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..deps import get_engine, get_settings
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
    skip: int = 0,
    limit: int = 100,
    admin=Depends(require_super_admin),
    engine=Depends(get_engine)
):
    """
    Get all users in the system
    Requires Super Admin authentication
    """
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
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
    admin=Depends(require_super_admin),
    engine=Depends(get_engine)
):
    """
    Get specific user details by ID
    Requires Super Admin authentication
    """
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
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
            
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "full_name": row[3],
                "phone": row[4],
                "subscription_status": row[5],
                "subscription_plan": row[6],
                "kyc_status": row[7],
                "address": {
                    "line1": row[8],
                    "line2": row[9],
                    "city": row[10],
                    "state": row[11],
                    "country": row[12],
                    "pincode": row[13]
                },
                "id_verification": {
                    "type": row[14],
                    "number": row[15],
                    "verified": row[16]
                },
                "created_at": row[17],
                "updated_at": row[18]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user: {str(e)}")

@router.get("/employees", response_model=List[EmployeeResponse])
async def get_all_employees(
    skip: int = 0,
    limit: int = 100,
    admin=Depends(require_super_admin),
    engine=Depends(get_engine)
):
    """
    Get all employees in the system
    Requires Super Admin authentication
    """
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
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
    admin=Depends(require_super_admin),
    engine=Depends(get_engine)
):
    """
    Get specific employee details by ID
    Requires Super Admin authentication
    """
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
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
            
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Employee not found")
            
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "role": row[3],
                "department": row[4],
                "status": row[5],
                "created_at": row[6],
                "updated_at": row[7]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch employee: {str(e)}")

@router.get("/stats")
async def get_system_stats(
    admin=Depends(require_super_admin),
    engine=Depends(get_engine)
):
    """
    Get system statistics
    Requires Super Admin authentication
    """
    try:
        with engine.begin() as conn:
            # Count users
            user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            
            # Count employees
            employee_count = conn.execute(text("SELECT COUNT(*) FROM employees")).scalar()
            
            # Count active subscriptions
            active_subs = conn.execute(text("""
                SELECT COUNT(*) FROM users 
                WHERE subscription_status = 'active'
            """)).scalar()
            
            # Count pending KYC
            pending_kyc = conn.execute(text("""
                SELECT COUNT(*) FROM users 
                WHERE kyc_status = 'pending' OR kyc_status IS NULL
            """)).scalar()
            
            return {
                "total_users": user_count,
                "total_employees": employee_count,
                "active_subscriptions": active_subs,
                "pending_kyc": pending_kyc
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")
