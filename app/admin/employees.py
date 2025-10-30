from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import text
from pydantic import BaseModel
import bcrypt
from ..auth.jwt_utils import get_current_user

router = APIRouter(prefix="/admin/employees", tags=["admin"])

class ResetPasswordPayload(BaseModel):
    new_password: str

@router.post("/", dependencies=[Depends(get_current_user)])
async def create_emp(request: Request, payload: dict, current_user=Depends(get_current_user)):
    """Create new employee (Super Admin only)"""
    try:
        # Verify super admin
        user_type = current_user.get("user_type")
        role = current_user.get("role")
        
        if user_type != "super_admin" and role != "super_admin":
            raise HTTPException(403, "Only super admin can create employees")
        
        db = request.app.state.db
        
        # Hash password if provided
        password = payload.get("password", "")
        if password:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            # Generate random password if not provided
            import secrets
            temp_password = secrets.token_urlsafe(12)
            password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insert employee
        await db.execute(text("""
            INSERT INTO employees(
                username, password_hash, email, name, role, department, active, created_at
            ) VALUES (
                :username, :password, :email, :name, :role, :dept, true, NOW()
            )
        """), {
            "username": payload.get("username"),
            "password": password_hash,
            "email": payload.get("email"),
            "name": payload.get("name"),
            "role": payload.get("role"),
            "dept": payload.get("department")
        })
        
        return {"ok": True, "message": "Employee created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to create employee: {str(e)}")

@router.get("/", dependencies=[Depends(get_current_user)])
async def list_emp(request: Request, current_user=Depends(get_current_user)):
    """List all employees"""
    try:
        db = request.app.state.db
        rows = (await db.execute(text("""
            SELECT id, username, email, name, role, department, active, created_at
            FROM employees 
            ORDER BY id DESC
        """))).fetchall()
        return {"items": [dict(r._mapping) for r in rows]}
    except Exception as e:
        raise HTTPException(500, f"Failed to list employees: {str(e)}")

@router.patch("/{emp_id}", dependencies=[Depends(get_current_user)])
async def update_emp(emp_id: int, request: Request, payload: dict, current_user=Depends(get_current_user)):
    """Update employee (Super Admin only)"""
    try:
        # Verify super admin
        user_type = current_user.get("user_type")
        role = current_user.get("role")
        
        if user_type != "super_admin" and role != "super_admin":
            raise HTTPException(403, "Only super admin can update employees")
        
        db = request.app.state.db
        
        # Check if employee exists
        check = await db.execute(
            text("SELECT id, is_super_admin FROM employees WHERE id=:id"),
            {"id": emp_id}
        )
        employee = check.fetchone()
        
        if not employee:
            raise HTTPException(404, "Employee not found")
        
        # Prevent modifying super admin
        if employee[1]:  # is_super_admin
            raise HTTPException(403, "Cannot modify super admin account")
        
        # Update employee
        await db.execute(text("""
            UPDATE employees 
            SET name=COALESCE(:n,name), 
                role=COALESCE(:r,role), 
                active=COALESCE(:a,active),
                department=COALESCE(:d,department),
                updated_at=NOW()
            WHERE id=:id
        """), {
            "n": payload.get("name"), 
            "r": payload.get("role"), 
            "a": payload.get("active"),
            "d": payload.get("department"),
            "id": emp_id
        })
        
        return {"ok": True, "message": "Employee updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update employee: {str(e)}")

@router.delete("/{emp_id}", dependencies=[Depends(get_current_user)])
async def delete_emp(emp_id: int, request: Request, current_user=Depends(get_current_user)):
    """Delete an employee (Super Admin only)"""
    try:
        # Verify super admin
        user_type = current_user.get("user_type")
        role = current_user.get("role")
        
        if user_type != "super_admin" and role != "super_admin":
            raise HTTPException(403, "Only super admin can delete employees")
        
        db = request.app.state.db
        
        # Check if employee exists
        check = await db.execute(
            text("SELECT id, is_super_admin FROM employees WHERE id=:id"),
            {"id": emp_id}
        )
        employee = check.fetchone()
        
        if not employee:
            raise HTTPException(404, "Employee not found")
        
        # Prevent deleting super admin
        if employee[1]:  # is_super_admin
            raise HTTPException(403, "Cannot delete super admin account")
        
        # Delete employee
        await db.execute(
            text("DELETE FROM employees WHERE id=:id"),
            {"id": emp_id}
        )
        return {"ok": True, "message": "Employee deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to delete employee: {str(e)}")

@router.post("/{emp_id}/reset-password", dependencies=[Depends(get_current_user)])
async def reset_employee_password(emp_id: int, request: Request, payload: ResetPasswordPayload, current_user=Depends(get_current_user)):
    """Reset employee password (Super Admin only)"""
    try:
        # Verify super admin
        user_type = current_user.get("user_type")
        role = current_user.get("role")
        
        if user_type != "super_admin" and role != "super_admin":
            raise HTTPException(403, "Only super admin can reset passwords")
        
        db = request.app.state.db
        
        # Check if employee exists
        check = await db.execute(
            text("SELECT id, is_super_admin FROM employees WHERE id=:id"),
            {"id": emp_id}
        )
        employee = check.fetchone()
        
        if not employee:
            raise HTTPException(404, "Employee not found")
        
        # Prevent resetting super admin password
        if employee[1]:  # is_super_admin
            raise HTTPException(403, "Cannot reset super admin password")
        
        # Hash the new password
        hashed = bcrypt.hashpw(payload.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Update password
        await db.execute(
            text("UPDATE employees SET password_hash=:pwd, updated_at=NOW() WHERE id=:id"),
            {"pwd": hashed, "id": emp_id}
        )
        return {"ok": True, "message": "Password reset successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to reset password: {str(e)}")
