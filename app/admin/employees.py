from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import text
from ..rbac import guard_admin
from pydantic import BaseModel
import bcrypt

router = APIRouter(prefix="/admin/employees", tags=["admin"])

@router.post("/", dependencies=[Depends(guard_admin)])
async def create_emp(request: Request, payload: dict):
    q = text("INSERT INTO employees(email,name,role,active) VALUES(:e,:n,:r,TRUE)")
    await request.app.state.db.execute(q, {"e": payload["email"], "n": payload["name"], "r": payload["role"]})
    return {"ok": True}

@router.get("/", dependencies=[Depends(guard_admin)])
async def list_emp(request: Request):
    rows = (await request.app.state.db.execute(text("SELECT * FROM employees ORDER BY id DESC"))).fetchall()
    return {"items": [dict(r._mapping) for r in rows]}

@router.patch("/{emp_id}", dependencies=[Depends(guard_admin)])
async def update_emp(emp_id: int, request: Request, payload: dict):
    await request.app.state.db.execute(text(
      "UPDATE employees SET name=COALESCE(:n,name), role=COALESCE(:r,role), active=COALESCE(:a,active) WHERE id=:id"
    ), {"n": payload.get("name"), "r": payload.get("role"), "a": payload.get("active"), "id": emp_id})
    return {"ok": True}

@router.delete("/{emp_id}", dependencies=[Depends(guard_admin)])
async def delete_emp(emp_id: int, request: Request):
    """Delete an employee"""
    try:
        # Check if employee exists
        check = await request.app.state.db.execute(
            text("SELECT id FROM employees WHERE id=:id"),
            {"id": emp_id}
        )
        if not check.fetchone():
            raise HTTPException(404, "Employee not found")
        
        # Delete employee
        await request.app.state.db.execute(
            text("DELETE FROM employees WHERE id=:id"),
            {"id": emp_id}
        )
        return {"ok": True, "message": "Employee deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to delete employee: {str(e)}")

class ResetPasswordPayload(BaseModel):
    new_password: str

@router.post("/{emp_id}/reset-password", dependencies=[Depends(guard_admin)])
async def reset_employee_password(emp_id: int, request: Request, payload: ResetPasswordPayload):
    """Reset employee password"""
    try:
        # Check if employee exists
        check = await request.app.state.db.execute(
            text("SELECT id FROM employees WHERE id=:id"),
            {"id": emp_id}
        )
        if not check.fetchone():
            raise HTTPException(404, "Employee not found")
        
        # Hash the new password
        hashed = bcrypt.hashpw(payload.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Update password
        await request.app.state.db.execute(
            text("UPDATE employees SET password_hash=:pwd WHERE id=:id"),
            {"pwd": hashed, "id": emp_id}
        )
        return {"ok": True, "message": "Password reset successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to reset password: {str(e)}")
