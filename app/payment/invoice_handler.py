"""
Invoice Handler for Payment Processing
Handles invoice generation, storage, and email delivery
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import os
from ..database import get_db
from ..invoices.invoice_generator import invoice_generator
from ..email_service import send_email
from ..auth.simple_login import get_current_user

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.post("/generate-subscription-invoice")
async def generate_subscription_invoice(
    order_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate invoice for subscription purchase"""
    try:
        # Get order details from database
        order = db.execute(
            "SELECT * FROM orders WHERE id = :order_id AND user_id = :user_id",
            {"order_id": order_id, "user_id": current_user.id}
        ).fetchone()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Generate invoice number
        invoice_number = f"ECF{datetime.now().strftime('%Y%m%d')}{order_id[-6:]}"
        
        # Prepare invoice data
        invoice_data = {
            "invoice_number": invoice_number,
            "customer_name": current_user.name,
            "customer_email": current_user.email,
            "customer_phone": current_user.phone or "N/A",
            "plan_name": order['plan_name'],
            "billing_cycle": order['billing_cycle'],
            "base_amount": order['amount'] / 1.18,  # Remove GST to get base
            "payment_method": order['payment_method'],
            "transaction_id": order['transaction_id']
        }
        
        # Generate PDF
        invoice_path = invoice_generator.generate_subscription_invoice(invoice_data)
        
        # Save invoice record to database
        db.execute("""
            INSERT INTO invoices (
                invoice_number, user_id, order_id, amount, 
                gst_amount, total_amount, invoice_path, created_at
            ) VALUES (
                :invoice_number, :user_id, :order_id, :amount,
                :gst_amount, :total_amount, :invoice_path, :created_at
            )
        """, {
            "invoice_number": invoice_number,
            "user_id": current_user.id,
            "order_id": order_id,
            "amount": invoice_data['base_amount'],
            "gst_amount": invoice_data['base_amount'] * 0.18,
            "total_amount": order['amount'],
            "invoice_path": invoice_path,
            "created_at": datetime.now()
        })
        db.commit()
        
        # Send invoice via email
        with open(invoice_path, 'rb') as f:
            invoice_content = f.read()
        
        send_email(
            to_email=current_user.email,
            subject=f"EchoFort Invoice - {invoice_number}",
            body=f"""
            Dear {current_user.name},
            
            Thank you for subscribing to EchoFort {invoice_data['plan_name']} Plan!
            
            Your invoice is attached to this email.
            
            Invoice Number: {invoice_number}
            Amount Paid: ₹{order['amount']:,.2f} (including GST)
            
            Your subscription is now active and your family is protected.
            
            Best regards,
            EchoFort Team
            """,
            attachments=[{
                "filename": f"invoice_{invoice_number}.pdf",
                "content": invoice_content
            }]
        )
        
        # Also send to admin@echofort.ai
        send_email(
            to_email="admin@echofort.ai",
            subject=f"New Subscription - {invoice_number}",
            body=f"""
            New subscription received:
            
            Customer: {current_user.name} ({current_user.email})
            Plan: {invoice_data['plan_name']}
            Amount: ₹{order['amount']:,.2f}
            Invoice: {invoice_number}
            """,
            attachments=[{
                "filename": f"invoice_{invoice_number}.pdf",
                "content": invoice_content
            }]
        )
        
        return {
            "success": True,
            "invoice_number": invoice_number,
            "invoice_url": f"/api/invoices/download/{invoice_number}",
            "message": "Invoice generated and sent to your email"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-refund-invoice")
async def generate_refund_invoice(
    refund_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate refund invoice"""
    try:
        # Get refund details
        refund = db.execute(
            "SELECT * FROM refunds WHERE id = :refund_id AND user_id = :user_id",
            {"refund_id": refund_id, "user_id": current_user.id}
        ).fetchone()
        
        if not refund:
            raise HTTPException(status_code=404, detail="Refund not found")
        
        # Generate refund invoice number
        refund_number = f"REF{datetime.now().strftime('%Y%m%d')}{refund_id[-6:]}"
        
        # Prepare refund invoice data
        refund_data = {
            "refund_number": refund_number,
            "original_invoice": refund['original_invoice_number'],
            "customer_name": current_user.name,
            "customer_email": current_user.email,
            "customer_phone": current_user.phone or "N/A",
            "plan_name": refund['plan_name'],
            "refund_amount": refund['refund_amount'],
            "reason": refund.get('reason', 'Customer requested refund'),
            "refund_method": refund['refund_method'],
            "refund_transaction_id": refund['refund_transaction_id']
        }
        
        # Generate PDF
        refund_invoice_path = invoice_generator.generate_refund_invoice(refund_data)
        
        # Save refund invoice record
        db.execute("""
            INSERT INTO refund_invoices (
                refund_invoice_number, user_id, refund_id, refund_amount,
                invoice_path, created_at
            ) VALUES (
                :refund_number, :user_id, :refund_id, :refund_amount,
                :invoice_path, :created_at
            )
        """, {
            "refund_number": refund_number,
            "user_id": current_user.id,
            "refund_id": refund_id,
            "refund_amount": refund['refund_amount'],
            "invoice_path": refund_invoice_path,
            "created_at": datetime.now()
        })
        db.commit()
        
        # Send refund invoice via email
        with open(refund_invoice_path, 'rb') as f:
            refund_invoice_content = f.read()
        
        send_email(
            to_email=current_user.email,
            subject=f"EchoFort Refund Invoice - {refund_number}",
            body=f"""
            Dear {current_user.name},
            
            Your refund has been processed successfully.
            
            Refund Invoice Number: {refund_number}
            Refund Amount: ₹{refund['refund_amount']:,.2f}
            
            The amount will be credited to your account within 5-7 business days.
            
            We're sorry to see you go. Feel free to return anytime!
            
            Best regards,
            EchoFort Team
            """,
            attachments=[{
                "filename": f"refund_invoice_{refund_number}.pdf",
                "content": refund_invoice_content
            }]
        )
        
        # Notify admin
        send_email(
            to_email="admin@echofort.ai",
            subject=f"Refund Processed - {refund_number}",
            body=f"""
            Refund processed:
            
            Customer: {current_user.name} ({current_user.email})
            Amount: ₹{refund['refund_amount']:,.2f}
            Refund Invoice: {refund_number}
            Reason: {refund_data['reason']}
            """,
            attachments=[{
                "filename": f"refund_invoice_{refund_number}.pdf",
                "content": refund_invoice_content
            }]
        )
        
        return {
            "success": True,
            "refund_invoice_number": refund_number,
            "refund_invoice_url": f"/api/invoices/download/{refund_number}",
            "message": "Refund invoice generated and sent to your email"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{invoice_number}")
async def download_invoice(
    invoice_number: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download invoice PDF"""
    try:
        # Check if it's a regular invoice or refund invoice
        if invoice_number.startswith("REF"):
            invoice = db.execute(
                "SELECT * FROM refund_invoices WHERE refund_invoice_number = :number AND user_id = :user_id",
                {"number": invoice_number, "user_id": current_user.id}
            ).fetchone()
        else:
            invoice = db.execute(
                "SELECT * FROM invoices WHERE invoice_number = :number AND user_id = :user_id",
                {"number": invoice_number, "user_id": current_user.id}
            ).fetchone()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        invoice_path = invoice['invoice_path']
        
        if not os.path.exists(invoice_path):
            raise HTTPException(status_code=404, detail="Invoice file not found")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            invoice_path,
            media_type="application/pdf",
            filename=f"{invoice_number}.pdf"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_invoices(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all invoices for current user"""
    try:
        # Get regular invoices
        invoices = db.execute(
            "SELECT * FROM invoices WHERE user_id = :user_id ORDER BY created_at DESC",
            {"user_id": current_user.id}
        ).fetchall()
        
        # Get refund invoices
        refund_invoices = db.execute(
            "SELECT * FROM refund_invoices WHERE user_id = :user_id ORDER BY created_at DESC",
            {"user_id": current_user.id}
        ).fetchall()
        
        return {
            "invoices": [dict(inv) for inv in invoices],
            "refund_invoices": [dict(inv) for inv in refund_invoices]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

