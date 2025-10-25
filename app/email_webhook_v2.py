"""
Email Webhook Handler for EchoFort Support System (V2 - Form Data Support)
Receives emails from Make.com and creates support tickets
Accepts both JSON and Form Data to avoid encoding issues
"""

from fastapi import APIRouter, Request, HTTPException, Form
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# Auto-response templates (keyword matching)
AUTO_RESPONSES = {
    "pricing": {
        "keywords": ["price", "pricing", "cost", "how much", "plan", "subscription"],
        "response": """Thank you for your inquiry about EchoFort pricing!

We offer three subscription plans:

1. **Basic Plan** - ₹399/month (includes GST)
   - Real-time scam detection
   - Call screening
   - Basic protection features

2. **Personal Plan** - ₹799/month (includes GST)
   - Everything in Basic
   - Full call recording
   - GPS tracking
   - Screen time monitoring
   - Personal dashboard

3. **Family Plan** - ₹1,499/month (includes GST)
   - Everything in Personal
   - Protect up to 5 family members
   - Selective call recording (scam/harassment only)
   - Family tracking dashboard
   - Geofencing alerts

All plans include a 24-hour free trial with full money-back guarantee.

You can sign up at: https://echofort.ai/signup

If you have any questions, please reply to this email and our support team will assist you.

Best regards,
EchoFort Support Team"""
    },
    "how_it_works": {
        "keywords": ["how does it work", "how it works", "explain", "what is", "features"],
        "response": """Thank you for your interest in EchoFort!

**How EchoFort Works:**

1. **AI-Powered Call Screening**
   - Our AI analyzes incoming calls in real-time
   - Detects scam patterns, fake police calls, investment frauds
   - Blocks suspicious calls automatically

2. **Digital Arrest Protection**
   - Identifies fake CBI/police/court calls
   - Alerts you immediately
   - Auto-drafts emails to authorities

3. **Family Protection**
   - Track family members' location (on-demand)
   - Monitor children's screen time
   - Get alerts for suspicious activities

4. **Scam Database**
   - Access to 125,000+ known scam numbers
   - Real-time updates from community reports
   - Truecaller integration

**Getting Started:**
1. Sign up at https://echofort.ai/signup
2. Download the mobile app (Android/iOS)
3. Grant necessary permissions
4. You're protected!

If you have more questions, please reply to this email.

Best regards,
EchoFort Support Team"""
    },
    "refund": {
        "keywords": ["refund", "money back", "cancel", "unsubscribe", "return"],
        "response": """We're sorry to hear you're considering a refund.

**Our Refund Policy:**

- **24-hour money-back guarantee** for all plans
- **Full refund** if you cancel within 24 hours of purchase
- **Pro-rated refund** for annual plans (if canceled within 7 days)

**To request a refund:**
1. Reply to this email with your registered email and order ID
2. Our team will process your refund within 3-5 business days
3. Refund will be credited to your original payment method

**Need help instead?**
If you're facing technical issues, our support team can help! Just reply to this email and we'll assist you.

Best regards,
EchoFort Support Team"""
    },
    "technical_issue": {
        "keywords": ["not working", "error", "bug", "problem", "issue", "help", "support"],
        "response": """Thank you for contacting EchoFort Support!

We're here to help you resolve any technical issues you're experiencing.

**Common Solutions:**

1. **App not detecting calls:**
   - Ensure all permissions are granted (Phone, Microphone, Accessibility)
   - Restart the app
   - Check if battery optimization is disabled for EchoFort

2. **GPS tracking not working:**
   - Enable location permissions (Always Allow)
   - Ensure location services are turned on
   - Check internet connection

3. **Login issues:**
   - Reset password at: https://echofort.ai/reset-password
   - Clear app cache and try again
   - Contact us if issue persists

**Need personalized help?**
Please reply to this email with:
- Your registered email/phone number
- Device model and OS version
- Detailed description of the issue
- Screenshots (if applicable)

Our support team will respond within 24 hours.

Best regards,
EchoFort Support Team"""
    }
}


