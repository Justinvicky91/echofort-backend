"""
User Verification API
Mobile app endpoint for completing user verification during onboarding
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import text
from .utils import get_current_user
import re

router = APIRouter(prefix="/api/user", tags=["User Verification"])

# ID validation patterns (India-specific)
ID_PATTERNS = {
    "aadhaar": r"^\d{12}$",
    "pan": r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$",
    "passport": r"^[A-Z]{1}[0-9]{7}$",
    "driving_license": r"^[A-Z]{2}[0-9]{13}$",
    "voter_id": r"^[A-Z]{3}[0-9]{7}$"
}


class VerificationRequest(BaseModel):
    address: str
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    pincode: str
    id_type: str
    id_number: str


def validate_id_number(id_type: str, id_number: str) -> tuple[bool, str]:
    """Validate ID number format"""
    pattern = ID_PATTERNS.get(id_type.lower())
    
    if not pattern:
        return False, "Invalid ID type"
    
    if not re.match(pattern, id_number.upper()):
        return False, f"Invalid {id_type.upper()} format"
    
    return True, ""


@router.post("/verification/complete")
async def complete_verification(
    request: Request,
    payload: VerificationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Complete user verification by submitting address and ID details
    Called by mobile app after OTP verification during onboarding
    """
    try:
        db = request.app.state.db
        user_id = current_user["id"]
        
        # Validate ID format
        is_valid, error_msg = validate_id_number(payload.id_type, payload.id_number)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Update users table with verification info
        update_query = text("""
            UPDATE users
            SET 
                address_line1 = :address,
                city = :city,
                district = :district,
                state = :state,
                country = :country,
                pincode = :pincode,
                id_type = :id_type,
                id_number = :id_number,
                kyc_status = 'pending'
            WHERE id = :user_id
        """)
        
        await db.execute(update_query, {
            "user_id": user_id,
            "address": payload.address,
            "city": payload.city,
            "district": payload.district,
            "state": payload.state,
            "country": payload.country,
            "pincode": payload.pincode,
            "id_type": payload.id_type,
            "id_number": payload.id_number
        })
        
        return {
            "ok": True,
            "message": "Verification information saved successfully",
            "kyc_status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")
