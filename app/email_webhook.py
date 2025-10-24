"""
Email Webhook Handler for EchoFort Support System
Receives emails from Make.com and creates support tickets
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class EmailWebhookPayload(BaseModel):
    """Email data from Make.com Gmail module"""
    from_email: EmailStr = None  # Renamed from 'from' to avoid Python keyword
    fromName: Optional[str] = None
    to: str
    subject: str
    textPlain: Optional[str] = None
    textHtml: Optional[str] = None
    date: str
    messageId: str
    
    class Config:
        # Allow 'from' field to be mapped to 'from_email'
        fields = {'from_email': 'from'}


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

24-hour free trial available. No credit card required.

For more details, visit: https://echofort.ai/features

Best regards,
EchoFort Support Team"""
    },
    "refund": {
        "keywords": ["refund", "money back", "cancel", "cancellation", "unsubscribe"],
        "response": """Thank you for contacting EchoFort support regarding refunds.

**Our Refund Policy:**

- **24-Hour Money-Back Guarantee**: Full refund if you cancel within 24 hours of purchase
- **No Questions Asked**: We process refunds immediately
- **Refund Timeline**: 5-7 business days to your original payment method

**To Request a Refund:**
1. Reply to this email with your registered email address
2. Our team will process your refund within 24 hours
3. You'll receive a confirmation email

**Note:** After 24 hours, refunds are not available, but you can cancel your subscription anytime to avoid future charges.

For more details, see our Refund Policy: https://echofort.ai/refund

A support agent will follow up with you shortly.

Best regards,
EchoFort Support Team"""
    },
    "technical_issue": {
        "keywords": ["not working", "error", "bug", "problem", "issue", "crash", "freeze"],
        "response": """Thank you for reporting a technical issue with EchoFort.

We're sorry you're experiencing problems. Our technical team will investigate and respond within 24 hours.

**In the meantime, please try these steps:**

1. **Restart the app**
   - Close EchoFort completely
   - Reopen and check if issue persists

2. **Check permissions**
   - Go to Settings → Apps → EchoFort
   - Ensure all permissions are granted

3. **Update the app**
   - Check Google Play/App Store for updates
   - Install latest version

4. **Clear cache** (if issue persists)
   - Settings → Apps → EchoFort → Storage → Clear Cache

**Please provide these details in your reply:**
- Device model and Android/iOS version
- EchoFort app version
- Exact error message (if any)
- Steps to reproduce the issue

Our support team will prioritize your ticket and respond soon.

Best regards,
EchoFort Support Team"""
    }
}


def find_auto_response(subject: str, body: str) -> Optional[str]:
    """Check if email matches any auto-response keywords"""
    combined_text = f"{subject} {body}".lower()
    
    for category, data in AUTO_RESPONSES.items():
        for keyword in data["keywords"]:
            if keyword.lower() in combined_text:
                logger.info(f"Auto-response matched: {category} (keyword: {keyword})")
                return data["response"]
    
    return None


async def send_email_via_sendgrid(to_email: str, subject: str, body: str, request: Request):
    """Send email using SendGrid API"""
    try:
        import httpx
        import os
        
        sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        if not sendgrid_api_key:
            logger.error("SENDGRID_API_KEY not configured")
            return False
        
        from_email = os.getenv("HELLO_EMAIL", "noreply@echofort.ai")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {sendgrid_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "personalizations": [{
                        "to": [{"email": to_email}],
                        "subject": subject
                    }],
                    "from": {"email": from_email, "name": "EchoFort Support"},
                    "reply_to": {"email": "support@echofort.ai", "name": "EchoFort Support"},
                    "content": [{
                        "type": "text/plain",
                        "value": body
                    }]
                },
                timeout=10.0
            )
            
            if response.status_code == 202:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False


