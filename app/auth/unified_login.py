# app/auth/unified_login.py
"""
Unified Authentication System for EchoFort
- Users (Customers): Email/Phone + OTP
- Employees: Username + Password
- Super Admin: Username + OTP + Password
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import text
from datetime import datetime, timedelta
import random
import hashlib
import bcrypt
from ..deps import get_settings
from ..utils import jwt_encode
from ..email_service import email_service

router = APIRouter(prefix="/auth/unified", tags=["auth"])

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash"""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except:
        # Fallback to SHA-256 for legacy passwords
        return hashlib.sha256(password.encode()).hexdigest() == hashed

@router.post("/login/initiate")
async def initiate_login(payload: dict, request: Request):
    """
    Step 1: Initiate login - Determine user type and send OTP if needed
    
    Input: { "identifier": "email@example.com" or "username" }
    
    Returns:
    - user_type: "customer" | "employee" | "super_admin"
    - requires_otp: true/false
    - requires_password: true/false
    """
    identifier = payload.get("identifier", "").strip()
    
    if not identifier:
        raise HTTPException(400, "Email, phone, or username required")
    
    db = request.app.state.db
    
    # Check if it's an email/phone (customer) or username (employee/admin)
    is_email_or_phone = "@" in identifier or identifier.isdigit()
    
    if is_email_or_phone:
        # Customer login - send OTP
        otp_code = str(random.randint(100000, 999999))
        
        await db.execute(text("""
            INSERT INTO otps(identity, code, expires_at, created_at)
            VALUES (:i, :c, :e, NOW())
        """), {
            "i": identifier,
            "c": otp_code,
            "e": datetime.utcnow() + timedelta(minutes=5)
        })
        
        # Send OTP
        email_service.send_otp(identifier, otp_code, "")
        
        return {
            "user_type": "customer",
            "requires_otp": True,
            "requires_password": False,
            "message": f"OTP sent to {identifier}"
        }
    
    else:
        # Username - check if employee or super admin
        result = (await db.execute(text("""
            SELECT id, username, role, password_hash, is_super_admin
            FROM employees
            WHERE username = :u AND (active = true OR active IS NULL)
        """), {"u": identifier})).fetchone()
        
        if not result:
            raise HTTPException(404, "Username not found")
        
        if result['is_super_admin']:
            # Super Admin - send OTP + requires password
            # Get super admin email from users table
            admin_user = (await db.execute(text("""
                SELECT email FROM users WHERE id = :id
            """), {"id": result['id']})).fetchone()
            
            if admin_user:
                otp_code = str(random.randint(100000, 999999))
                
                await db.execute(text("""
                    INSERT INTO otps(identity, code, expires_at, created_at)
                    VALUES (:i, :c, :e, NOW())
                """), {
                    "i": admin_user['email'],
                    "c": otp_code,
                    "e": datetime.utcnow() + timedelta(minutes=5)
                })
                
                email_service.send_otp(admin_user['email'], otp_code, "")
            
            return {
                "user_type": "super_admin",
                "requires_otp": True,
                "requires_password": True,
                "message": "OTP sent to your registered email"
            }
        
        else:
            # Regular employee - only password needed
            return {
                "user_type": "employee",
                "requires_otp": False,
                "requires_password": True,
                "role": result['role'],
                "message": "Enter your password"
            }

