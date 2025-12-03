"""
Invoice Management API
Provides endpoints for viewing and downloading invoices
"""
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy import text
from typing import Optional
import os

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])


@router.get("/list")
async def list_invoices(request: Request, limit: int = 100, offset: int = 0):
    """
    Get list of all invoices
    """
    try:
        db = request.app.state.db
        
        query = text("""
            SELECT 
                i.id,
                i.invoice_number,
                i.user_id,
                i.razorpay_order_id,
                i.razorpay_payment_id,
                i.amount,
                i.currency,
                i.status,
                i.is_internal_test,
                i.created_at,
                i.pdf_url,
                u.name as user_name,
                u.email as user_email
            FROM invoices i
            LEFT JOIN users u ON i.user_id = u.user_id
            ORDER BY i.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        results = (await db.execute(query, {"limit": limit, "offset": offset})).fetchall()
        
        invoices = []
        for row in results:
            invoices.append({
                "id": row[0],
                "invoice_number": row[1],
                "user_id": row[2],
                "order_id": row[3],
                "payment_id": row[4],
                "amount": row[5],
                "currency": row[6],
                "status": row[7],
                "is_internal_test": row[8],
                "created_at": row[9].isoformat() if row[9] else None,
                "pdf_url": row[10],
                "user_name": row[11],
                "user_email": row[12]
            })
        
        return {
            "ok": True,
            "invoices": invoices,
            "total": len(invoices)
        }
    
    except Exception as e:
        print(f"❌ Error fetching invoices: {str(e)}")
        raise HTTPException(500, f"Failed to fetch invoices: {str(e)}")


@router.get("/{invoice_id}")
async def get_invoice(request: Request, invoice_id: int):
    """
    Get single invoice details
    """
    try:
        db = request.app.state.db
        
        query = text("""
            SELECT 
                i.id,
                i.invoice_number,
                i.user_id,
                i.razorpay_order_id,
                i.razorpay_payment_id,
                i.amount,
                i.currency,
                i.status,
                i.is_internal_test,
                i.invoice_html,
                i.pdf_url,
                i.created_at,
                u.name as user_name,
                u.email as user_email
            FROM invoices i
            LEFT JOIN users u ON i.user_id = u.user_id
            WHERE i.id = :invoice_id
        """)
        
        result = (await db.execute(query, {"invoice_id": invoice_id})).fetchone()
        
        if not result:
            raise HTTPException(404, "Invoice not found")
        
        return {
            "ok": True,
            "invoice": {
                "id": result[0],
                "invoice_number": result[1],
                "user_id": result[2],
                "order_id": result[3],
                "payment_id": result[4],
                "amount": result[5],
                "currency": result[6],
                "status": result[7],
                "is_internal_test": result[8],
                "html_content": result[9],
                "pdf_url": result[10],
                "created_at": result[11].isoformat() if result[11] else None,
                "user_name": result[12],
                "user_email": result[13]
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching invoice: {str(e)}")
        raise HTTPException(500, f"Failed to fetch invoice: {str(e)}")


@router.get("/{invoice_id}/download")
async def download_invoice(request: Request, invoice_id: int):
    """
    Download invoice PDF
    """
    try:
        db = request.app.state.db
        
        # Get invoice details
        query = text("""
            SELECT invoice_number, pdf_url, invoice_html
            FROM invoices
            WHERE id = :invoice_id
        """)
        
        result = (await db.execute(query, {"invoice_id": invoice_id})).fetchone()
        
        if not result:
            raise HTTPException(404, "Invoice not found")
        
        invoice_number = result[0]
        pdf_url = result[1]
        html_content = result[2]
        
        # Check if PDF exists
        if pdf_url:
            pdf_path = pdf_url.replace("https://api.echofort.ai/invoices/", "/tmp/invoices/")
            if os.path.exists(pdf_path):
                return FileResponse(
                    pdf_path,
                    media_type="application/pdf",
                    filename=f"{invoice_number}.pdf"
                )
        
        # If no PDF, generate on-the-fly from HTML
        if html_content:
            from .invoice_generator import convert_html_to_pdf
            
            pdf_dir = "/tmp/invoices"
            os.makedirs(pdf_dir, exist_ok=True)
            pdf_path = f"{pdf_dir}/{invoice_number}.pdf"
            
            success = await convert_html_to_pdf(html_content, pdf_path)
            
            if success and os.path.exists(pdf_path):
                return FileResponse(
                    pdf_path,
                    media_type="application/pdf",
                    filename=f"{invoice_number}.pdf"
                )
        
        raise HTTPException(404, "Invoice PDF not available")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error downloading invoice: {str(e)}")
        raise HTTPException(500, f"Failed to download invoice: {str(e)}")


@router.get("/{invoice_id}/html")
async def get_invoice_html(request: Request, invoice_id: int):
    """
    Get invoice HTML for preview
    """
    try:
        db = request.app.state.db
        
        query = text("""
            SELECT invoice_html
            FROM invoices
            WHERE id = :invoice_id
        """)
        
        result = (await db.execute(query, {"invoice_id": invoice_id})).fetchone()
        
        if not result or not result[0]:
            raise HTTPException(404, "Invoice HTML not found")
        
        return Response(content=result[0], media_type="text/html")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching invoice HTML: {str(e)}")
        raise HTTPException(500, f"Failed to fetch invoice HTML: {str(e)}")
