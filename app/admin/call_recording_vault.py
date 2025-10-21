# app/admin/call_recording_vault.py
"""
Call Recording Vault Management
- Super Admin sets vault password
- All call recordings encrypted with vault password
- Only Super Admin can access/decrypt
"""

from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File
from sqlalchemy import text
from datetime import datetime
import hashlib
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from ..utils import get_current_user

router = APIRouter(prefix="/admin/vault", tags=["admin"])

def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password using PBKDF2"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def encrypt_file(file_data: bytes, password: str) -> tuple:
    """Encrypt file data with password"""
    # Generate random salt
    salt = os.urandom(16)
    
    # Derive key from password
    key = derive_key_from_password(password, salt)
    
    # Encrypt data
    f = Fernet(key)
    encrypted_data = f.encrypt(file_data)
    
    return encrypted_data, salt

def decrypt_file(encrypted_data: bytes, password: str, salt: bytes) -> bytes:
    """Decrypt file data with password"""
    # Derive key from password
    key = derive_key_from_password(password, salt)
    
    # Decrypt data
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_data)
    
    return decrypted_data

@router.post("/set-password")
async def set_vault_password(payload: dict, request: Request, current_user=Depends(get_current_user)):
    """
    Set or update vault password (Super Admin only)
    All future call recordings will be encrypted with this password
    """
    db = request.app.state.db
    
    # Verify super admin
    employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee or not employee['is_super_admin']:
        raise HTTPException(403, "Only super admin can set vault password")
    
    new_password = payload.get("vault_password")
    if not new_password or len(new_password) < 8:
        raise HTTPException(400, "Vault password must be at least 8 characters")
    
    # Hash password for storage (not for encryption, just for verification)
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
    
    # Store in settings
    await db.execute(text("""
        INSERT INTO admin_settings (key, value, updated_at, updated_by)
        VALUES ('vault_password_hash', :hash, NOW(), :uid)
        ON CONFLICT (key) DO UPDATE
        SET value = :hash, updated_at = NOW(), updated_by = :uid
    """), {"hash": password_hash, "uid": current_user['user_id']})
    
    return {
        "ok": True,
        "message": "Vault password set successfully",
        "note": "All future call recordings will be encrypted with this password"
    }

@router.post("/verify-password")
async def verify_vault_password(payload: dict, request: Request, current_user=Depends(get_current_user)):
    """
    Verify vault password before accessing call recordings
    """
    db = request.app.state.db
    
    # Verify super admin
    employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee or not employee['is_super_admin']:
        raise HTTPException(403, "Only super admin can access vault")
    
    password = payload.get("vault_password")
    if not password:
        raise HTTPException(400, "Vault password required")
    
    # Get stored password hash
    setting = await db.fetch_one(text("""
        SELECT value FROM admin_settings WHERE key = 'vault_password_hash'
    """))
    
    if not setting:
        raise HTTPException(404, "Vault password not set. Please set it first.")
    
    # Verify password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if password_hash != setting['value']:
        raise HTTPException(401, "Invalid vault password")
    
    return {
        "ok": True,
        "message": "Vault password verified",
        "access_granted": True
    }

@router.get("/recordings/list")
async def list_vault_recordings(
    request: Request, 
    current_user=Depends(get_current_user),
    vault_password: str = None
):
    """
    List all call recordings in vault (Super Admin only, requires vault password)
    """
    db = request.app.state.db
    
    # Verify super admin
    employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee or not employee['is_super_admin']:
        raise HTTPException(403, "Only super admin can access vault")
    
    # Verify vault password
    if not vault_password:
        raise HTTPException(400, "Vault password required")
    
    setting = await db.fetch_one(text("""
        SELECT value FROM admin_settings WHERE key = 'vault_password_hash'
    """))
    
    if not setting:
        raise HTTPException(404, "Vault password not set")
    
    password_hash = hashlib.sha256(vault_password.encode()).hexdigest()
    if password_hash != setting['value']:
        raise HTTPException(401, "Invalid vault password")
    
    # Get all call recordings
    recordings = await db.fetch_all(text("""
        SELECT 
            cr.id,
            cr.user_id,
            cr.phone_number,
            cr.call_type,
            cr.duration,
            cr.scam_detected,
            cr.trust_score,
            cr.file_path,
            cr.file_size,
            cr.encrypted,
            cr.created_at,
            u.email,
            u.name
        FROM call_recordings cr
        LEFT JOIN users u ON cr.user_id = u.id
        ORDER BY cr.created_at DESC
    """))
    
    return {
        "total": len(recordings),
        "recordings": [dict(r) for r in recordings]
    }

