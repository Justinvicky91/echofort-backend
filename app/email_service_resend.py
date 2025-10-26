"""
Resend Email Service for EchoFort
Sends OTP emails using Resend API
"""
import os
import httpx
from typing import Optional

# Resend API configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_API_URL = "https://api.resend.com/emails"
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@echofort.ai")
FROM_NAME = os.getenv("FROM_NAME", "EchoFort")


def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Send OTP email using Resend API
    
    Args:
        to_email: Recipient email address
        otp_code: 6-digit OTP code
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not RESEND_API_KEY:
        print("❌ RESEND_API_KEY not configured")
        return False
    
    # Email HTML template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your OTP Code</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
        <table role="presentation" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td align="center" style="padding: 40px 0;">
                    <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="padding: 40px 40px 20px 40px; text-align: center;">
                                <h1 style="margin: 0; font-size: 28px; font-weight: 600; color: #1a1a1a;">EchoFort</h1>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 20px 40px;">
                                <h2 style="margin: 0 0 20px 0; font-size: 20px; font-weight: 600; color: #1a1a1a;">Your One-Time Password</h2>
                                <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 24px; color: #4a4a4a;">
                                    Use the following OTP to complete your login:
                                </p>
                            </td>
                        </tr>
                        
                        <!-- OTP Code -->
                        <tr>
                            <td style="padding: 0 40px 30px 40px; text-align: center;">
                                <div style="background-color: #f8f9fa; border-radius: 8px; padding: 24px; display: inline-block;">
                                    <span style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #2563eb; font-family: 'Courier New', monospace;">
                                        {otp_code}
                                    </span>
                                </div>
                            </td>
                        </tr>
                        
                        <!-- Warning -->
                        <tr>
                            <td style="padding: 0 40px 30px 40px;">
                                <p style="margin: 0; font-size: 14px; line-height: 20px; color: #6b7280;">
                                    ⏱️ This OTP will expire in <strong>10 minutes</strong>.
                                </p>
                                <p style="margin: 12px 0 0 0; font-size: 14px; line-height: 20px; color: #6b7280;">
                                    🔒 For security reasons, do not share this code with anyone.
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 30px 40px; border-top: 1px solid #e5e7eb;">
                                <p style="margin: 0; font-size: 12px; line-height: 18px; color: #9ca3af; text-align: center;">
                                    If you didn't request this code, please ignore this email.
                                </p>
                                <p style="margin: 8px 0 0 0; font-size: 12px; line-height: 18px; color: #9ca3af; text-align: center;">
                                    © 2025 EchoFort. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    # Plain text fallback
    text_content = f"""
    Your EchoFort OTP Code
    
    Use the following OTP to complete your login:
    
    {otp_code}
    
    This OTP will expire in 10 minutes.
    For security reasons, do not share this code with anyone.
    
    If you didn't request this code, please ignore this email.
    
    © 2025 EchoFort. All rights reserved.
    """
    
    # Prepare request payload
    payload = {
        "from": f"{FROM_NAME} <{FROM_EMAIL}>",
        "to": [to_email],
        "subject": f"Your EchoFort OTP Code: {otp_code}",
        "html": html_content,
        "text": text_content.strip()
    }
    
    # Send request to Resend API
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"📧 Sending OTP email to {to_email} via Resend API...")
        with httpx.Client() as client:
            response = client.post(
                RESEND_API_URL,
                json=payload,
                headers=headers,
                timeout=30.0
            )
        
        if response.status_code == 200:
            result = response.json()
            email_id = result.get("id", "unknown")
            print(f"✅ Email sent successfully! ID: {email_id}")
            return True
        else:
            error_data = response.json()
            print(f"❌ Resend API error: {response.status_code} - {error_data}")
            return False
            
    except httpx.TimeoutException:
        print(f"❌ Resend API timeout after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False


def send_email(to_email: str, subject: str, body: str, html: Optional[str] = None) -> bool:
    """
    Send a generic email using Resend API
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text email body
        html: Optional HTML email body
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not RESEND_API_KEY:
        print("❌ RESEND_API_KEY not configured")
        return False
    
    payload = {
        "from": f"{FROM_NAME} <{FROM_EMAIL}>",
        "to": [to_email],
        "subject": subject,
        "text": body
    }
    
    if html:
        payload["html"] = html
    
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"📧 Sending email to {to_email} via Resend API...")
        with httpx.Client() as client:
            response = client.post(
                RESEND_API_URL,
                json=payload,
                headers=headers,
                timeout=30.0
            )
        
        if response.status_code == 200:
            result = response.json()
            email_id = result.get("id", "unknown")
            print(f"✅ Email sent successfully! ID: {email_id}")
            return True
        else:
            error_data = response.json()
            print(f"❌ Resend API error: {response.status_code} - {error_data}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False

