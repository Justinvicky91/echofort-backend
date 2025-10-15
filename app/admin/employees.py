from fastapi import APIRouter, Request, Depends
from sqlalchemy import text
from ..rbac import guard_admin

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
