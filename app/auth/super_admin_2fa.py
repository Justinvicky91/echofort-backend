"""
Super Admin 2FA API Endpoints
Handles Email OTP + WhatsApp OTP + Recovery Codes
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
from .whatsapp_otp import send_whatsapp_otp, verify_whatsapp_otp, generate_recovery_codes
from ..database import get_db_connection
import bcrypt
import secrets

router = APIRouter(prefix="/auth", tags=["Super Admin 2FA"])

# Super Admin email from environment
SUPER_ADMIN_EMAIL = os.getenv("OWNER_EMAIL", "Vicky.Jvsap@gmail.com")

class MobileOTPRequest(BaseModel):
    email: EmailStr
    temp_token: str

class MobileOTPVerify(BaseModel):
    email: EmailStr
    mobile_otp: str
    temp_token: str

class RecoveryCodeVerify(BaseModel):
    email: EmailStr
    recovery_code: str
    temp_token: str

@router.post("/send-mobile-otp")
async def send_mobile_otp_endpoint(request: MobileOTPRequest):
    """
    Send WhatsApp OTP to Super Admin (2nd factor)
    Only called after email OTP is verified
    """
    # Verify it's Super Admin
    if request.email.lower() != SUPER_ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Not authorized for 2FA")
    
    # TODO: Verify temp_token is valid
    
    # Send WhatsApp OTP
    result = send_whatsapp_otp(request.email)
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result['message'])
    
    return {
        "success": True,
        "message": "WhatsApp OTP sent successfully",
        "dev_mode": result.get('dev_mode', False)
    }

@router.post("/verify-mobile-otp")
async def verify_mobile_otp_endpoint(request: MobileOTPVerify):
    """
    Verify WhatsApp OTP (2nd factor)
    Returns final auth token on success
    """
    # Verify it's Super Admin
    if request.email.lower() != SUPER_ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Verify OTP
    result = verify_whatsapp_otp(request.email, request.mobile_otp)
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    
    # Generate final auth token
    final_token = secrets.token_urlsafe(32)
    
    # Get user data from database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, email, role 
        FROM users 
        WHERE email = %s AND role = 'super_admin'
    """, (request.email,))
    
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="Super Admin not found")
    
    return {
        "success": True,
        "token": final_token,
        "user": {
            "id": user[0],
            "name": user[1],
            "email": user[2],
            "role": user[3]
        }
    }

@router.post("/verify-recovery-code")
async def verify_recovery_code_endpoint(request: RecoveryCodeVerify):
    """
    Verify recovery code (backup for lost mobile)
    Returns final auth token on success
    """
    # Verify it's Super Admin
    if request.email.lower() != SUPER_ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get stored recovery codes from database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT recovery_codes 
        FROM super_admin_recovery 
        WHERE email = %s
    """, (request.email,))
    
    result = cursor.fetchone()
    
    if not result or not result[0]:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="No recovery codes found")
    
    recovery_codes = result[0].split(',')
    
    # Verify recovery code
    if request.recovery_code not in recovery_codes:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid recovery code")
    
    # Remove used recovery code
    recovery_codes.remove(request.recovery_code)
    
    cursor.execute("""
        UPDATE super_admin_recovery 
        SET recovery_codes = %s, last_used = NOW()
        WHERE email = %s
    """, (','.join(recovery_codes), request.email))
    
    conn.commit()
    
    # Get user data
    cursor.execute("""
        SELECT id, name, email, role 
        FROM users 
        WHERE email = %s AND role = 'super_admin'
    """, (request.email,))
    
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="Super Admin not found")
    
    # Generate final auth token
    final_token = secrets.token_urlsafe(32)
    
    return {
        "success": True,
        "token": final_token,
        "user": {
            "id": user[0],
            "name": user[1],
            "email": user[2],
            "role": user[3]
        },
        "warning": "Recovery code used. Please update your mobile number."
    }

@router.post("/generate-recovery-codes")
async def generate_recovery_codes_endpoint(email: EmailStr):
    """
    Generate new recovery codes for Super Admin
    Only accessible by Super Admin
    """
    # Verify it's Super Admin
    if email.lower() != SUPER_ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Generate 10 recovery codes
    codes = generate_recovery_codes(10)
    
    # Store in database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO super_admin_recovery (email, recovery_codes, created_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (email) 
        DO UPDATE SET recovery_codes = EXCLUDED.recovery_codes, created_at = NOW()
    """, (email, ','.join(codes)))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {
        "success": True,
        "recovery_codes": codes,
        "message": "Save these codes in a secure location. Each code can only be used once."
    }