@router.get("/recordings/{recording_id}/decrypt")
async def decrypt_recording(
    recording_id: int,
    request: Request,
    current_user=Depends(get_current_user),
    vault_password: str = None
):
    """
    Decrypt and download a call recording (Super Admin only)
    """
    db = request.app.state.db
    
    # Verify super admin
    employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee or not employee['is_super_admin']:
        raise HTTPException(403, "Only super admin can decrypt recordings")
    
    # Verify vault password
    if not vault_password:
        raise HTTPException(400, "Vault password required")
    
    setting = await db.fetch_one(text("""
        SELECT value FROM admin_settings WHERE key = 'vault_password_hash'
    """))
    
    if not setting:
        raise HTTPException(404, "Vault password not set")
    
    password_hash = hashlib.sha256(vault_password.encode()).hexdigest()
    if password_hash != setting['value']:
        raise HTTPException(401, "Invalid vault password")
    
    # Get recording
    recording = await db.fetch_one(text("""
        SELECT * FROM call_recordings WHERE id = :id
    """), {"id": recording_id})
    
    if not recording:
        raise HTTPException(404, "Recording not found")
    
    # If encrypted, decrypt
    if recording['encrypted']:
        # Read encrypted file
        with open(recording['file_path'], 'rb') as f:
            encrypted_data = f.read()
        
        # Get salt from database
        salt_hex = recording.get('encryption_salt')
        if not salt_hex:
            raise HTTPException(500, "Encryption salt not found")
        
        salt = bytes.fromhex(salt_hex)
        
        # Decrypt
        try:
            decrypted_data = decrypt_file(encrypted_data, vault_password, salt)
            
            return {
                "ok": True,
                "recording_id": recording_id,
                "decrypted_size": len(decrypted_data),
                "download_url": f"/admin/vault/recordings/{recording_id}/download?vault_password={vault_password}"
            }
        except Exception as e:
            raise HTTPException(500, f"Decryption failed: {str(e)}")
    else:
        # Not encrypted, return file path
        return {
            "ok": True,
            "recording_id": recording_id,
            "encrypted": False,
            "file_path": recording['file_path']
        }

@router.delete("/recordings/{recording_id}")
async def delete_recording(
    recording_id: int,
    request: Request,
    current_user=Depends(get_current_user),
    vault_password: str = None
):
    """
    Delete a call recording (Super Admin only, requires vault password)
    """
    db = request.app.state.db
    
    # Verify super admin
    employee = await db.fetch_one(text("""
        SELECT is_super_admin FROM employees WHERE user_id = :uid
    """), {"uid": current_user['user_id']})
    
    if not employee or not employee['is_super_admin']:
        raise HTTPException(403, "Only super admin can delete recordings")
    
    # Verify vault password
    if not vault_password:
        raise HTTPException(400, "Vault password required")
    
    setting = await db.fetch_one(text("""
        SELECT value FROM admin_settings WHERE key = 'vault_password_hash'
    """))
    
    if not setting:
        raise HTTPException(404, "Vault password not set")
    
    password_hash = hashlib.sha256(vault_password.encode()).hexdigest()
    if password_hash != setting['value']:
        raise HTTPException(401, "Invalid vault password")
    
    # Get recording
    recording = await db.fetch_one(text("""
        SELECT file_path FROM call_recordings WHERE id = :id
    """), {"id": recording_id})
    
    if not recording:
        raise HTTPException(404, "Recording not found")
    
    # Delete file
    if os.path.exists(recording['file_path']):
        os.remove(recording['file_path'])
    
    # Delete from database
    await db.execute(text("""
        DELETE FROM call_recordings WHERE id = :id
    """), {"id": recording_id})
    
    return {
        "ok": True,
        "message": "Recording deleted successfully"
    }

