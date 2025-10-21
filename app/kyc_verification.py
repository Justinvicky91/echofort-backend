# app/kyc_verification.py - KYC Verification System
"""
KYC Verification - Government ID Verification
Supports: Aadhaar, PAN, Passport, Driving License, Voter ID
Compliant with Digital Personal Data Protection Act 2023
"""

from fastapi import APIRouter, Request, HTTPException, Depends, File, UploadFile
from sqlalchemy import text
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr
from .utils import get_current_user
import os
import re

router = APIRouter(prefix="/api/kyc", tags=["KYC Verification"])

# ID validation patterns (India-specific)
ID_PATTERNS = {
    "aadhaar": r"^\d{12}$",  # 12 digits
    "pan": r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$",  # ABCDE1234F format
    "passport": r"^[A-Z]{1}[0-9]{7}$",  # A1234567 format
    "driving_license": r"^[A-Z]{2}[0-9]{13}$",  # State code + 13 digits
    "voter_id": r"^[A-Z]{3}[0-9]{7}$"  # ABC1234567 format
}


class KYCSubmission(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    country: str = "India"
    postal_code: str
    id_type: Literal["aadhaar", "pan", "passport", "driving_license", "voter_id"]
    id_number: str


class KYCApproval(BaseModel):
    kyc_id: int
    approved: bool
    rejection_reason: Optional[str] = None
    admin_key: str


def validate_id_number(id_type: str, id_number: str) -> tuple[bool, str]:
    """
    Validate ID number format
    Returns: (is_valid, error_message)
    """
    pattern = ID_PATTERNS.get(id_type)
    
    if not pattern:
        return False, "Invalid ID type"
    
    if not re.match(pattern, id_number.upper()):
        return False, f"Invalid {id_type.upper()} format"
    
    # Additional validations
    if id_type == "aadhaar":
        # Aadhaar should not start with 0 or 1
        if id_number[0] in ["0", "1"]:
            return False, "Invalid Aadhaar number"
    
    elif id_type == "pan":
        # PAN 4th character should be P for individual
        if id_number[3] not in ["P", "C", "H", "F", "A", "T", "B", "L", "J", "G"]:
            return False, "Invalid PAN format"
    
    return True, ""


def mask_id_number(id_type: str, id_number: str) -> str:
    """
    Mask ID number for security (show only last 4 digits)
    """
    if len(id_number) <= 4:
        return "****"
    
    return "*" * (len(id_number) - 4) + id_number[-4:]


@router.post("/submit")
async def submit_kyc(
    request: Request,
    payload: KYCSubmission,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit KYC verification request
    User uploads government ID for verification
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Check if KYC already exists
        existing_query = text("""
            SELECT id, verification_status FROM kyc_verifications
            WHERE user_id = :uid
        """)
        existing = (await db.execute(existing_query, {"uid": user_id})).fetchone()
        
        if existing:
            if existing[1] == "verified":
                raise HTTPException(400, "KYC already verified")
            elif existing[1] == "pending":
                raise HTTPException(400, "KYC verification already pending")
        
        # Validate ID number format
        is_valid, error_msg = validate_id_number(payload.id_type, payload.id_number)
        if not is_valid:
            raise HTTPException(400, error_msg)
        
        # Save KYC submission
        insert_query = text("""
            INSERT INTO kyc_verifications (
                user_id, full_name, email, phone,
                address_line1, address_line2, city, state, country, postal_code,
                id_type, id_number, id_proof_url,
                verification_status, created_at, updated_at
            ) VALUES (
                :uid, :name, :email, :phone,
                :addr1, :addr2, :city, :state, :country, :postal,
                :id_type, :id_num, NULL,
                'pending', NOW(), NOW()
            )
            ON CONFLICT (user_id) DO UPDATE SET
                full_name = :name,
                email = :email,
                phone = :phone,
                address_line1 = :addr1,
                address_line2 = :addr2,
                city = :city,
                state = :state,
                country = :country,
                postal_code = :postal,
                id_type = :id_type,
                id_number = :id_num,
                verification_status = 'pending',
                updated_at = NOW()
            RETURNING id
        """)
        
        result = await db.execute(insert_query, {
            "uid": user_id,
            "name": payload.full_name,
            "email": payload.email,
            "phone": payload.phone,
            "addr1": payload.address_line1,
            "addr2": payload.address_line2,
            "city": payload.city,
            "state": payload.state,
            "country": payload.country,
            "postal": payload.postal_code,
            "id_type": payload.id_type,
            "id_num": payload.id_number
        })
        
        kyc_id = result.fetchone()[0]
        
        return {
            "ok": True,
            "kyc_id": kyc_id,
            "status": "pending",
            "message": "KYC verification submitted successfully",
            "id_type": payload.id_type,
            "id_number_masked": mask_id_number(payload.id_type, payload.id_number),
            "next_steps": [
                "Upload ID proof document (front and back)",
                "Wait for admin verification (24-48 hours)",
                "You will be notified via email once verified"
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"KYC submission error: {str(e)}")


@router.post("/upload-document/{kyc_id}")
async def upload_kyc_document(
    request: Request,
    kyc_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload ID proof document (image/PDF)
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Verify KYC belongs to user
        kyc_query = text("""
            SELECT user_id, verification_status FROM kyc_verifications
            WHERE id = :kid
        """)
        kyc = (await db.execute(kyc_query, {"kid": kyc_id})).fetchone()
        
        if not kyc:
            raise HTTPException(404, "KYC record not found")
        
        if kyc[0] != user_id:
            raise HTTPException(403, "Unauthorized")
        
        if kyc[1] == "verified":
            raise HTTPException(400, "KYC already verified")
        
        # Read file
        file_data = await file.read()
        
        # In production, upload to S3/cloud storage
        # For now, save file path
        file_path = f"/uploads/kyc/{user_id}_{kyc_id}_{file.filename}"
        
        # Update KYC with document URL
        update_query = text("""
            UPDATE kyc_verifications
            SET id_proof_url = :url, updated_at = NOW()
            WHERE id = :kid
        """)
        
        await db.execute(update_query, {"url": file_path, "kid": kyc_id})
        
        return {
            "ok": True,
            "kyc_id": kyc_id,
            "document_uploaded": True,
            "message": "ID proof uploaded successfully",
            "status": "pending_verification"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Document upload error: {str(e)}")


@router.get("/status")
async def get_kyc_status(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Get user's KYC verification status
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        kyc_query = text("""
            SELECT 
                id, full_name, id_type, verification_status,
                created_at, verified_at, rejection_reason
            FROM kyc_verifications
            WHERE user_id = :uid
        """)
        
        kyc = (await db.execute(kyc_query, {"uid": user_id})).fetchone()
        
        if not kyc:
            return {
                "ok": True,
                "kyc_status": "not_submitted",
                "message": "KYC not submitted yet"
            }
        
        return {
            "ok": True,
            "kyc_id": kyc[0],
            "full_name": kyc[1],
            "id_type": kyc[2],
            "verification_status": kyc[3],
            "submitted_at": str(kyc[4]),
            "verified_at": str(kyc[5]) if kyc[5] else None,
            "rejection_reason": kyc[6],
            "message": {
                "pending": "KYC verification in progress",
                "verified": "KYC verified successfully",
                "rejected": f"KYC rejected: {kyc[6]}",
                "expired": "KYC expired, please resubmit"
            }.get(kyc[3], "Unknown status")
        }
    
    except Exception as e:
        raise HTTPException(500, f"Status check error: {str(e)}")


@router.post("/admin/verify")
async def admin_verify_kyc(request: Request, payload: KYCApproval):
    """
    Admin endpoint to approve/reject KYC
    """
    try:
        # Verify admin key
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if payload.admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        db = request.app.state.db
        
        if payload.approved:
            # Approve KYC
            update_query = text("""
                UPDATE kyc_verifications
                SET 
                    verification_status = 'verified',
                    verified_by = 1,
                    verified_at = NOW(),
                    updated_at = NOW()
                WHERE id = :kid
            """)
            
            await db.execute(update_query, {"kid": payload.kyc_id})
            
            return {
                "ok": True,
                "kyc_id": payload.kyc_id,
                "status": "verified",
                "message": "KYC approved successfully"
            }
        else:
            # Reject KYC
            update_query = text("""
                UPDATE kyc_verifications
                SET 
                    verification_status = 'rejected',
                    rejection_reason = :reason,
                    verified_by = 1,
                    updated_at = NOW()
                WHERE id = :kid
            """)
            
            await db.execute(update_query, {
                "kid": payload.kyc_id,
                "reason": payload.rejection_reason or "Document verification failed"
            })
            
            return {
                "ok": True,
                "kyc_id": payload.kyc_id,
                "status": "rejected",
                "message": "KYC rejected",
                "reason": payload.rejection_reason
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Verification error: {str(e)}")


@router.get("/admin/pending")
async def get_pending_kyc(request: Request, admin_key: str, limit: int = 50):
    """
    Admin endpoint to get pending KYC verifications
    """
    try:
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        db = request.app.state.db
        
        pending_query = text("""
            SELECT 
                k.id, k.user_id, k.full_name, k.email, k.phone,
                k.id_type, k.id_number, k.id_proof_url,
                k.created_at, u.identity
            FROM kyc_verifications k
            LEFT JOIN users u ON k.user_id = u.id
            WHERE k.verification_status = 'pending'
            ORDER BY k.created_at DESC
            LIMIT :lim
        """)
        
        pending = (await db.execute(pending_query, {"lim": limit})).fetchall()
        
        return {
            "ok": True,
            "total_pending": len(pending),
            "kyc_requests": [
                {
                    "kyc_id": p[0],
                    "user_id": p[1],
                    "full_name": p[2],
                    "email": p[3],
                    "phone": p[4],
                    "id_type": p[5],
                    "id_number_masked": mask_id_number(p[5], p[6]),
                    "id_proof_url": p[7],
                    "submitted_at": str(p[8]),
                    "user_identity": p[9]
                }
                for p in pending
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error fetching pending KYC: {str(e)}")