@router.post("/email")
async def receive_email_webhook(payload: dict, request: Request):
    """
    Webhook endpoint for receiving emails from Make.com
    
    Flow:
    1. Customer sends email to support@echofort.ai
    2. Cloudflare forwards to Echofortai@gmail.com
    3. Make.com detects email in Gmail
    4. Make.com sends POST to this endpoint
    5. Create ticket in database
    6. Check for auto-response
    7. Send auto-response or acknowledgment
    """
    try:
        logger.info(f"Email webhook received: {payload}")
        
        # Extract email data (handle both 'from' and 'from_email' keys)
        from_email = payload.get("from") or payload.get("from_email")
        from_name = payload.get("fromName") or payload.get("from_name") or "Unknown"
        to_email = payload.get("to", "support@echofort.ai")
        subject = payload.get("subject", "No Subject")
        text_plain = payload.get("textPlain") or payload.get("text_plain") or ""
        text_html = payload.get("textHtml") or payload.get("text_html") or ""
        date_str = payload.get("date", datetime.utcnow().isoformat())
        message_id = payload.get("messageId") or payload.get("message_id") or f"msg-{datetime.utcnow().timestamp()}"
        
        if not from_email:
            raise HTTPException(status_code=400, detail="Missing 'from' email address")
        
        # Get database connection
        db = request.app.state.db
        
        # Check if ticket already exists (prevent duplicates)
        existing = await db.execute(
            text("SELECT id FROM support_tickets WHERE email_message_id = :msg_id"),
            {"msg_id": message_id}
        )
        if existing.fetchone():
            logger.info(f"Ticket already exists for message_id: {message_id}")
            return {"success": True, "message": "Ticket already exists", "duplicate": True}
        
        # Determine priority based on keywords
        priority = "medium"
        urgent_keywords = ["urgent", "emergency", "asap", "critical", "scam", "fraud", "hacked"]
        if any(keyword in subject.lower() or keyword in text_plain.lower() for keyword in urgent_keywords):
            priority = "urgent"
        
        # Create support ticket
        result = await db.execute(
            text("""
                INSERT INTO support_tickets (
                    from_email, from_name, subject, message_plain, message_html,
                    email_message_id, status, priority, source, created_at
                )
                VALUES (
                    :from_email, :from_name, :subject, :message_plain, :message_html,
                    :message_id, 'open', :priority, 'email', NOW()
                )
                RETURNING id
            """),
            {
                "from_email": from_email,
                "from_name": from_name,
                "subject": subject,
                "message_plain": text_plain,
                "message_html": text_html,
                "message_id": message_id,
                "priority": priority
            }
        )
        
        ticket_id = result.fetchone()[0]
        logger.info(f"Support ticket created: #{ticket_id}")
        
        # Check for auto-response
        auto_response = find_auto_response(subject, text_plain)
        
        if auto_response:
            # Send auto-response
            await send_email_via_sendgrid(
                to_email=from_email,
                subject=f"Re: {subject}",
                body=auto_response,
                request=request
            )
            
            # Update ticket status
            await db.execute(
                text("""
                    UPDATE support_tickets
                    SET status = 'auto_responded', auto_response_sent = TRUE
                    WHERE id = :ticket_id
                """),
                {"ticket_id": ticket_id}
            )
            
            # Log auto-response in conversation
            await db.execute(
                text("""
                    INSERT INTO ticket_responses (
                        ticket_id, from_type, from_name, message, created_at
                    )
                    VALUES (:ticket_id, 'system', 'EchoFort Bot', :message, NOW())
                """),
                {"ticket_id": ticket_id, "message": auto_response}
            )
            
            logger.info(f"Auto-response sent for ticket #{ticket_id}")
            
        else:
            # Send acknowledgment email
            acknowledgment = f"""Thank you for contacting EchoFort Support!

We've received your message and assigned it ticket number #{ticket_id}.

Our support team will review your inquiry and respond within 24 hours.

**Your Message:**
{subject}

If you have any additional information, please reply to this email and mention your ticket number.

Best regards,
EchoFort Support Team

---
Ticket ID: #{ticket_id}
Status: Open
Priority: {priority.capitalize()}
"""
            
            await send_email_via_sendgrid(
                to_email=from_email,
                subject=f"[Ticket #{ticket_id}] {subject}",
                body=acknowledgment,
                request=request
            )
            
            logger.info(f"Acknowledgment sent for ticket #{ticket_id}")
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "priority": priority,
            "auto_response_sent": auto_response is not None,
            "message": "Ticket created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error processing email webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing email: {str(e)}")


@router.get("/email/test")
async def test_email_webhook():
    """Test endpoint to verify webhook is accessible"""
    return {
        "status": "ok",
        "endpoint": "/webhooks/email",
        "method": "POST",
        "message": "Email webhook is ready to receive emails from Make.com"
    }

