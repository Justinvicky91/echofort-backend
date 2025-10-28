# app/email_service.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    def __init__(self):
        # Namecheap SMTP settings
        self.smtp_server = os.getenv("SMTP_HOST", "mail.privateemail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USER", "noreply@echofort.ai")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("SMTP_FROM", "noreply@echofort.ai")
        self.from_name = os.getenv("FROM_NAME", "EchoFort")
        self.support_email = os.getenv("SUPPORT_EMAIL", "support@echofort.ai")
    
    def _send_smtp_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send email via Namecheap SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach HTML body
            msg.attach(MIMEText(html_body, 'html'))
            
            # Connect to SMTP server and send
            # Try SSL first (port 465), fallback to STARTTLS (port 587)
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                    server.starttls()  # Enable TLS encryption
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            
            print(f"✅ Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_otp(self, to_email: str, otp_code: str, phone: str = ""):
        """Send OTP via Namecheap SMTP"""
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
        
        return self._send_smtp_email(to_email, subject, html)
    
    def send_welcome_email(self, to_email: str, name: str):
        """Send welcome email via Namecheap SMTP"""
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
        
        return self._send_smtp_email(to_email, subject, html)

# Global instance
email_service = EmailService()


    def send_password_reset_otp(self, to_email: str, name: str, otp_code: str):
        """Send password reset OTP via Namecheap SMTP"""
        subject = "Reset Your EchoFort Password"
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f4f4f4;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
<tr><td style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:30px;text-align:center;">
<h1 style="color:white;margin:0;font-size:28px;">EchoFort</h1>
<p style="color:rgba(255,255,255,0.9);margin:5px 0 0 0;font-size:14px;">Password Reset Request</p>
</td></tr>
<tr><td style="padding:40px 30px;">
<h2 style="color:#333;margin:0 0 15px 0;font-size:22px;">Hi {name},</h2>
<p style="color:#666;line-height:1.6;margin:0 0 25px 0;">We received a request to reset your password. Use this code to reset it:</p>
<div style="background:#f8f9fa;padding:25px;text-align:center;border-radius:8px;margin:25px 0;">
<div style="color:#667eea;font-size:42px;font-weight:bold;letter-spacing:10px;font-family:'Courier New',monospace;">{otp_code}</div>
</div>
<table width="100%" cellpadding="0" cellspacing="0" style="margin:25px 0;">
<tr><td style="padding:8px 0;color:#666;font-size:14px;"><strong>Valid for:</strong> 10 minutes</td></tr>
</table>
<div style="background:#fff3cd;border-left:4px solid #ffc107;padding:15px;margin:25px 0;border-radius:4px;">
<p style="margin:0;color:#856404;font-size:13px;"><strong>⚠️ Security Notice:</strong> If you didn't request this, please ignore this email or contact support.</p>
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
        
        return self._send_smtp_email(to_email, subject, html)

# Singleton instance
email_service = EmailService()
