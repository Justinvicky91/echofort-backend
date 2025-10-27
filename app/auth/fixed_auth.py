# app/auth/fixed_auth.py
"""
Fixed Authentication System for EchoFort
- Robust database connection handling
- Better error handling
- Simplified flow
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from datetime import datetime, timedelta
import random
import hashlib
import bcrypt
import os
from ..utils import jwt_encode

router = APIRouter(prefix="/auth/fixed", tags=["auth-fixed"])

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash"""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        # Fallback to SHA-256 for legacy passwords
        try:
            return hashlib.sha256(password.encode()).hexdigest() == hashed
        except:
            return False

@router.post("/login/initiate")
async def initiate_login(payload: dict, request: Request):
    """
    Step 1: Initiate login - Determine user type
    
    Input: { "identifier": "email@example.com" or "username" }
    
    Returns:
    - user_type: "customer" | "employee" | "super_admin"
    - requires_otp: true/false
    - requires_password: true/false
    """
    try:
        identifier = payload.get("identifier", "").strip()
        
        if not identifier:
            raise HTTPException(400, "Email, phone, or username required")
        
        print(f"🔍 Login initiate for: {identifier}")
        
        # Get database connection
        try:
            db = request.app.state.db
            print(f"✅ Database connection obtained")
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise HTTPException(500, f"Database connection failed: {str(e)}")
        
        # Check if it's an email/phone (customer) or username (employee/admin)
        is_email_or_phone = "@" in identifier or identifier.isdigit()
        
        if is_email_or_phone:
            # Customer login - would send OTP (simplified for now)
            print(f"📧 Customer login detected: {identifier}")
            return {
                "user_type": "customer",
                "requires_otp": True,
                "requires_password": False,
                "message": f"OTP would be sent to {identifier} (SendGrid not configured)"
            }
        
        else:
            # Username - check if employee or super admin
            print(f"👤 Employee/Admin login detected: {identifier}")
            
            try:
                result = await db.execute(text("""
                    SELECT id, username, role, password_hash, is_super_admin, active
                    FROM employees
                    WHERE username = :u AND (active = true OR active IS NULL)
                """), {"u": identifier})
                
                employee = result.fetchone()
                
                if not employee:
                    print(f"❌ Username not found: {identifier}")
                    raise HTTPException(404, "Username not found")
                
                # Convert tuple to dict
                emp_id, emp_username, emp_role, emp_password_hash, emp_is_super_admin, emp_active = employee
                
                print(f"✅ Employee found: {emp_username}, role: {emp_role}, super_admin: {emp_is_super_admin}")
                
                if emp_is_super_admin:
                    return {
                        "user_type": "super_admin",
                        "requires_otp": False,
                        "requires_password": True,
                        "message": "Enter your password"
                    }
                else:
                    return {
                        "user_type": "employee",
                        "requires_otp": False,
                        "requires_password": True,
                        "role": emp_role,
                        "message": "Enter your password"
                    }
                    
            except HTTPException:
                raise
            except Exception as e:
                print(f"❌ Database query error: {e}")
                raise HTTPException(500, f"Database query failed: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in initiate_login: {e}")
        raise HTTPException(500, f"Login initiation failed: {str(e)}")

@router.post("/login/verify")
async def verify_login(payload: dict, request: Request):
    """
    Step 2: Verify login credentials
    
    For Customers: { "identifier": "email", "otp": "123456" }
    For Employees: { "identifier": "username", "password": "xxx" }
    """
    try:
        identifier = payload.get("identifier", "").strip()
        password = payload.get("password")
        otp = payload.get("otp")
        device_id = payload.get("device_id", "web")
        device_name = payload.get("device_name", "Web Browser")
        
        if not identifier:
            raise HTTPException(400, "Identifier required")
        
        print(f"🔍 Login verify for: {identifier}")
        
        # Get database connection
        try:
            db = request.app.state.db
            print(f"✅ Database connection obtained")
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise HTTPException(500, f"Database connection failed: {str(e)}")
        
        is_email_or_phone = "@" in identifier or identifier.isdigit()
        
        if is_email_or_phone:
            # Customer login - verify OTP (simplified)
            print(f"📧 Customer OTP verification: {identifier}")
            
            if not otp:
                raise HTTPException(400, "OTP required for customer login")
            
            # For now, return error since SendGrid not configured
            raise HTTPException(503, "Customer login not fully configured (SendGrid required)")
        
        else:
            # Employee or Super Admin login
            print(f"👤 Employee/Admin password verification: {identifier}")
            
            if not password:
                raise HTTPException(400, "Password required")
            
            try:
                result = await db.execute(text("""
                    SELECT id, username, role, password_hash, is_super_admin, active
                    FROM employees 
                    WHERE username = :u AND (active = true OR active IS NULL)
                """), {"u": identifier})
                
                employee = result.fetchone()
                
                if not employee:
                    print(f"❌ Username not found: {identifier}")
                    raise HTTPException(404, "Username not found")
                
                # Convert tuple to dict
                emp_id, emp_username, emp_role, emp_password_hash, emp_is_super_admin, emp_active = employee
                
                print(f"✅ Employee found: {emp_username}")
                
                # Verify password
                if not verify_password(password, emp_password_hash):
                    print(f"❌ Invalid password for: {identifier}")
                    raise HTTPException(401, "Invalid password")
                
                print(f"✅ Password verified for: {identifier}")
                
                # Create session token
                token_data = {
                    "sub": str(emp_id),
                    "employee_id": str(emp_id),
                    "user_type": "super_admin" if emp_is_super_admin else "employee",
                    "role": "super_admin" if emp_is_super_admin else emp_role,
                    "device_id": device_id,
                    "exp": (datetime.utcnow() + timedelta(hours=8)).timestamp()
                }
                
                token = jwt_encode(token_data)
                
                # Determine redirect
                if emp_is_super_admin:
                    redirect = "/super-admin"
                else:
                    role_redirects = {
                        "admin": "/admin/dashboard",
                        "customer_support": "/admin/support",
                        "marketing": "/admin/marketing",
                        "accounting": "/admin/accounting",
                        "hr": "/admin/hr"
                    }
                    redirect = role_redirects.get(emp_role, "/admin/dashboard")
                
                print(f"✅ Login successful for: {identifier}, redirecting to: {redirect}")
                
                return {
                    "token": token,
                    "user": {
                        "id": emp_id,
                        "employee_id": emp_id,
                        "username": emp_username,
                        "role": "super_admin" if emp_is_super_admin else emp_role,
                        "user_type": "super_admin" if emp_is_super_admin else "employee"
                    },
                    "redirect": redirect
                }
                
            except HTTPException:
                raise
            except Exception as e:
                print(f"❌ Database query error: {e}")
                raise HTTPException(500, f"Database query failed: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in verify_login: {e}")
        raise HTTPException(500, f"Login verification failed: {str(e)}")

@router.get("/test")
async def test_auth(request: Request):
    """Test authentication system"""
    try:
        db = request.app.state.db
        
        # Test database connection
        result = await db.execute(text("SELECT COUNT(*) FROM employees"))
        count_tuple = result.fetchone()
        count = count_tuple[0] if count_tuple else 0
        
        return {
            "status": "ok",
            "database": "connected",
            "employee_count": count,
            "message": "Authentication system operational"
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e),
            "message": "Authentication system has issues"
        }

