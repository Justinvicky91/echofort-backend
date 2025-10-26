"""
WhatsApp OTP Service for Super Admin 2FA
Sends OTP via WhatsApp using Twilio API
"""

import os
import random
import string
from datetime import datetime, timedelta
from twilio.rest import Client

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")  # Twilio Sandbox

# Super Admin WhatsApp Number
SUPER_ADMIN_WHATSAPP = os.getenv("SUPER_ADMIN_WHATSAPP", "+919361440568")

# OTP Storage (in-memory for now, should use Redis in production)
otp_storage = {}

def generate_otp(length=6):
    """Generate random 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=length))

def send_whatsapp_otp(email: str) -> dict:
    """
    Send OTP via WhatsApp to Super Admin
    
    Args:
        email: Super Admin email (for verification)
        
    Returns:
        dict with success status and message
    """
    try:
        # Generate OTP
        otp = generate_otp()
        
        # Store OTP with expiry (5 minutes)
        otp_storage[email] = {
            'otp': otp,
            'expires_at': datetime.now() + timedelta(minutes=5),
            'attempts': 0
        }
        
        # Initialize Twilio client
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            # Fallback: Log OTP to console (development mode)
            print(f"[DEV MODE] WhatsApp OTP for {email}: {otp}")
            return {
                'success': True,
                'message': f'OTP sent to WhatsApp (DEV: {otp})',
                'dev_mode': True
            }
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Send WhatsApp message
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=f"""🔐 *EchoFort Super Admin Login*

Your verification code is: *{otp}*

This code will expire in 5 minutes.

⚠️ Never share this code with anyone.
If you didn't request this, please contact support immediately.

- EchoFort Security Team""",
            to=f"whatsapp:{SUPER_ADMIN_WHATSAPP}"
        )
        
        return {
            'success': True,
            'message': 'OTP sent to WhatsApp successfully',
            'message_sid': message.sid
        }
        
    except Exception as e:
        print(f"Error sending WhatsApp OTP: {str(e)}")
        return {
            'success': False,
            'message': f'Failed to send WhatsApp OTP: {str(e)}'
        }

def verify_whatsapp_otp(email: str, otp: str) -> dict:
    """
    Verify WhatsApp OTP
    
    Args:
        email: Super Admin email
        otp: OTP code to verify
        
    Returns:
        dict with verification result
    """
    if email not in otp_storage:
        return {
            'success': False,
            'message': 'No OTP found. Please request a new one.'
        }
    
    stored_data = otp_storage[email]
    
    # Check expiry
    if datetime.now() > stored_data['expires_at']:
        del otp_storage[email]
        return {
            'success': False,
            'message': 'OTP expired. Please request a new one.'
        }
    
    # Check attempts (max 3)
    if stored_data['attempts'] >= 3:
        del otp_storage[email]
        return {
            'success': False,
            'message': 'Too many failed attempts. Please request a new OTP.'
        }
    
    # Verify OTP
    if stored_data['otp'] == otp:
        del otp_storage[email]
        return {
            'success': True,
            'message': 'OTP verified successfully'
        }
    else:
        stored_data['attempts'] += 1
        return {
            'success': False,
            'message': f'Invalid OTP. {3 - stored_data["attempts"]} attempts remaining.'
        }

def generate_recovery_codes(count=10) -> list:
    """
    Generate backup recovery codes
    
    Args:
        count: Number of recovery codes to generate
        
    Returns:
        List of recovery codes
    """
    codes = []
    for _ in range(count):
        # Generate 8-character alphanumeric code
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        # Format as XXXX-XXXX
        formatted_code = f"{code[:4]}-{code[4:]}"
        codes.append(formatted_code)
    return codes

