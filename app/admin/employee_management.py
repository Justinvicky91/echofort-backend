# app/admin/employee_management.py
"""
Employee Management System
Only accessible by Super Admin
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import text
from datetime import datetime
import hashlib
from ..utils import get_current_user, is_admin

router = APIRouter(prefix="/admin/employees", tags=["admin"])

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

@router.post("/create")
async def create_employee(payload: dict, request: Request, current_user=Depends(get_current_user)):
    """
    Create new employee (Super Admin only)
    
    Roles: admin, marketing, customer_support, accounting, hr
    """
    # Verify super admin
    db = request.app.state.db
    
    employee_check = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee_check or not employee_check['is_super_admin']:
        raise HTTPException(403, "Only super admin can create employees")
    
    username = payload.get("username")
    password = payload.get("password")
    role = payload.get("role")  # admin, marketing, customer_support, accounting, hr
    department = payload.get("department")
    email = payload.get("email")
    name = payload.get("name", "Employee")
    
    if not username or not password or not role:
        raise HTTPException(400, "Username, password, and role required")
    
    valid_roles = ["admin", "marketing", "customer_support", "accounting", "hr"]
    if role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    # Check if username already exists
    existing = await db.fetch_one(text("""
        SELECT id FROM employees WHERE username = :u
    """), {"u": username})
    
    if existing:
        raise HTTPException(400, "Username already exists")
    
    # Create user account if email provided
    user_id = None
    if email:
        await db.execute(text("""
            INSERT INTO users(email, name, created_at)
            VALUES (:e, :n, NOW())
            ON CONFLICT (email) DO NOTHING
        """), {"e": email, "n": name})
        
        user = await db.fetch_one(text("SELECT id FROM users WHERE email = :e"), {"e": email})
        if user:
            user_id = user['id']
    
    # Create employee record
    await db.execute(text("""
        INSERT INTO employees(
            user_id, username, password_hash, role, department, 
            is_super_admin, active, created_at, created_by
        )
        VALUES (:uid, :u, :p, :r, :d, false, true, NOW(), :cb)
    """), {
        "uid": user_id,
        "u": username,
        "p": hash_password(password),
        "r": role,
        "d": department or role.replace("_", " ").title(),
        "cb": current_user['user_id']
    })
    
    return {
        "ok": True,
        "message": "Employee created successfully",
        "username": username,
        "role": role
    }

@router.get("/list")
async def list_employees(request: Request, current_user=Depends(get_current_user)):
    """List all employees (Super Admin only)"""
    db = request.app.state.db
    
    # Verify super admin
    employee_check = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee_check or not employee_check['is_super_admin']:
        raise HTTPException(403, "Only super admin can view employees")
    
    employees = await db.fetch_all(text("""
        SELECT 
            e.id, e.username, e.role, e.department, e.active,
            e.created_at, e.last_login, e.is_super_admin,
            u.email, u.name
        FROM employees e
        LEFT JOIN users u ON e.user_id = u.id
        ORDER BY e.is_super_admin DESC, e.created_at DESC
    """))
    
    return {
        "employees": [dict(emp) for emp in employees]
    }

@router.put("/{employee_id}/update")
async def update_employee(employee_id: int, payload: dict, request: Request, current_user=Depends(get_current_user)):
    """Update employee details (Super Admin only)"""
    db = request.app.state.db
    
    # Verify super admin
    employee_check = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee_check or not employee_check['is_super_admin']:
        raise HTTPException(403, "Only super admin can update employees")
    
    # Check if employee exists and is not super admin
    target_employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE id = :id
    """), {"id": employee_id})
    
    if not target_employee:
        raise HTTPException(404, "Employee not found")
    
    if target_employee['is_super_admin']:
        raise HTTPException(403, "Cannot modify super admin account")
    
    # Update fields
    updates = []
    params = {"id": employee_id}
    
    if "username" in payload:
        updates.append("username = :username")
        params["username"] = payload["username"]
    
    if "role" in payload:
        valid_roles = ["admin", "marketing", "customer_support", "accounting", "hr"]
        if payload["role"] not in valid_roles:
            raise HTTPException(400, f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        updates.append("role = :role")
        params["role"] = payload["role"]
    
    if "department" in payload:
        updates.append("department = :department")
        params["department"] = payload["department"]
    
    if "active" in payload:
        updates.append("active = :active")
        params["active"] = payload["active"]
    
    if not updates:
        raise HTTPException(400, "No fields to update")
    
    await db.execute(text(f"""
        UPDATE employees
        SET {', '.join(updates)}, updated_at = NOW()
        WHERE id = :id
    """), params)
    
    return {
        "ok": True,
        "message": "Employee updated successfully"
    }

@router.post("/{employee_id}/reset-password")
async def reset_employee_password(employee_id: int, payload: dict, request: Request, current_user=Depends(get_current_user)):
    """Reset employee password (Super Admin only)"""
    db = request.app.state.db
    
    # Verify super admin
    employee_check = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee_check or not employee_check['is_super_admin']:
        raise HTTPException(403, "Only super admin can reset passwords")
    
    new_password = payload.get("new_password")
    if not new_password:
        raise HTTPException(400, "New password required")
    
    # Check if employee exists and is not super admin
    target_employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE id = :id
    """), {"id": employee_id})
    
    if not target_employee:
        raise HTTPException(404, "Employee not found")
    
    if target_employee['is_super_admin']:
        raise HTTPException(403, "Cannot reset super admin password")
    
    # Update password
    await db.execute(text("""
        UPDATE employees
        SET password_hash = :p, updated_at = NOW()
        WHERE id = :id
    """), {
        "p": hash_password(new_password),
        "id": employee_id
    })
    
    return {
        "ok": True,
        "message": "Password reset successfully"
    }

@router.delete("/{employee_id}")
async def delete_employee(employee_id: int, request: Request, current_user=Depends(get_current_user)):
    """Delete employee (Super Admin only)"""
    db = request.app.state.db
    
    # Verify super admin
    employee_check = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee_check or not employee_check['is_super_admin']:
        raise HTTPException(403, "Only super admin can delete employees")
    
    # Check if employee exists and is not super admin
    target_employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE id = :id
    """), {"id": employee_id})
    
    if not target_employee:
        raise HTTPException(404, "Employee not found")
    
    if target_employee['is_super_admin']:
        raise HTTPException(403, "Cannot delete super admin account")
    
    # Soft delete (deactivate)
    await db.execute(text("""
        UPDATE employees
        SET active = false, updated_at = NOW()
        WHERE id = :id
    """), {"id": employee_id})
    
    return {
        "ok": True,
        "message": "Employee deleted successfully"
    }

@router.put("/super-admin/change-username")
async def change_super_admin_username(payload: dict, request: Request, current_user=Depends(get_current_user)):
    """Change super admin username (Super Admin only)"""
    db = request.app.state.db
    
    # Verify super admin
    employee_check = await db.fetch_one(text("""
        SELECT id, is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee_check or not employee_check['is_super_admin']:
        raise HTTPException(403, "Only super admin can change their username")
    
    new_username = payload.get("new_username")
    if not new_username:
        raise HTTPException(400, "New username required")
    
    # Check if username already exists
    existing = await db.fetch_one(text("""
        SELECT id FROM employees WHERE username = :u AND id != :id
    """), {"u": new_username, "id": employee_check['id']})
    
    if existing:
        raise HTTPException(400, "Username already exists")
    
    # Update username
    await db.execute(text("""
        UPDATE employees
        SET username = :u, updated_at = NOW()
        WHERE id = :id
    """), {
        "u": new_username,
        "id": employee_check['id']
    })
    
    return {
        "ok": True,
        "message": "Username changed successfully",
        "new_username": new_username
    }