def detect_auto_response(subject: str, body: str) -> Optional[str]:
    """Detect if email matches any auto-response keywords"""
    content = f"{subject} {body}".lower()
    
    for category, data in AUTO_RESPONSES.items():
        for keyword in data["keywords"]:
            if keyword.lower() in content:
                return data["response"]
    
    return None


async def send_email_via_sendgrid(to_email: str, subject: str, body: str, from_email: str = "support@echofort.ai"):
    """Send email using SendGrid"""
    import os
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    
    try:
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=f"Re: {subject}",
            html_content=body.replace("\n", "<br>")
        )
        
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        
        logger.info(f"Email sent to {to_email} via SendGrid. Status: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email via SendGrid: {e}")
        return False


@router.post("/email")
async def receive_email_webhook(
    request: Request,
    from_email: str = Form(None, alias="from"),
    fromName: str = Form(None),
    to: str = Form(...),
    subject: str = Form(...),
    textPlain: str = Form(None),
    textHtml: str = Form(None),
    date: str = Form(...),
    messageId: str = Form(...)
):
    """
    Receive email webhook from Make.com (Form Data)
    This version accepts form-data to avoid JSON encoding issues with special characters
    """
    try:
        logger.info(f"Received email webhook from {from_email} - Subject: {subject}")
        
        # Validate required fields
        if not from_email:
            raise HTTPException(status_code=400, detail="Missing 'from' email address")
        
        # Get message content (prefer plain text)
        message_content = textPlain or textHtml or ""
        
        # Get database connection from request (using DBShim from main.py)
        db = request.app.state.db
        
        # Insert ticket
        ticket_query = text("""
            INSERT INTO support_tickets (
                from_email, from_name, subject, message_plain, message_html,
                email_message_id, source, status, priority, auto_response_sent, created_at
            )
            VALUES (
                :from_email, :from_name, :subject, :message_plain, :message_html,
                :message_id, 'email', 'open', 'medium', FALSE, NOW()
            )
            RETURNING id
        """)
        
        result = await db.execute(
            ticket_query,
            {
                "from_email": from_email,
                "from_name": fromName or from_email.split("@")[0],
                "subject": subject,
                "message_plain": message_content[:5000],  # Limit to 5000 chars
                "message_html": textHtml[:10000] if textHtml else None,
                "message_id": messageId
            }
        )
        
        ticket_id = result.scalar()
        logger.info(f"Created support ticket #{ticket_id}")
        
        # Check for auto-response
        auto_response = detect_auto_response(subject, message_content)
        
        if auto_response:
            # Send auto-response
            email_sent = await send_email_via_sendgrid(
                to_email=from_email,
                subject=subject,
                body=auto_response
            )
            
            if email_sent:
                # Mark ticket as auto-responded
                await db.execute(
                    text("UPDATE support_tickets SET auto_response_sent = TRUE WHERE id = :id"),
                    {"id": ticket_id}
                )
                
                # Add response to conversation
                await db.execute(
                    text("""
                        INSERT INTO ticket_responses (ticket_id, from_type, from_name, message, created_at)
                        VALUES (:ticket_id, 'system', 'EchoFort Auto-Response', :message, NOW())
                    """),
                    {"ticket_id": ticket_id, "message": auto_response}
                )
                
                logger.info(f"Auto-response sent for ticket #{ticket_id}")
        
        return {
            "ok": True,
            "ticket_id": ticket_id,
            "auto_response_sent": bool(auto_response),
            "message": "Email received and ticket created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing email webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process email: {str(e)}")


@router.get("/email/test")
async def test_email_webhook():
    """Test endpoint to verify webhook is accessible"""
    return {
        "status": "ok",
        "endpoint": "/webhooks/email",
        "method": "POST",
        "accepts": "application/x-www-form-urlencoded or multipart/form-data",
        "message": "Email webhook is ready to receive emails from Make.com"
    }

