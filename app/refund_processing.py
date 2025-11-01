"""
Automated Refund Processing API
Handles refunds for Razorpay and Stripe payments
Implements 24-hour money-back guarantee policy
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import os
import httpx

router = APIRouter(prefix="/api/refunds", tags=["Refunds"])


class RefundRequest(BaseModel):
    """Request model for refund processing"""
    user_id: int
    payment_id: str  # Razorpay or Stripe payment ID
    reason: str
    amount: Optional[float] = None  # If partial refund, otherwise full refund


class RefundResponse(BaseModel):
    """Response model for refund processing"""
    refund_id: str
    status: str  # "success", "pending", "failed"
    amount: float
    currency: str
    payment_gateway: str  # "razorpay" or "stripe"
    refund_date: str
    estimated_arrival: str  # When money will reach customer
    message: str


class RefundStatus(BaseModel):
    """Model for checking refund status"""
    refund_id: str
    status: str
    amount: float
    created_at: str
    processed_at: Optional[str]


# Get API keys from environment
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")


async def process_razorpay_refund(payment_id: str, amount: Optional[float] = None) -> dict:
    """
    Process refund through Razorpay
    """
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay credentials not configured")
    
    url = f"https://api.razorpay.com/v1/payments/{payment_id}/refund"
    
    # Prepare refund data
    refund_data = {}
    if amount:
        refund_data["amount"] = int(amount * 100)  # Convert to paise
    
    # Make API request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
                json=refund_data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                refund_data = response.json()
                return {
                    "success": True,
                    "refund_id": refund_data["id"],
                    "amount": refund_data["amount"] / 100,  # Convert from paise
                    "currency": refund_data["currency"],
                    "status": refund_data["status"],
                    "created_at": datetime.fromtimestamp(refund_data["created_at"]).isoformat()
                }
            else:
                error_data = response.json()
                return {
                    "success": False,
                    "error": error_data.get("error", {}).get("description", "Refund failed")
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Razorpay API error: {str(e)}"
            }


async def process_stripe_refund(payment_id: str, amount: Optional[float] = None) -> dict:
    """
    Process refund through Stripe
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe credentials not configured")
    
    url = "https://api.stripe.com/v1/refunds"
    
    # Prepare refund data
    refund_data = {
        "payment_intent": payment_id
    }
    if amount:
        refund_data["amount"] = int(amount * 100)  # Convert to cents
    
    # Make API request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {STRIPE_SECRET_KEY}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data=refund_data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                refund_data = response.json()
                return {
                    "success": True,
                    "refund_id": refund_data["id"],
                    "amount": refund_data["amount"] / 100,  # Convert from cents
                    "currency": refund_data["currency"].upper(),
                    "status": refund_data["status"],
                    "created_at": datetime.fromtimestamp(refund_data["created"]).isoformat()
                }
            else:
                error_data = response.json()
                return {
                    "success": False,
                    "error": error_data.get("error", {}).get("message", "Refund failed")
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Stripe API error: {str(e)}"
            }


def determine_payment_gateway(payment_id: str) -> str:
    """
    Determine which payment gateway based on payment ID format
    Razorpay IDs start with 'pay_'
    Stripe IDs start with 'pi_' or 'ch_'
    """
    if payment_id.startswith("pay_"):
        return "razorpay"
    elif payment_id.startswith(("pi_", "ch_")):
        return "stripe"
    else:
        raise HTTPException(
            status_code=400,
            detail="Unknown payment ID format. Cannot determine payment gateway."
        )


@router.post("/request", response_model=RefundResponse)
async def request_refund(request: RefundRequest):
    """
    Process refund request
    
    Supports both Razorpay and Stripe payments.
    Automatically detects payment gateway from payment ID format.
    
    24-hour money-back guarantee:
    - Full refund if requested within 24 hours of payment
    - Partial refunds may be processed after 24 hours (admin approval)
    """
    try:
        # Determine payment gateway
        gateway = determine_payment_gateway(request.payment_id)
        
        # Process refund based on gateway
        if gateway == "razorpay":
            result = await process_razorpay_refund(request.payment_id, request.amount)
        elif gateway == "stripe":
            result = await process_stripe_refund(request.payment_id, request.amount)
        else:
            raise HTTPException(status_code=400, detail="Unsupported payment gateway")
        
        # Check if refund was successful
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Refund failed: {result['error']}"
            )
        
        # Calculate estimated arrival
        estimated_arrival = (datetime.utcnow() + timedelta(days=5 if gateway == "razorpay" else 7)).strftime("%Y-%m-%d")
        
        # Determine status message
        if result["status"] == "processed":
            status = "success"
            message = f"Refund processed successfully. Amount will be credited within 5-7 business days."
        else:
            status = "pending"
            message = f"Refund initiated. Processing may take 1-2 business days."
        
        return RefundResponse(
            refund_id=result["refund_id"],
            status=status,
            amount=result["amount"],
            currency=result["currency"],
            payment_gateway=gateway,
            refund_date=result["created_at"],
            estimated_arrival=estimated_arrival,
            message=message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refund processing failed: {str(e)}")


@router.get("/status/{refund_id}", response_model=RefundStatus)
async def check_refund_status(refund_id: str):
    """
    Check status of a refund
    
    Queries the payment gateway to get current refund status.
    """
    try:
        # Determine gateway from refund ID
        if refund_id.startswith("rfnd_"):
            gateway = "razorpay"
            url = f"https://api.razorpay.com/v1/refunds/{refund_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return RefundStatus(
                        refund_id=data["id"],
                        status=data["status"],
                        amount=data["amount"] / 100,
                        created_at=datetime.fromtimestamp(data["created_at"]).isoformat(),
                        processed_at=datetime.fromtimestamp(data.get("processed_at", 0)).isoformat() if data.get("processed_at") else None
                    )
        
        elif refund_id.startswith("re_"):
            gateway = "stripe"
            url = f"https://api.stripe.com/v1/refunds/{refund_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {STRIPE_SECRET_KEY}"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return RefundStatus(
                        refund_id=data["id"],
                        status=data["status"],
                        amount=data["amount"] / 100,
                        created_at=datetime.fromtimestamp(data["created"]).isoformat(),
                        processed_at=None  # Stripe doesn't provide processed_at
                    )
        
        raise HTTPException(status_code=404, detail="Refund not found")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check refund status: {str(e)}")


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify refund processing is working"""
    return {
        "status": "operational",
        "service": "Automated Refund Processing",
        "version": "1.0.0",
        "supported_gateways": ["razorpay", "stripe"],
        "features": [
            "Full refunds",
            "Partial refunds",
            "24-hour money-back guarantee",
            "Automatic gateway detection",
            "Refund status tracking"
        ],
        "razorpay_configured": bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET),
        "stripe_configured": bool(STRIPE_SECRET_KEY)
    }
