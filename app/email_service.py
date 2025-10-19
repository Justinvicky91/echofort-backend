# app/email_service.py
import os
import requests

class EmailService:
    def __init__(self):
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("SMTP_FROM", "noreply@echofort.ai")
        self.support_email = os.getenv("SUPPORT_EMAIL", "support@echofort.ai")
    
    def send_otp(self, to_email: str, otp_code: str, phone: str = ""):
        """Send OTP via SendGrid"""
        subject = "Your EchoFort OTP Code"
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f4f4f4;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
<tr><td style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:30px;text-align:center;">
<h1 style="color:white;margin:0;font-size:28px;">EchoFort</h1>
<p style="color:rgba(255,255,255,0.9);margin:5px 0 0 0;font-size:14px;">Real-time Scam Protection</p>
</td></tr>
<tr><td style="padding:40px 30px;">
<h2 style="color:#333;margin:0 0 15px 0;font-size:22px;">Your Security Code</h2>
<p style="color:#666;line-height:1.6;margin:0 0 25px 0;">Enter this code to verify your account:</p>
<div style="background:#f8f9fa;padding:25px;text-align:center;border-radius:8px;margin:25px 0;">
<div style="color:#667eea;font-size:42px;font-weight:bold;letter-spacing:10px;font-family:'Courier New',monospace;">{otp_code}</div>
</div>
<table width="100%" cellpadding="0" cellspacing="0" style="margin:25px 0;">
<tr><td style="padding:8px 0;color:#666;font-size:14px;"><strong>Phone:</strong> {phone or "Not provided"}</td></tr>
<tr><td style="padding:8px 0;color:#666;font-size:14px;"><strong>Valid for:</strong> 5 minutes</td></tr>
</table>
<div style="background:#fff3cd;border-left:4px solid #ffc107;padding:15px;margin:25px 0;border-radius:4px;">
<p style="margin:0;color:#856404;font-size:13px;"><strong>⚠️ Security Notice:</strong> Never share this code.</p>
</div>
</td></tr>
<tr><td style="background:#f8f9fa;padding:25px 30px;border-top:1px solid #e9ecef;">
<p style="color:#999;font-size:12px;margin:0;">Need help? Contact {self.support_email}</p>
</td></tr>
<tr><td style="background:#333;padding:20px;text-align:center;">
<p style="color:#999;font-size:12px;margin:0;">© 2025 EchoFort AI | India's Trust Shield</p>
</td></tr>
</table></td></tr></table>
</body></html>"""
        
        return self._send_via_sendgrid(to_email, subject, html)
    
    def send_welcome_email(self, to_email: str, name: str):
        """Send welcome email via SendGrid"""
        subject = "Welcome to EchoFort! 🎉"
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f4f4f4;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:8px;overflow:hidden;">
<tr><td style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:40px 30px;text-align:center;">
<h1 style="color:white;margin:0;font-size:32px;">Welcome to EchoFort!</h1>
<p style="color:rgba(255,255,255,0.9);margin:10px 0 0 0;">🎉 Your journey to safer digital life starts now</p>
</td></tr>
<tr><td style="padding:40px 30px;">
<h2 style="color:#333;margin:0 0 15px 0;font-size:24px;">Hi {name},</h2>
<p style="color:#666;line-height:1.8;">Thank you for joining <strong>India's first real-time scam protection platform</strong>!</p>
<div style="background:linear-gradient(135deg,#fff3cd 0%,#ffeaa7 100%);padding:25px;border-radius:8px;margin:25px 0;border-left:4px solid #ffc107;">
<h3 style="color:#856404;margin:0 0 10px 0;font-size:20px;">🎁 Your 48-Hour Trial is Active!</h3>
<p style="color:#856404;margin:0;font-size:14px;">Explore all premium features absolutely free.</p>
</div>
<h3 style="color:#333;margin:30px 0 15px 0;">What You Get:</h3>
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:10px 0;"><span style="color:#28a745;font-size:18px;">✓</span> <span style="color:#666;margin-left:10px;">Real-time call analysis with AI</span></td></tr>
<tr><td style="padding:10px 0;"><span style="color:#28a745;font-size:18px;">✓</span> <span style="color:#666;margin-left:10px;">Trust Factor scoring (0-10)</span></td></tr>
<tr><td style="padding:10px 0;"><span style="color:#28a745;font-size:18px;">✓</span> <span style="color:#666;margin-left:10px;">Voice warnings during calls</span></td></tr>
<tr><td style="padding:10px 0;"><span style="color:#28a745;font-size:18px;">✓</span> <span style="color:#666;margin-left:10px;">Evidence library access</span></td></tr>
<tr><td style="padding:10px 0;"><span style="color:#28a745;font-size:18px;">✓</span> <span style="color:#666;margin-left:10px;">24/7 protection</span></td></tr>
</table>
</td></tr>
<tr><td style="background:#f8f9fa;padding:25px 30px;border-top:1px solid #e9ecef;">
<p style="color:#666;font-size:14px;margin:0;text-align:center;"><strong>Need help?</strong></p>
<p style="color:#999;font-size:13px;margin:5px 0 0 0;text-align:center;">Contact {self.support_email}</p>
</td></tr>
<tr><td style="background:#333;padding:20px;text-align:center;">
<p style="color:#999;font-size:12px;margin:0;">© 2025 EchoFort AI | <a href="https://echofort.ai" style="color:#667eea;">echofort.ai</a></p>
</td></tr>
</table></td></tr></table>
</body></html>"""
        
        return self._send_via_sendgrid(to_email, subject, html)
    
    def _send_via_sendgrid(self, to_email: str, subject: str, html_body: str):
        """Send email using SendGrid API"""
        if not self.sendgrid_api_key:
            print("❌ SENDGRID_API_KEY not configured")
            return False
        
        try:
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "personalizations": [{
                    "to": [{"email": to_email}]
                }],
                "from": {
                    "email": self.from_email,
                    "name": "EchoFort"
                },
                "subject": subject,
                "content": [{
                    "type": "text/html",
                    "value": html_body
                }]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 202:
                print(f"✅ Email sent successfully to {to_email}")
                return True
            else:
                print(f"❌ SendGrid error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Email sending failed: {str(e)}")
            return False

# Global instance
email_service = EmailService()
