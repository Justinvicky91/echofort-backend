"""
Google Authenticator (TOTP) 2FA API Endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from ..auth.google_authenticator import (
    generate_totp_secret,
    generate_qr_code,
    verify_totp,
    generate_backup_codes
)

router = APIRouter(prefix="/auth/totp", tags=["totp-2fa"])

@router.post("/setup")
async def setup_totp(payload: dict, request: Request):
    """
    Setup TOTP 2FA for Super Admin
    
    Input: { "username": "EchofortSuperAdmin91", "password": "xxx" }
    Returns: QR code and secret for Google Authenticator setup
    """
    try:
        username = payload.get("username", "").strip()
        password = payload.get("password")
        
        if not username or not password:
            raise HTTPException(400, "Username and password required")
        
        # Get database connection
        db = request.app.state.db
        
        # Verify user is Super Admin and password is correct
        from ..auth.fixed_auth import verify_password
        
        result = await db.execute(text("""
            SELECT id, username, password_hash, is_super_admin
            FROM employees 
            WHERE username = :u AND is_super_admin = true AND (active = true OR active IS NULL)
        """), {"u": username})
        
        employee = result.fetchone()
        
        if not employee:
            raise HTTPException(404, "Super Admin not found")
        
        emp_id, emp_username, emp_password_hash, emp_is_super_admin = employee
        
        # Verify password
        if not verify_password(password, emp_password_hash):
            raise HTTPException(401, "Invalid password")
        
        # Generate TOTP secret
        secret = generate_totp_secret()
        
        # Generate QR code
        qr_code = generate_qr_code(secret, emp_username)
        
        # Generate backup codes
        backup_codes = generate_backup_codes(10)
        
        # Store secret in database
        await db.execute(text("""
            UPDATE employees 
            SET totp_secret = :secret, totp_enabled = false
            WHERE id = :id
        """), {"secret": secret, "id": emp_id})
        
        print(f"✅ TOTP setup initiated for: {emp_username}")
        
        return {
            "success": True,
            "qr_code": qr_code,
            "secret": secret,
            "backup_codes": backup_codes,
            "message": "Scan QR code with Google Authenticator app"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ TOTP setup error: {e}")
        raise HTTPException(500, f"TOTP setup failed: {str(e)}")

@router.post("/enable")
async def enable_totp(payload: dict, request: Request):
    """
    Enable TOTP 2FA after verifying first code
    
    Input: { "username": "EchofortSuperAdmin91", "token": "123456" }
    Returns: Success confirmation
    """
    try:
        username = payload.get("username", "").strip()
        token = payload.get("token", "").strip()
        
        if not username or not token:
            raise HTTPException(400, "Username and token required")
        
        # Get database connection
        db = request.app.state.db
        
        # Get user's TOTP secret
        result = await db.execute(text("""
            SELECT id, username, totp_secret, totp_enabled
            FROM employees 
            WHERE username = :u AND is_super_admin = true AND (active = true OR active IS NULL)
        """), {"u": username})
        
        employee = result.fetchone()
        
        if not employee:
            raise HTTPException(404, "Super Admin not found")
        
        emp_id, emp_username, totp_secret, totp_enabled = employee
        
        if not totp_secret:
            raise HTTPException(400, "TOTP not set up. Run /setup first.")
        
        if totp_enabled:
            raise HTTPException(400, "TOTP already enabled")
        
        # Verify TOTP token
        if not verify_totp(totp_secret, token):
            raise HTTPException(401, "Invalid TOTP code")
        
        # Enable TOTP
        await db.execute(text("""
            UPDATE employees 
            SET totp_enabled = true
            WHERE id = :id
        """), {"id": emp_id})
        
        print(f"✅ TOTP enabled for: {emp_username}")
        
        return {
            "success": True,
            "message": "Google Authenticator 2FA enabled successfully!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ TOTP enable error: {e}")
        raise HTTPException(500, f"TOTP enable failed: {str(e)}")

@router.post("/verify")
async def verify_totp_login(payload: dict, request: Request):
    """
    Verify TOTP code during login
    
    Input: { "username": "EchofortSuperAdmin91", "token": "123456" }
    Returns: JWT token if valid
    """
    try:
        username = payload.get("username", "").strip()
        token = payload.get("token", "").strip()
        device_id = payload.get("device_id", "web")
        
        if not username or not token:
            raise HTTPException(400, "Username and token required")
        
        # Get database connection
        db = request.app.state.db
        
        # Get user's TOTP secret
        result = await db.execute(text("""
            SELECT id, username, totp_secret, totp_enabled
            FROM employees 
            WHERE username = :u AND is_super_admin = true AND (active = true OR active IS NULL)
        """), {"u": username})
        
        employee = result.fetchone()
        
        if not employee:
            raise HTTPException(404, "Super Admin not found")
        
        emp_id, emp_username, totp_secret, totp_enabled = employee
        
        if not totp_enabled or not totp_secret:
            raise HTTPException(400, "TOTP not enabled for this account")
        
        # Verify TOTP token
        if not verify_totp(totp_secret, token):
            raise HTTPException(401, "Invalid TOTP code")
        
        # Generate JWT token
        from datetime import datetime, timedelta
        from ..utils import jwt_encode
        
        token_data = {
            "sub": str(emp_id),
            "employee_id": str(emp_id),
            "user_type": "super_admin",
            "role": "super_admin",
            "device_id": device_id,
            "exp": (datetime.utcnow() + timedelta(hours=8)).timestamp()
        }
        
        jwt_token = jwt_encode(token_data)
        
        print(f"✅ TOTP 2FA login successful for: {emp_username}")
        
        # Get permissions and sidebar items for super_admin
        from ..rbac import get_permissions_for_role, get_sidebar_items_for_role
        permissions = get_permissions_for_role("super_admin")
        sidebar_items = get_sidebar_items_for_role("super_admin")
        
        return {
            "token": jwt_token,
            "user": {
                "id": emp_id,
                "employee_id": emp_id,
                "username": emp_username,
                "role": "super_admin",
                "user_type": "super_admin",
                "is_super_admin": True,
                "department": "Executive"
            },
            "permissions": permissions,
            "sidebar_items": sidebar_items,
            "redirect": "/super-admin"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ TOTP verify error: {e}")
        raise HTTPException(500, f"TOTP verification failed: {str(e)}")

@router.post("/disable")
async def disable_totp(payload: dict, request: Request):
    """
    Disable TOTP 2FA (requires password confirmation)
    
    Input: { "username": "EchofortSuperAdmin91", "password": "xxx" }
    Returns: Success confirmation
    """
    try:
        username = payload.get("username", "").strip()
        password = payload.get("password")
        
        if not username or not password:
            raise HTTPException(400, "Username and password required")
        
        # Get database connection
        db = request.app.state.db
        
        # Verify user and password
        from ..auth.fixed_auth import verify_password
        
        result = await db.execute(text("""
            SELECT id, username, password_hash
            FROM employees 
            WHERE username = :u AND is_super_admin = true AND (active = true OR active IS NULL)
        """), {"u": username})
        
        employee = result.fetchone()
        
        if not employee:
            raise HTTPException(404, "Super Admin not found")
        
        emp_id, emp_username, emp_password_hash = employee
        
        # Verify password
        if not verify_password(password, emp_password_hash):
            raise HTTPException(401, "Invalid password")
        
        # Disable TOTP
        await db.execute(text("""
            UPDATE employees 
            SET totp_enabled = false, totp_secret = NULL
            WHERE id = :id
        """), {"id": emp_id})
        
        print(f"✅ TOTP disabled for: {emp_username}")
        
        return {
            "success": True,
            "message": "Google Authenticator 2FA disabled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ TOTP disable error: {e}")
        raise HTTPException(500, f"TOTP disable failed: {str(e)}")

@router.get("/status/{username}")
async def get_totp_status(username: str, request: Request):
    """
    Check if TOTP is enabled for a user
    
    Returns: { "enabled": true/false }
    """
    try:
        # Get database connection
        db = request.app.state.db
        
        result = await db.execute(text("""
            SELECT totp_enabled
            FROM employees 
            WHERE username = :u AND is_super_admin = true AND (active = true OR active IS NULL)
        """), {"u": username})
        
        employee = result.fetchone()
        
        if not employee:
            raise HTTPException(404, "Super Admin not found")
        
        totp_enabled = employee[0] if employee[0] is not None else False
        
        return {
            "enabled": totp_enabled,
            "username": username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ TOTP status error: {e}")
        raise HTTPException(500, f"Status check failed: {str(e)}")

@router.get("/test")
async def test_totp():
    """Test TOTP system"""
    return {
        "status": "ok",
        "message": "TOTP 2FA system operational"
    }
