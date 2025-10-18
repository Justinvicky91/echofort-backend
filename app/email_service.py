# app/email_service.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "mail.privateemail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("SMTP_FROM", "noreply@echofort.ai")
        self.support_email = os.getenv("SUPPORT_EMAIL", "support@echofort.ai")
        self.support_ticket_email = os.getenv("SUPPORT_TICKET_EMAIL", "support@echofort.io")
    
    def send_otp(self, to_email: str, otp_code: str, phone: str = ""):
        """Send OTP via email"""
        subject = "Your EchoFort OTP Code"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            <tr>
                                <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                                    <h1 style="color: white; margin: 0; font-size: 28px;">EchoFort</h1>
                                    <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0; font-size: 14px;">Real-time Scam Protection</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px 30px;">
                                    <h2 style="color: #333; margin: 0 0 15px 0; font-size: 22px;">Your Security Code</h2>
                                    <p style="color: #666; line-height: 1.6; margin: 0 0 25px 0;">Enter this code to verify your account:</p>
                                    <div style="background: #f8f9fa; padding: 25px; text-align: center; border-radius: 8px; margin: 25px 0;">
                                        <div style="color: #667eea; font-size: 42px; font-weight: bold; letter-spacing: 10px; font-family: 'Courier New', monospace;">{otp_code}</div>
                                    </div>
                                    <table width="100%" cellpadding="0" cellspacing="0" style="margin: 25px 0;">
                                        <tr><td style="padding: 8px 0; color: #666; font-size: 14px;"><strong>Phone:</strong> {phone or "Not provided"}</td></tr>
                                        <tr><td style="padding: 8px 0; color: #666; font-size: 14px;"><strong>Valid for:</strong> 5 minutes</td></tr>
                                    </table>
                                    <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 25px 0; border-radius: 4px;">
                                        <p style="margin: 0; color: #856404; font-size: 13px;"><strong>⚠️ Security Notice:</strong> Never share this code with anyone. EchoFort will never ask for your OTP.</p>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="background: #f8f9fa; padding: 25px 30px; border-top: 1px solid #e9ecef;">
                                    <p style="color: #999; font-size: 12px; margin: 0 0 10px 0;">If you didn't request this code, please ignore this email.</p>
                                    <p style="color: #999; font-size: 12px; margin: 0;">Need help? Contact us at <a href="mailto:{self.support_email}" style="color: #667eea; text-decoration: none;">{self.support_email}</a></p>
                                </td>
                            </tr>
                            <tr>
                                <td style="background: #333; padding: 20px; text-align: center;">
                                    <p style="color: #999; font-size: 12px; margin: 0;">© 2025 EchoFort AI | India's Trust Shield Against Scams</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        return self._send_email(to_email, subject, html)
    
    def send_welcome_email(self, to_email: str, name: str):
        """Send welcome email after signup"""
        subject = "Welcome to EchoFort! 🎉"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            <tr>
                                <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                                    <h1 style="color: white; margin: 0; font-size: 32px;">Welcome to EchoFort!</h1>
                                    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">🎉 Your journey to safer digital life starts now</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px 30px;">
                                    <h2 style="color: #333; margin: 0 0 15px 0; font-size: 24px;">Hi {name},</h2>
                                    <p style="color: #666; line-height: 1.8; margin: 0 0 25px 0; font-size: 15px;">Thank you for joining <strong>India's first real-time scam protection platform</strong>! We're excited to have you onboard.</p>
                                    <div style="background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); padding: 25px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #ffc107;">
                                        <h3 style="color: #856404; margin: 0 0 10px 0; font-size: 20px;">🎁 Your 48-Hour Trial is Active!</h3>
                                        <p style="color: #856404; margin: 0; font-size: 14px;">Explore all premium features absolutely free for the next 48 hours.</p>
                                    </div>
                                    <h3 style="color: #333; margin: 30px 0 15px 0; font-size: 18px;">What You Get:</h3>
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr><td style="padding: 10px 0;"><span style="color: #28a745; font-size: 18px;">✓</span> <span style="color: #666; margin-left: 10px;">Real-time call analysis with AI</span></td></tr>
                                        <tr><td style="padding: 10px 0;"><span style="color: #28a745; font-size: 18px;">✓</span> <span style="color: #666; margin-left: 10px;">Trust Factor scoring (0-10)</span></td></tr>
                                        <tr><td style="padding: 10px 0;"><span style="color: #28a745; font-size: 18px;">✓</span> <span style="color: #666; margin-left: 10px;">Voice warnings during suspicious calls</span></td></tr>
                                        <tr><td style="padding: 10px 0;"><span style="color: #28a745; font-size: 18px;">✓</span> <span style="color: #666; margin-left: 10px;">Access to evidence library with real scam cases</span></td></tr>
                                        <tr><td style="padding: 10px 0;"><span style="color: #28a745; font-size: 18px;">✓</span> <span style="color: #666; margin-left: 10px;">24/7 protection for you and your family</span></td></tr>
                                    </table>
                                    <div style="text-align: center; margin: 35px 0;">
                                        <a href="https://echofort.ai/dashboard" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 40px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">Visit Your Dashboard →</a>
                                    </div>
                                    <div style="background: #f8f9fa; padding: 25px; border-radius: 8px; margin: 25px 0;">
                                        <h3 style="color: #333; margin: 0 0 15px 0; font-size: 18px;">📱 Next Steps:</h3>
                                        <ol style="color: #666; line-height: 1.8; margin: 0; padding-left: 20px;">
                                            <li>Download the EchoFort mobile app (Android coming soon!)</li>
                                            <li>Enable call analysis permissions</li>
                                            <li>Test with a voice call to see the magic ✨</li>
                                        </ol>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="background: #f8f9fa; padding: 25px 30px; border-top: 1px solid #e9ecef;">
                                    <p style="color: #666; font-size: 14px; margin: 0 0 10px 0; text-align: center;"><strong>Need help getting started?</strong></p>
                                    <p style="color: #999; font-size: 13px; margin: 0; text-align: center;">Reply to this email or contact us at <a href="mailto:{self.support_email}" style="color: #667eea; text-decoration: none;">{self.support_email}</a></p>
                                    <p style="color: #999; font-size: 13px; margin: 10px 0 0 0; text-align: center;">Our support team is here for you! 🤝</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="background: #333; padding: 20px; text-align: center;">
                                    <p style="color: #999; font-size: 12px; margin: 0 0 5px 0;">© 2025 EchoFort AI Private Limited</p>
                                    <p style="color: #999; font-size: 12px; margin: 0;">India's Trust Shield | <a href="https://echofort.ai" style="color: #667eea; text-decoration: none;">echofort.ai</a></p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        return self._send_email(to_email, subject, html)
    
    def _send_email(self, to_email: str, subject: str, html_body: str):
        """Internal method to send email via SMTP"""
        try:
            import ssl
            
            msg = MIMEMultipart('alternative')
            msg['From'] = f"EchoFort <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Reply-To'] = self.support_email
            
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Create secure SSL context for Gmail
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.set_debuglevel(1)  # Enable debug output
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ Email sent successfully to {to_email}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ SMTP Authentication failed: {str(e)}")
            print(f"   Check Gmail App Password is correct")
            return False
        except smtplib.SMTPException as e:
            print(f"❌ SMTP Error: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Email sending failed: {str(e)}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            return False

# Global instance
email_service = EmailService()
