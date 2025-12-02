"""
Block 24F - Forgot Password Flow
Implements password reset via email for all dashboard users
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from datetime import datetime, timedelta
import hashlib
import secrets
import os

router = APIRouter(prefix="/auth", tags=["auth-forgot-password"])

def hash_token(token: str) -> str:
    """Hash a token using SHA-256"""
    return hashlib.sha256(token.encode()).hexdigest()

def generate_reset_token() -> str:
    """Generate a secure random token (32 bytes = 64 hex characters)"""
    return secrets.token_urlsafe(32)

async def send_reset_email(email: str, username: str, reset_token: str):
    """Send password reset email"""
    reset_link = f"https://echofort.ai/reset-password?token={reset_token}"
    
    # TODO: Integrate with existing email infrastructure
    # For now, just log the reset link
    print(f"=" * 70)
    print(f"PASSWORD RESET EMAIL")
    print(f"=" * 70)
    print(f"To: {email}")
    print(f"Username: {username}")
    print(f"Reset Link: {reset_link}")
    print(f"=" * 70)
    
    # In production, this would use the email service
    # Example:
    # from ..utils.email import send_email
    # await send_email(
    #     to=email,
    #     subject="EchoFort - Password Reset Request",
    #     body=f"Click here to reset your password: {reset_link}"
    # )

@router.post("/forgot-password")
async def forgot_password(payload: dict, request: Request):
    """
    Step 1: Request password reset
    
    Input: { "identifier": "email-or-username" }
    
    Returns generic message regardless of whether account exists
    (security best practice - don't leak which accounts exist)
    """
    try:
        identifier = payload.get("identifier", "").strip()
        
        if not identifier:
            raise HTTPException(400, "Email or username required")
        
        print(f"🔐 Password reset requested for: {identifier}")
        
        # Get database connection
        try:
            db = request.app.state.db
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise HTTPException(500, f"Database connection failed: {str(e)}")
        
        try:
            # Look up employee by email or username
            # Note: employees table doesn't have email column yet
            # We'll look up by username for now
            result = await db.execute(text("""
                SELECT id, username, user_id
                FROM employees 
                WHERE username = :identifier AND (active = true OR active IS NULL)
            """), {"identifier": identifier})
            
            employee = result.fetchone()
            
            if employee:
                emp_id, emp_username, user_id = employee
                
                # Get email from users table if user_id exists
                email = None
                if user_id:
                    user_result = await db.execute(text("""
                        SELECT email FROM users WHERE id = :user_id
                    """), {"user_id": user_id})
                    user_row = user_result.fetchone()
                    if user_row:
                        email = user_row[0]
                
                # If no email found, use a placeholder (for testing)
                if not email:
                    email = f"{emp_username}@echofort.ai"
                
                # Generate reset token
                reset_token = generate_reset_token()
                token_hash = hash_token(reset_token)
                
                # Set expiry (30 minutes from now)
                expires_at = datetime.utcnow() + timedelta(minutes=30)
                
                # Store token hash in database
                await db.execute(text("""
                    INSERT INTO password_reset_tokens 
                    (employee_id, token_hash, expires_at)
                    VALUES (:employee_id, :token_hash, :expires_at)
                """), {
                    "employee_id": emp_id,
                    "token_hash": token_hash,
                    "expires_at": expires_at
                })
                
                # Send reset email
                await send_reset_email(email, emp_username, reset_token)
                
                print(f"✅ Password reset email sent to: {email}")
            else:
                print(f"⚠️  Account not found: {identifier}")
        
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Database error: {e}")
            raise HTTPException(500, f"Failed to process request: {str(e)}")
        
        # Always return generic message (security best practice)
        return {
            "success": True,
            "message": "If an account exists, a reset link has been sent to the associated email"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in forgot_password: {e}")
        raise HTTPException(500, f"Password reset request failed: {str(e)}")

@router.post("/reset-password")
async def reset_password(payload: dict, request: Request):
    """
    Step 2: Reset password using token
    
    Input: { "token": "<raw-token>", "new_password": "<string>" }
    
    Returns success message if token is valid and password is updated
    """
    try:
        token = payload.get("token", "").strip()
        new_password = payload.get("new_password", "").strip()
        
        if not token:
            raise HTTPException(400, "Reset token required")
        
        if not new_password:
            raise HTTPException(400, "New password required")
        
        if len(new_password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")
        
        print(f"🔐 Password reset attempt with token: {token[:10]}...")
        
        # Get database connection
        try:
            db = request.app.state.db
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise HTTPException(500, f"Database connection failed: {str(e)}")
        
        try:
            # Hash the provided token
            token_hash = hash_token(token)
            
            # Look up token in database
            result = await db.execute(text("""
                SELECT id, employee_id, expires_at, used_at
                FROM password_reset_tokens
                WHERE token_hash = :token_hash
            """), {"token_hash": token_hash})
            
            token_row = result.fetchone()
            
            if not token_row:
                print(f"❌ Invalid token: {token[:10]}...")
                raise HTTPException(400, "Invalid or expired reset token")
            
            token_id, employee_id, expires_at, used_at = token_row
            
            # Check if token has been used
            if used_at:
                print(f"❌ Token already used: {token[:10]}...")
                raise HTTPException(400, "Reset token has already been used")
            
            # Check if token has expired
            if datetime.utcnow() > expires_at:
                print(f"❌ Token expired: {token[:10]}...")
                raise HTTPException(400, "Reset token has expired")
            
            # Hash the new password using bcrypt
            import bcrypt
            password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            
            # Update employee's password
            await db.execute(text("""
                UPDATE employees
                SET password_hash = :password_hash,
                    updated_at = NOW()
                WHERE id = :employee_id
            """), {
                "password_hash": password_hash,
                "employee_id": employee_id
            })
            
            # Mark token as used
            await db.execute(text("""
                UPDATE password_reset_tokens
                SET used_at = NOW()
                WHERE id = :token_id
            """), {"token_id": token_id})
            
            # Get employee info for logging
            emp_result = await db.execute(text("""
                SELECT username, role, is_super_admin
                FROM employees
                WHERE id = :employee_id
            """), {"employee_id": employee_id})
            
            emp_row = emp_result.fetchone()
            if emp_row:
                emp_username, emp_role, is_super_admin = emp_row
                
                print(f"✅ Password reset successful for: {emp_username} (role: {emp_role})")
                
                # Log security event for SuperAdmin password resets
                if is_super_admin:
                    print(f"🔒 SECURITY EVENT: SuperAdmin password reset - {emp_username}")
                    # TODO: Log to config_changes or security_events table
            
            return {
                "success": True,
                "message": "Password has been reset successfully. You can now log in with your new password."
            }
        
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Database error: {e}")
            raise HTTPException(500, f"Failed to reset password: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in reset_password: {e}")
        raise HTTPException(500, f"Password reset failed: {str(e)}")
