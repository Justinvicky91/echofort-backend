"""
Email service using SendGrid API (works on Railway, no SMTP blocking issues)
"""
import os
import requests
from typing import Optional

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@echofort.ai")
FROM_NAME = os.getenv("FROM_NAME", "EchoFort")


def send_email_via_sendgrid(to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
    """
    Send email using SendGrid API
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        text_content: Plain text email content (optional)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not SENDGRID_API_KEY:
        print("❌ SENDGRID_API_KEY not configured")
        return False
    
    if not text_content:
        # Strip HTML tags for plain text version
        import re
        text_content = re.sub('<[^<]+?>', '', html_content)
    
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject
            }
        ],
        "from": {
            "email": SMTP_FROM,
            "name": FROM_NAME
        },
        "content": [
            {
                "type": "text/plain",
                "value": text_content
            },
            {
                "type": "text/html",
                "value": html_content
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 202:
            print(f"✅ Email sent successfully to {to_email} via SendGrid")
            return True
        else:
            print(f"❌ SendGrid API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to send email via SendGrid: {str(e)}")
        return False


def send_otp_email(to_email: str, otp_code: str) -> bool:
    """Send OTP email using SendGrid API"""
    subject = "Your EchoFort Login OTP"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your EchoFort OTP</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
        <table role="presentation" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td align="center" style="padding: 40px 0;">
                    <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="padding: 40px 30px; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: bold;">🛡️ EchoFort</h1>
                                <p style="margin: 10px 0 0 0; color: #ffffff; font-size: 14px;">India's Most Advanced Scam Protection</p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 30px;">
                                <h2 style="margin: 0 0 20px 0; color: #333333; font-size: 24px;">Your Login OTP</h2>
                                <p style="margin: 0 0 30px 0; color: #666666; font-size: 16px; line-height: 1.5;">
                                    Use the following One-Time Password (OTP) to complete your login:
                                </p>
                                
                                <!-- OTP Box -->
                                <table role="presentation" style="width: 100%; border-collapse: collapse;">
                                    <tr>
                                        <td align="center" style="padding: 20px; background-color: #f8f9fa; border: 2px dashed #667eea; border-radius: 8px;">
                                            <span style="font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 8px; font-family: 'Courier New', monospace;">{otp_code}</span>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="margin: 30px 0 0 0; color: #666666; font-size: 14px; line-height: 1.5;">
                                    ⏰ This OTP is valid for <strong>10 minutes</strong>.<br>
                                    🔒 For security reasons, do not share this OTP with anyone.
                                </p>
                                
                                <p style="margin: 30px 0 0 0; color: #999999; font-size: 13px; line-height: 1.5;">
                                    If you didn't request this OTP, please ignore this email or contact our support team.
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 30px; text-align: center; background-color: #f8f9fa; border-top: 1px solid #e9ecef;">
                                <p style="margin: 0 0 10px 0; color: #999999; font-size: 12px;">
                                    © 2025 EchoFort. All rights reserved.
                                </p>
                                <p style="margin: 0; color: #999999; font-size: 12px;">
                                    Protecting Indian families from scams with AI-powered technology.
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
    
    text_content = f"""
    EchoFort - Your Login OTP
    
    Your One-Time Password (OTP) is: {otp_code}
    
    This OTP is valid for 10 minutes.
    For security reasons, do not share this OTP with anyone.
    
    If you didn't request this OTP, please ignore this email.
    
    © 2025 EchoFort. All rights reserved.
    """
    
    return send_email_via_sendgrid(to_email, subject, html_content, text_content)

