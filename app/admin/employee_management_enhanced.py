from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from typing import Optional
from ..utils import is_admin

router = APIRouter(prefix="/admin/employees", tags=["admin-employees"])

class EmployeeAssignment(BaseModel):
    employee_id: int
    role_id: int

@router.get("/roles")
async def get_employee_roles(request: Request, user_id: int = None):
    """Get all employee roles"""
    # Super Admin can access without user_id
    if user_id and not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    rows = (await request.app.state.db.execute(text("""
        SELECT * FROM employee_roles ORDER BY role_name
    """))).fetchall()
    
    return {"ok": True, "roles": [dict(r._mapping) for r in rows]}

@router.get("/")
async def get_all_employees(
    user_id: int,
    request: Request,
    role_id: Optional[int] = None,
    is_active: Optional[bool] = None
):
    """Get all employees with their roles"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    query = """
        SELECT 
            u.id,
            u.username,
            u.email,
            u.full_name,
            u.phone,
            ea.role_id,
            er.role_name,
            er.role_description,
            ea.assigned_at,
            ea.is_active
        FROM users u
        JOIN employee_assignments ea ON u.id = ea.employee_id
        JOIN employee_roles er ON ea.role_id = er.id
        WHERE 1=1
    """
    
    params = {}
    
    if role_id:
        query += " AND ea.role_id = :role_id"
        params['role_id'] = role_id
    
    if is_active is not None:
        query += " AND ea.is_active = :is_active"
        params['is_active'] = is_active
    
    query += " ORDER BY u.username"
    
    rows = (await request.app.state.db.execute(text(query), params)).fetchall()
    
    return {"ok": True, "employees": [dict(r._mapping) for r in rows]}

@router.post("/assign")
async def assign_employee_role(
    user_id: int,
    request: Request,
    assignment: EmployeeAssignment
):
    """Assign a role to an employee"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    await request.app.state.db.execute(text("""
        INSERT INTO employee_assignments (employee_id, role_id, assigned_by, is_active)
        VALUES (:employee_id, :role_id, :assigned_by, TRUE)
        ON CONFLICT (employee_id, role_id) 
        DO UPDATE SET is_active = TRUE, assigned_by = :assigned_by, assigned_at = CURRENT_TIMESTAMP
    """), {
        "employee_id": assignment.employee_id,
        "role_id": assignment.role_id,
        "assigned_by": user_id
    })
    await request.app.state.db.commit()
    
    return {"ok": True, "message": "Employee role assigned successfully"}

@router.delete("/assign/{employee_id}/{role_id}")
async def remove_employee_role(
    user_id: int,
    employee_id: int,
    role_id: int,
    request: Request
):
    """Remove a role from an employee"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    await request.app.state.db.execute(text("""
        UPDATE employee_assignments
        SET is_active = FALSE
        WHERE employee_id = :employee_id AND role_id = :role_id
    """), {"employee_id": employee_id, "role_id": role_id})
    await request.app.state.db.commit()
    
    return {"ok": True, "message": "Employee role removed successfully"}

@router.get("/verification-queue")
async def get_verification_queue(
    user_id: int,
    request: Request,
    status: Optional[str] = None,
    assigned_to: Optional[int] = None,
    limit: int = 100
):
    """Get evidence verification queue"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    query = """
        SELECT 
            evq.*,
            u.username as submitter_username,
            u.email as submitter_email,
            u.full_name as submitter_name,
            e.username as assigned_to_username
        FROM evidence_verification_queue evq
        JOIN users u ON evq.submitted_by = u.id
        LEFT JOIN users e ON evq.assigned_to = e.id
        WHERE 1=1
    """
    
    params = {}
    
    if status:
        query += " AND evq.status = :status"
        params['status'] = status
    
    if assigned_to:
        query += " AND evq.assigned_to = :assigned_to"
        params['assigned_to'] = assigned_to
    
    query += " ORDER BY evq.priority DESC, evq.submitted_at ASC LIMIT :limit"
    params['limit'] = limit
    
    rows = (await request.app.state.db.execute(text(query), params)).fetchall()
    
    return {"ok": True, "queue": [dict(r._mapping) for r in rows]}

@router.post("/verification-queue/{queue_id}/assign")
async def assign_verification_task(
    user_id: int,
    queue_id: int,
    request: Request,
    employee_id: int
):
    """Assign evidence verification task to employee"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    await request.app.state.db.execute(text("""
        UPDATE evidence_verification_queue
        SET assigned_to = :employee_id,
            assigned_at = CURRENT_TIMESTAMP,
            status = 'in_review'
        WHERE id = :queue_id
    """), {"employee_id": employee_id, "queue_id": queue_id})
    await request.app.state.db.commit()
    
    return {"ok": True, "message": "Task assigned successfully"}

@router.get("/performance")
async def get_employee_performance(
    user_id: int,
    request: Request,
    employee_id: Optional[int] = None,
    days: int = 30
):
    """Get employee performance metrics"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    query = """
        SELECT 
            ep.*,
            u.username,
            u.email,
            u.full_name
        FROM employee_performance ep
        JOIN users u ON ep.employee_id = u.id
        WHERE ep.date >= CURRENT_DATE - INTERVAL ':days days'
    """
    
    params = {"days": days}
    
    if employee_id:
        query += " AND ep.employee_id = :employee_id"
        params['employee_id'] = employee_id
    
    query += " ORDER BY ep.date DESC"
    
    rows = (await request.app.state.db.execute(text(query), params)).fetchall()
    
    return {"ok": True, "performance": [dict(r._mapping) for r in rows]}

@router.get("/stats")
async def get_employee_stats(user_id: int, request: Request):
    """Get employee statistics overview"""
    if not is_admin(user_id):
        raise HTTPException(403, "Not authorized")
    
    stats = {}
    
    # Total employees
    total = (await request.app.state.db.execute(text("""
        SELECT COUNT(DISTINCT employee_id) as count
        FROM employee_assignments
        WHERE is_active = TRUE
    """))).fetchone()
    stats['total_employees'] = total[0] if total else 0
    
    # Employees by role
    by_role = (await request.app.state.db.execute(text("""
        SELECT er.role_name, COUNT(*) as count
        FROM employee_assignments ea
        JOIN employee_roles er ON ea.role_id = er.id
        WHERE ea.is_active = TRUE
        GROUP BY er.role_name
    """))).fetchall()
    stats['by_role'] = [dict(r._mapping) for r in by_role]
    
    # Verification queue stats
    queue_stats = (await request.app.state.db.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'in_review' THEN 1 END) as in_review,
            COUNT(CASE WHEN status = 'verified' THEN 1 END) as verified,
            COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected
        FROM evidence_verification_queue
    """))).fetchone()
    stats['verification_queue'] = dict(queue_stats._mapping) if queue_stats else {}
    
    return {"ok": True, "stats": stats}
