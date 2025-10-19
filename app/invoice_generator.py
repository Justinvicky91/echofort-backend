"""Invoice generator"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

class InvoiceCreate(BaseModel):
    email: str
    plan: str
    amount: float

@router.post("/generate")
async def gen_invoice(request: Request, inv: InvoiceCreate):
    num = f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    await request.app.state.db.execute("""
        INSERT INTO invoices (invoice_number, user_email, plan, amount, invoice_data)
        VALUES (:num, :email, :plan, :amt, :data)
    """, {"num": num, "email": inv.email, "plan": inv.plan, "amt": inv.amount, "data": f"Invoice {num}"})
    return {"invoice_number": num}
