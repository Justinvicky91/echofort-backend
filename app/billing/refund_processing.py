"""
Refund Processing Module
Handles 24-hour refund policy with Razorpay integration
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy import text
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
import os
import razorpay

router = APIRouter(prefix="/billing/refund", tags=["Refunds"])

# Initialize Razorpay client
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_live_RaVY92nlBc6XrE')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', 'Byz4CcXbUnustnAKgU3EprCy')

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


class RefundRequest(BaseModel):
    razorpay_payment_id: str
    reason: Optional[str] = None


class RefundApproval(BaseModel):
    refund_request_id: int
    approved: bool
    admin_notes: Optional[str] = None


async def get_payment_details(request: Request, payment_id: str) -> dict:
    """
    Get payment details from invoices table
    """
    db = request.app.state.db
    
    result = await db.execute(text("""
        SELECT 
            invoice_id, user_id, amount, razorpay_payment_id, 
            razorpay_order_id, customer_name, customer_email, 
            customer_phone, created_at
        FROM invoices
        WHERE razorpay_payment_id = :payment_id
    """), {'payment_id': payment_id})
    
    invoice = result.fetchone()
    
    if not invoice:
        raise HTTPException(404, "Payment not found")
    
    return {
        'invoice_id': invoice[0],
        'user_id': invoice[1],
        'amount': invoice[2],
        'razorpay_payment_id': invoice[3],
        'razorpay_order_id': invoice[4],
        'customer_name': invoice[5],
        'customer_email': invoice[6],
        'customer_phone': invoice[7],
        'payment_date': invoice[8]
    }


async def check_24_hour_window(payment_date: datetime) -> tuple[bool, Decimal]:
    """
    Check if refund request is within 24-hour window
    Returns: (within_24_hours, hours_since_payment)
    """
    now = datetime.now()
    time_diff = now - payment_date
    hours_since_payment = Decimal(time_diff.total_seconds() / 3600)
    within_24_hours = hours_since_payment <= 24
    
    return within_24_hours, hours_since_payment


async def process_razorpay_refund(payment_id: str, amount: Decimal) -> dict:
    """
    Process refund via Razorpay API
    Returns: refund details
    """
    try:
        # Convert amount to paise
        amount_paise = int(amount * 100)
        
        # Create refund
        refund = razorpay_client.payment.refund(payment_id, {
            'amount': amount_paise,
            'speed': 'normal',  # normal or optimum
            'notes': {
                'reason': '24-hour refund policy',
                'processed_by': 'EchoFort System'
            }
        })
        
        return {
            'refund_id': refund['id'],
            'status': refund['status'],
            'amount': Decimal(refund['amount']) / 100,
            'speed': refund.get('speed', 'normal')
        }
        
    except razorpay.errors.BadRequestError as e:
        raise HTTPException(400, f"Razorpay refund failed: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Refund processing error: {str(e)}")


@router.post("/request")
async def request_refund(payload: RefundRequest, request: Request):
    """
    Request a refund (user-facing endpoint)
    Validates 24-hour window and creates refund request
    """
    db = request.app.state.db
    
    # TODO: Get user_id from JWT token
    # For now, get from payment details
    
    # Get payment details
    payment = await get_payment_details(request, payload.razorpay_payment_id)
    
    # Check if refund already requested
    existing = await db.execute(text("""
        SELECT id, status FROM refund_requests
        WHERE razorpay_payment_id = :payment_id
    """), {'payment_id': payload.razorpay_payment_id})
    
    existing_refund = existing.fetchone()
    
    if existing_refund:
        status = existing_refund[1]
        if status in ['pending', 'approved', 'processed']:
            raise HTTPException(400, f"Refund already {status}")
    
    # Check 24-hour window
    within_24_hours, hours_since_payment = await check_24_hour_window(payment['payment_date'])
    
    if not within_24_hours:
        raise HTTPException(400, 
            f"Refund window expired. Refunds are only allowed within 24 hours of purchase. "
            f"Your payment was {hours_since_payment:.1f} hours ago."
        )
    
    # Create refund request
    result = await db.execute(text("""
        INSERT INTO refund_requests (
            user_id, invoice_id, razorpay_payment_id, razorpay_order_id,
            amount, reason, payment_date, customer_name, customer_email, customer_phone
        ) VALUES (
            :user_id, :invoice_id, :payment_id, :order_id,
            :amount, :reason, :payment_date, :customer_name, :customer_email, :customer_phone
        )
        RETURNING id, status, hours_since_payment, within_24_hours, request_date
    """), {
        'user_id': payment['user_id'],
        'invoice_id': payment['invoice_id'],
        'payment_id': payload.razorpay_payment_id,
        'order_id': payment['razorpay_order_id'],
        'amount': payment['amount'],
        'reason': payload.reason,
        'payment_date': payment['payment_date'],
        'customer_name': payment['customer_name'],
        'customer_email': payment['customer_email'],
        'customer_phone': payment['customer_phone']
    })
    
    refund_request = result.fetchone()
    
    return {
        'ok': True,
        'message': 'Refund request submitted successfully',
        'refund_request_id': refund_request[0],
        'status': refund_request[1],
        'hours_since_payment': float(refund_request[2]),
        'within_24_hours': refund_request[3],
        'request_date': refund_request[4].isoformat(),
        'note': 'Your refund will be processed within 5-7 business days'
    }


@router.post("/approve")
async def approve_refund(payload: RefundApproval, request: Request):
    """
    Approve/reject refund request (admin endpoint)
    If approved, processes refund via Razorpay
    """
    db = request.app.state.db
    
    # TODO: Verify admin authentication
    # For now, allow any authenticated user
    
    # Get refund request
    result = await db.execute(text("""
        SELECT 
            razorpay_payment_id, amount, status, within_24_hours,
            customer_email, customer_name
        FROM refund_requests
        WHERE id = :id
    """), {'id': payload.refund_request_id})
    
    refund_req = result.fetchone()
    
    if not refund_req:
        raise HTTPException(404, "Refund request not found")
    
    payment_id, amount, status, within_24_hours, customer_email, customer_name = refund_req
    
    if status != 'pending':
        raise HTTPException(400, f"Refund request already {status}")
    
    if not within_24_hours:
        raise HTTPException(400, "Refund request is outside 24-hour window")
    
    if not payload.approved:
        # Reject refund
        await db.execute(text("""
            UPDATE refund_requests
            SET status = 'rejected',
                processed_date = NOW(),
                admin_notes = :notes
            WHERE id = :id
        """), {
            'id': payload.refund_request_id,
            'notes': payload.admin_notes
        })
        
        return {
            'ok': True,
            'message': 'Refund request rejected',
            'status': 'rejected'
        }
    
    # Approve and process refund
    try:
        # Process refund via Razorpay
        refund_details = await process_razorpay_refund(payment_id, Decimal(amount))
        
        # Update refund request
        await db.execute(text("""
            UPDATE refund_requests
            SET status = 'processed',
                processed_date = NOW(),
                razorpay_refund_id = :refund_id,
                refund_status = :refund_status,
                refund_speed = :refund_speed,
                admin_notes = :notes
            WHERE id = :id
        """), {
            'id': payload.refund_request_id,
            'refund_id': refund_details['refund_id'],
            'refund_status': refund_details['status'],
            'refund_speed': refund_details['speed'],
            'notes': payload.admin_notes
        })
        
        # TODO: Send refund confirmation email to customer
        
        return {
            'ok': True,
            'message': 'Refund processed successfully',
            'status': 'processed',
            'refund_id': refund_details['refund_id'],
            'amount': float(refund_details['amount']),
            'note': 'Refund will be credited to customer account in 5-7 business days'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Mark as failed
        await db.execute(text("""
            UPDATE refund_requests
            SET status = 'failed',
                processed_date = NOW(),
                admin_notes = :notes
            WHERE id = :id
        """), {
            'id': payload.refund_request_id,
            'notes': f"Refund failed: {str(e)}"
        })
        
        raise HTTPException(500, f"Refund processing failed: {str(e)}")


@router.get("/status/{refund_request_id}")
async def get_refund_status(refund_request_id: int, request: Request):
    """
    Get refund request status
    """
    db = request.app.state.db
    
    result = await db.execute(text("""
        SELECT 
            id, status, amount, reason, hours_since_payment, within_24_hours,
            request_date, processed_date, razorpay_refund_id, refund_status
        FROM refund_requests
        WHERE id = :id
    """), {'id': refund_request_id})
    
    refund = result.fetchone()
    
    if not refund:
        raise HTTPException(404, "Refund request not found")
    
    return {
        'ok': True,
        'refund_request_id': refund[0],
        'status': refund[1],
        'amount': float(refund[2]),
        'reason': refund[3],
        'hours_since_payment': float(refund[4]) if refund[4] else None,
        'within_24_hours': refund[5],
        'request_date': refund[6].isoformat() if refund[6] else None,
        'processed_date': refund[7].isoformat() if refund[7] else None,
        'razorpay_refund_id': refund[8],
        'refund_status': refund[9]
    }


@router.get("/list")
async def list_refund_requests(request: Request, status: Optional[str] = None):
    """
    List refund requests (admin endpoint)
    """
    db = request.app.state.db
    
    # TODO: Verify admin authentication
    
    query = """
        SELECT 
            id, user_id, invoice_id, amount, status, reason,
            hours_since_payment, within_24_hours, customer_name, customer_email,
            request_date, processed_date
        FROM refund_requests
    """
    
    params = {}
    
    if status:
        query += " WHERE status = :status"
        params['status'] = status
    
    query += " ORDER BY request_date DESC LIMIT 100"
    
    result = await db.execute(text(query), params)
    
    refunds = []
    for row in result.fetchall():
        refunds.append({
            'id': row[0],
            'user_id': row[1],
            'invoice_id': row[2],
            'amount': float(row[3]),
            'status': row[4],
            'reason': row[5],
            'hours_since_payment': float(row[6]) if row[6] else None,
            'within_24_hours': row[7],
            'customer_name': row[8],
            'customer_email': row[9],
            'request_date': row[10].isoformat() if row[10] else None,
            'processed_date': row[11].isoformat() if row[11] else None
        })
    
    return {
        'ok': True,
        'refunds': refunds,
        'count': len(refunds)
    }


@router.get("/check/{razorpay_payment_id}")
async def check_refund_eligibility(razorpay_payment_id: str, request: Request):
    """
    Check if payment is eligible for refund (within 24 hours)
    """
    # Get payment details
    payment = await get_payment_details(request, razorpay_payment_id)
    
    # Check 24-hour window
    within_24_hours, hours_since_payment = await check_24_hour_window(payment['payment_date'])
    
    hours_remaining = 24 - float(hours_since_payment)
    
    return {
        'ok': True,
        'eligible': within_24_hours,
        'payment_id': razorpay_payment_id,
        'payment_date': payment['payment_date'].isoformat(),
        'hours_since_payment': float(hours_since_payment),
        'hours_remaining': max(0, hours_remaining),
        'message': 'Refund available' if within_24_hours else 'Refund window expired',
        'amount': float(payment['amount'])
    }