@router.post("/login/verify")
async def verify_login(payload: dict, request: Request):
    """
    Step 2: Verify login credentials
    
    For Customers: { "identifier": "email", "otp": "123456" }
    For Employees: { "identifier": "username", "password": "xxx" }
    For Super Admin: { "identifier": "username", "otp": "123456", "password": "xxx" }
    """
    identifier = payload.get("identifier", "").strip()
    otp = payload.get("otp")
    password = payload.get("password")
    device_id = payload.get("device_id", "web")
    device_name = payload.get("device_name", "Web Browser")
    
    db = request.app.state.db
    
    is_email_or_phone = "@" in identifier or identifier.isdigit()
    
    if is_email_or_phone:
        # Customer login - verify OTP
        if not otp:
            raise HTTPException(400, "OTP required")
        
        # Verify OTP
        otp_record = (await db.execute(text("""
            SELECT * FROM otps
            WHERE identity = :i AND code = :c AND expires_at > NOW()
            ORDER BY created_at DESC LIMIT 1
        """), {"i": identifier, "c": otp})).fetchone()
        
        if not otp_record:
            raise HTTPException(401, "Invalid or expired OTP")
        
        # Delete used OTP
        await db.execute(text("DELETE FROM otps WHERE identity = :i"), {"i": identifier})
        
        # Get or create user
        user = (await db.execute(text("SELECT * FROM users WHERE email = :e OR phone = :p"), 
                                  {"e": identifier, "p": identifier})).fetchone()
        
        if not user:
            # Create new user
            await db.execute(text("""
                INSERT INTO users(email, phone, name, created_at)
                VALUES (:e, :p, :n, NOW())
            """), {
                "e": identifier if "@" in identifier else "",
                "p": identifier if identifier.isdigit() else "",
                "n": "User"
            })
            
            user = (await db.execute(text("SELECT * FROM users WHERE email = :e OR phone = :p"), 
                                      {"e": identifier, "p": identifier})).fetchone()
        
        # Create session token
        token = jwt_encode({
            "sub": str(user['id']),
            "user_type": "customer",
            "device_id": device_id,
            "exp": (datetime.utcnow() + timedelta(days=30)).timestamp()
        })
        
        return {
            "token": token,
            "user": {
                "id": user['id'],
                "email": user['email'],
                "name": user['name'],
                "user_type": "customer"
            },
            "redirect": "/dashboard"
        }
    
    else:
        # Employee or Super Admin login
        employee = (await db.execute(text("""
            SELECT * FROM employees WHERE username = :u AND (active = true OR active IS NULL)
        """), {"u": identifier})).fetchone()
        
        if not employee:
            raise HTTPException(404, "Username not found")
        
        if employee['is_super_admin']:
            # Super Admin - verify OTP + password
            if not otp or not password:
                raise HTTPException(400, "OTP and password required for super admin")
            
            # Verify OTP
            admin_user = (await db.execute(text("SELECT email FROM users WHERE id = :id"), 
                                            {"id": employee['user_id']})).fetchone()
            
            if admin_user:
                otp_record = (await db.execute(text("""
                    SELECT * FROM otps
                    WHERE identity = :i AND code = :c AND expires_at > NOW()
                    ORDER BY created_at DESC LIMIT 1
                """), {"i": admin_user['email'], "c": otp})).fetchone()
                
                if not otp_record:
                    raise HTTPException(401, "Invalid or expired OTP")
                
                # Delete used OTP
                await db.execute(text("DELETE FROM otps WHERE identity = :i"), 
                                  {"i": admin_user['email']})
            
            # Verify password
            if not verify_password(password, employee['password_hash']):
                raise HTTPException(401, "Invalid password")
            
            # Create session token
            token = jwt_encode({
                "sub": str(employee['user_id']),
                "employee_id": str(employee['id']),
                "user_type": "super_admin",
                "role": "super_admin",
                "device_id": device_id,
                "exp": (datetime.utcnow() + timedelta(hours=8)).timestamp()
            })
            
            return {
                "token": token,
                "user": {
                    "id": employee['user_id'],
                    "employee_id": employee['id'],
                    "username": employee['username'],
                    "role": "super_admin",
                    "user_type": "super_admin"
                },
                "redirect": "/admin/dashboard"
            }
        
        else:
            # Regular employee - verify password only
            if not password:
                raise HTTPException(400, "Password required")
            
            if not verify_password(password, employee['password_hash']):
                raise HTTPException(401, "Invalid password")
            
            # Create session token
            token = jwt_encode({
                "sub": str(employee['user_id']) if employee['user_id'] else str(employee['id']),
                "employee_id": str(employee['id']),
                "user_type": "employee",
                "role": employee['role'],
                "device_id": device_id,
                "exp": (datetime.utcnow() + timedelta(hours=8)).timestamp()
            })
            
            # Determine redirect based on role
            role_redirects = {
                "admin": "/admin/dashboard",
                "marketing": "/admin/marketing",
                "customer_support": "/admin/support",
                "accounting": "/admin/accounting",
                "hr": "/admin/hr"
            }
            
            return {
                "token": token,
                "user": {
                    "id": employee['id'],
                    "username": employee['username'],
                    "role": employee['role'],
                    "user_type": "employee",
                    "department": employee.get('department', '')
                },
                "redirect": role_redirects.get(employee['role'], "/admin/dashboard")
            }

@router.post("/setup/super-admin")
async def setup_super_admin(payload: dict, request: Request):
    """
    First-time setup: Create super admin account
    This endpoint should only work if no super admin exists
    """
    username = payload.get("username")
    password = payload.get("password")
    email = payload.get("email")
    name = payload.get("name", "Super Admin")
    
    if not username or not password or not email:
        raise HTTPException(400, "Username, password, and email required")
    
    db = request.app.state.db
    
    # Check if super admin already exists
    existing = (await db.execute(text("""
        SELECT id FROM employees WHERE is_super_admin = true
    """))).fetchone()
    
    if existing:
        raise HTTPException(403, "Super admin already exists")
    
    # Create user account
    await db.execute(text("""
        INSERT INTO users(email, name, created_at)
        VALUES (:e, :n, NOW())
    """), {"e": email, "n": name})
    
    user = (await db.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email})).fetchone()
    
    # Create employee record as super admin
    await db.execute(text("""
        INSERT INTO employees(user_id, username, password_hash, role, department, is_super_admin, active, created_at)
        VALUES (:uid, :u, :p, 'super_admin', 'Management', true, true, NOW())
    """), {
        "uid": user['id'],
        "u": username,
        "p": hash_password(password)
    })
    
    return {
        "ok": True,
        "message": "Super admin account created successfully",
        "username": username,
        "email": email
    }

