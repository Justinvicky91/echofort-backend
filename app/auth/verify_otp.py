"""
BLOCK S2 - OTP Verification API
Verifies OTP and generates JWT token for authenticated sessions
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.deps import get_settings
import psycopg
from datetime import datetime, timedelta
import jwt

router = APIRouter(prefix="/auth", tags=["auth"])

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class VerifyOTPResponse(BaseModel):
    verified: bool
    token: str
    dashboard_url: str
    user: dict

def generate_jwt_token(user_id: int, email: str, dashboard_type: str = None) -> str:
    """Generate JWT token for authenticated user"""
    settings = get_settings()
    
    # Use a secret key from settings or generate one
    # In production, this should be a strong secret stored in environment variables
    secret_key = getattr(settings, 'JWT_SECRET_KEY', 'echofort-jwt-secret-key-change-in-production')
    
    payload = {
        'user_id': user_id,
        'email': email,
        'dashboard_type': dashboard_type,
        'exp': datetime.utcnow() + timedelta(days=30),  # Token expires in 30 days
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token

@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(req: VerifyOTPRequest):
    """
    Verify OTP and generate JWT token for user session
    """
    settings = get_settings()
    dsn = settings.DATABASE_URL
    
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # Check if user exists
                cur.execute("""
                    SELECT id, email, name, otp_verified, dashboard_type, plan_id, subscription_status
                    FROM users 
                    WHERE email = %s
                """, (req.email,))
                
                user_row = cur.fetchone()
                if not user_row:
                    raise HTTPException(status_code=404, detail="User not found")
                
                user_id, email, name, otp_verified, dashboard_type, plan_id, subscription_status = user_row
                
                # If already verified, just generate a new token
                if otp_verified:
                    print(f"[VERIFY_OTP] User {user_id} already verified, generating new token", flush=True)
                    token = generate_jwt_token(user_id, email, dashboard_type)
                    
                    # Determine dashboard URL based on dashboard_type
                    if dashboard_type == 'basic':
                        dashboard_url = '/dashboard/basic'
                    elif dashboard_type == 'personal':
                        dashboard_url = '/dashboard/personal'
                    elif dashboard_type == 'family_admin':
                        dashboard_url = '/dashboard/family'
                    else:
                        # No subscription yet - redirect to pricing/payment
                        dashboard_url = '/pricing'
                    
                    return VerifyOTPResponse(
                        verified=True,
                        token=token,
                        dashboard_url=dashboard_url,
                        user={
                            'id': user_id,
                            'email': email,
                            'name': name,
                            'plan_id': plan_id,
                            'subscription_status': subscription_status,
                            'dashboard_type': dashboard_type
                        }
                    )
                
                # Verify OTP
                cur.execute("""
                    SELECT id, code, expires_at 
                    FROM otps 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (user_id,))
                
                otp_row = cur.fetchone()
                if not otp_row:
                    raise HTTPException(status_code=400, detail="No OTP found for this user")
                
                otp_id, stored_otp, expires_at = otp_row
                
                # Check if OTP has expired
                if datetime.utcnow() > expires_at:
                    raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
                
                # Verify OTP matches
                if req.otp != stored_otp:
                    print(f"[VERIFY_OTP] Invalid OTP for user {user_id}: expected {stored_otp}, got {req.otp}", flush=True)
                    raise HTTPException(status_code=400, detail="Invalid OTP. Please try again.")
                
                # OTP is valid - mark user as verified
                cur.execute("""
                    UPDATE users 
                    SET otp_verified = true, updated_at = NOW()
                    WHERE id = %s
                """, (req.user_id,))
                
                # Delete used OTP
                cur.execute("DELETE FROM otps WHERE id = %s", (otp_id,))
                
                conn.commit()
                print(f"[VERIFY_OTP] User {user_id} ({email}) verified successfully", flush=True)
                
                # Generate JWT token
                token = generate_jwt_token(user_id, email, dashboard_type)
                
                # User is verified but has no subscription yet - redirect to pricing
                dashboard_url = '/pricing'
                
                return VerifyOTPResponse(
                    verified=True,
                    token=token,
                    dashboard_url=dashboard_url,
                    user={
                        'id': user_id,
                        'email': email,
                        'name': name,
                        'plan_id': None,
                        'subscription_status': 'inactive',
                        'dashboard_type': None
                    }
                )
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VERIFY_OTP] Error during OTP verification: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail="OTP verification failed. Please try again.")
