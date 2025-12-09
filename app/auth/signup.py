"""
BLOCK S2 - User Signup API
Handles user registration with OTP verification
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, validator
from app.deps import get_settings
import psycopg
import random
import re
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

router = APIRouter(prefix="/auth", tags=["auth"])

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    country: str = "India"
    state: str
    district: str
    
    @validator('phone')
    def validate_phone(cls, v):
        # Remove spaces and dashes
        phone = re.sub(r'[\s\-]', '', v)
        # Check if it's a valid Indian phone number (10 digits) or international format
        if not re.match(r'^\+?[1-9]\d{9,14}$', phone):
            raise ValueError('Invalid phone number format')
        return phone
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v.strip()

class SignupResponse(BaseModel):
    status: str
    user_id: int
    email: str
    message: str

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def send_otp_email(email: str, otp: str, name: str):
    """Send OTP via SendGrid"""
    settings = get_settings()
    
    message = Mail(
        from_email='noreply@echofort.ai',
        to_emails=email,
        subject='Your EchoFort Verification Code',
        html_content=f'''
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background-color: #4F46E5; padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">EchoFort</h1>
                    <p style="color: #E0E7FF; margin: 5px 0;">India's Most Advanced Scam Protection</p>
                </div>
                
                <div style="background-color: white; padding: 30px; margin-top: 20px; border-radius: 5px;">
                    <h2 style="color: #4F46E5;">Welcome, {name}!</h2>
                    <p>Thank you for signing up with EchoFort. To complete your registration, please verify your email address.</p>
                    
                    <div style="background-color: #F3F4F6; padding: 20px; text-align: center; margin: 30px 0; border-radius: 5px;">
                        <p style="margin: 0; font-size: 14px; color: #6B7280;">Your Verification Code</p>
                        <h1 style="font-size: 36px; letter-spacing: 8px; margin: 10px 0; color: #4F46E5;">{otp}</h1>
                        <p style="margin: 0; font-size: 12px; color: #9CA3AF;">This code will expire in 5 minutes</p>
                    </div>
                    
                    <p>If you didn't request this code, please ignore this email.</p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 12px; color: #6B7280;">
                            Need help? Contact us at <a href="mailto:support@echofort.ai" style="color: #4F46E5;">support@echofort.ai</a>
                        </p>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 20px; color: #6B7280; font-size: 12px;">
                    <p>&copy; 2025 EchoFort Technologies. Protecting India from scams.</p>
                </div>
            </div>
        </body>
        </html>
        '''
    )
    
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"[SIGNUP] OTP email sent to {email}, status: {response.status_code}", flush=True)
        return True
    except Exception as e:
        print(f"[SIGNUP] Failed to send OTP email to {email}: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail="Failed to send verification email")

@router.post("/signup", response_model=SignupResponse)
async def signup(req: SignupRequest):
    """
    User signup endpoint - creates user account and sends OTP for verification
    """
    settings = get_settings()
    dsn = settings.DATABASE_URL
    
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # Check if email already exists
                cur.execute("SELECT id, otp_verified FROM users WHERE email = %s", (req.email,))
                existing_user = cur.fetchone()
                
                if existing_user:
                    user_id, otp_verified = existing_user
                    if otp_verified:
                        raise HTTPException(
                            status_code=400, 
                            detail="Email already registered. Please login instead."
                        )
                    else:
                        # User exists but not verified - resend OTP
                        print(f"[SIGNUP] User {user_id} exists but not verified, resending OTP", flush=True)
                else:
                    # Create new user
                    cur.execute("""
                        INSERT INTO users (
                            identity, email, name, phone, country, state, district,
                            otp_verified, plan_id, subscription_status, dashboard_type,
                            created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s,
                            false, null, 'inactive', null,
                            NOW()
                        ) RETURNING id
                    """, (
                        req.email,  # identity = email for now
                        req.email,
                        req.name,
                        req.phone,
                        req.country,
                        req.state,
                        req.district
                    ))
                    user_id = cur.fetchone()[0]
                    print(f"[SIGNUP] Created new user {user_id} for {req.email}", flush=True)
                
                # Generate OTP
                otp = generate_otp()
                expires_at = datetime.utcnow() + timedelta(minutes=5)
                
                # Save OTP to database
                cur.execute("""
                    INSERT INTO otps (identity, code, expires_at, user_id, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (req.email, otp, expires_at, user_id))
                
                conn.commit()
                print(f"[SIGNUP] OTP generated for user {user_id}: {otp} (expires at {expires_at})", flush=True)
                
                # Send OTP email
                send_otp_email(req.email, otp, req.name)
                
                return SignupResponse(
                    status="otp_sent",
                    user_id=user_id,
                    email=req.email,
                    message=f"Verification code sent to {req.email}. Please check your inbox."
                )
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SIGNUP] Error during signup: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail="Signup failed. Please try again.")
