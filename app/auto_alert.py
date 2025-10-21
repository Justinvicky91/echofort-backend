# app/auto_alert.py - Auto-Alert System
"""
Auto-Alert System - Automated Email Drafting to Authorities
Helps users report scams to bank, police, cybercrime, RBI, consumer forum
Compliant with Indian laws (Digital Personal Data Protection Act 2023, Consumer Protection Act 2019)
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr
from .utils import get_current_user
import os

router = APIRouter(prefix="/api/auto-alert", tags=["Auto Alert"])

# Authority contact information (India-specific)
AUTHORITIES = {
    "cybercrime": {
        "name": "National Cybercrime Reporting Portal",
        "email": "complaints@cybercrime.gov.in",
        "portal": "https://cybercrime.gov.in",
        "phone": "1930"
    },
    "bank": {
        "name": "Bank Fraud Reporting",
        "email": None,  # User provides their bank email
        "portal": None,
        "phone": "1800-425-3800"  # Generic banking helpline
    },
    "rbi": {
        "name": "Reserve Bank of India - Consumer Education and Protection Department",
        "email": "helpdoc@rbi.org.in",
        "portal": "https://cms.rbi.org.in",
        "phone": "14448"
    },
    "police": {
        "name": "Local Police Station",
        "email": None,  # User provides local police email
        "portal": None,
        "phone": "100"
    },
    "consumer_forum": {
        "name": "National Consumer Helpline",
        "email": "nch@nic.in",
        "portal": "https://consumerhelpline.gov.in",
        "phone": "1915"
    }
}


class AlertRequest(BaseModel):
    alert_type: Literal["bank", "police", "cybercrime", "rbi", "consumer_forum"]
    scam_type: str  # "digital_arrest", "investment_fraud", "phishing", etc.
    incident_date: str
    amount_lost: Optional[float] = None
    scammer_phone: Optional[str] = None
    scammer_email: Optional[str] = None
    scammer_upi: Optional[str] = None
    scammer_account: Optional[str] = None
    description: str
    evidence_urls: Optional[list[str]] = None
    recipient_email: Optional[EmailStr] = None  # For bank/police
    recipient_name: Optional[str] = None


class AlertApproval(BaseModel):
    alert_id: int
    approved: bool
    modifications: Optional[str] = None


def generate_alert_email(alert_type: str, data: dict, user_info: dict) -> dict:
    """
    Generate email content for reporting to authorities
    Returns: {subject, body, recipient_email, recipient_name}
    """
    
    authority = AUTHORITIES.get(alert_type, {})
    
    # Common header
    header = f"""To: {authority.get('name', 'Authority')}
From: {user_info.get('name', 'User')} ({user_info.get('email', 'N/A')})
Date: {datetime.now().strftime('%d %B %Y, %I:%M %p')}

Subject: """
    
    # Generate subject and body based on alert type
    if alert_type == "cybercrime":
        subject = f"Cybercrime Report - {data['scam_type'].replace('_', ' ').title()}"
        body = f"""{header}{subject}

Dear Sir/Madam,

I am writing to report a cybercrime incident that occurred on {data['incident_date']}.

INCIDENT DETAILS:
- Type of Scam: {data['scam_type'].replace('_', ' ').title()}
- Date of Incident: {data['incident_date']}
- Financial Loss: ₹{data.get('amount_lost', 0):,.2f}

SCAMMER INFORMATION:
- Phone Number: {data.get('scammer_phone', 'Not available')}
- Email: {data.get('scammer_email', 'Not available')}
- UPI ID: {data.get('scammer_upi', 'Not available')}
- Bank Account: {data.get('scammer_account', 'Not available')}

INCIDENT DESCRIPTION:
{data['description']}

EVIDENCE:
{chr(10).join(f'- {url}' for url in data.get('evidence_urls', [])) if data.get('evidence_urls') else 'Evidence will be provided upon request'}

I request you to investigate this matter and take necessary action against the perpetrators.

I am available for any further information or clarification.

Thank you for your attention to this matter.

Yours sincerely,
{user_info.get('name', 'User')}
{user_info.get('email', 'N/A')}
{user_info.get('phone', 'N/A')}

---
This report was generated using EchoFort - AI-Powered Scam Protection Platform
Report ID: {data.get('report_id', 'N/A')}
Generated on: {datetime.now().strftime('%d %B %Y, %I:%M %p IST')}
"""
    
    elif alert_type == "bank":
        subject = f"Fraudulent Transaction Report - {data['scam_type'].replace('_', ' ').title()}"
        body = f"""{header}{subject}

Dear Sir/Madam,

I am a customer of your bank and I am writing to report a fraudulent transaction.

CUSTOMER DETAILS:
- Name: {user_info.get('name', 'User')}
- Email: {user_info.get('email', 'N/A')}
- Phone: {user_info.get('phone', 'N/A')}

FRAUD DETAILS:
- Type of Fraud: {data['scam_type'].replace('_', ' ').title()}
- Date of Incident: {data['incident_date']}
- Amount Lost: ₹{data.get('amount_lost', 0):,.2f}

FRAUDSTER DETAILS:
- Phone Number: {data.get('scammer_phone', 'Not available')}
- UPI ID: {data.get('scammer_upi', 'Not available')}
- Bank Account: {data.get('scammer_account', 'Not available')}

INCIDENT DESCRIPTION:
{data['description']}

IMMEDIATE ACTIONS REQUESTED:
1. Block the fraudster's account immediately
2. Freeze the transaction if possible
3. Investigate the fraud
4. Initiate chargeback/refund process
5. Report to cybercrime authorities

EVIDENCE:
{chr(10).join(f'- {url}' for url in data.get('evidence_urls', [])) if data.get('evidence_urls') else 'Evidence will be provided upon request'}

I request immediate action to prevent further losses and recover my funds.

Thank you for your urgent attention.

Yours sincerely,
{user_info.get('name', 'User')}
{user_info.get('email', 'N/A')}
{user_info.get('phone', 'N/A')}

---
This report was generated using EchoFort - AI-Powered Scam Protection Platform
"""
    
    elif alert_type == "rbi":
        subject = f"Banking Fraud Complaint - {data['scam_type'].replace('_', ' ').title()}"
        body = f"""{header}{subject}

Dear Sir/Madam,

I am writing to file a complaint regarding a banking fraud incident.

COMPLAINANT DETAILS:
- Name: {user_info.get('name', 'User')}
- Email: {user_info.get('email', 'N/A')}
- Phone: {user_info.get('phone', 'N/A')}

COMPLAINT DETAILS:
- Nature of Complaint: {data['scam_type'].replace('_', ' ').title()}
- Date of Incident: {data['incident_date']}
- Financial Loss: ₹{data.get('amount_lost', 0):,.2f}

DETAILS OF FRAUD:
{data['description']}

FRAUDSTER INFORMATION:
- Phone: {data.get('scammer_phone', 'Not available')}
- Email: {data.get('scammer_email', 'Not available')}
- UPI ID: {data.get('scammer_upi', 'Not available')}
- Account: {data.get('scammer_account', 'Not available')}

I request RBI to investigate this matter and take appropriate action as per banking regulations.

Yours faithfully,
{user_info.get('name', 'User')}
{user_info.get('email', 'N/A')}
{user_info.get('phone', 'N/A')}
"""
    
    elif alert_type == "police":
        subject = f"FIR Request - Cyber Fraud Case"
        body = f"""{header}{subject}

To: Station House Officer
{data.get('recipient_name', 'Local Police Station')}

Dear Sir/Madam,

I wish to file an FIR regarding a cyber fraud incident.

COMPLAINANT DETAILS:
- Name: {user_info.get('name', 'User')}
- Address: {user_info.get('address', 'To be provided')}
- Email: {user_info.get('email', 'N/A')}
- Phone: {user_info.get('phone', 'N/A')}

INCIDENT DETAILS:
- Type of Crime: Cyber Fraud - {data['scam_type'].replace('_', ' ').title()}
- Date & Time: {data['incident_date']}
- Place of Occurrence: Online/Telephonic
- Amount Cheated: ₹{data.get('amount_lost', 0):,.2f}

ACCUSED DETAILS:
- Phone Number: {data.get('scammer_phone', 'Unknown')}
- Email: {data.get('scammer_email', 'Unknown')}
- UPI ID: {data.get('scammer_upi', 'Unknown')}
- Bank Account: {data.get('scammer_account', 'Unknown')}

DETAILED DESCRIPTION OF INCIDENT:
{data['description']}

EVIDENCE:
{chr(10).join(f'- {url}' for url in data.get('evidence_urls', [])) if data.get('evidence_urls') else 'Physical evidence will be submitted'}

I request you to register an FIR and investigate this matter under relevant sections of IPC and IT Act.

Yours sincerely,
{user_info.get('name', 'User')}
"""
    
    else:  # consumer_forum
        subject = f"Consumer Complaint - Financial Fraud"
        body = f"""{header}{subject}

Dear Sir/Madam,

I am filing a consumer complaint regarding financial fraud.

CONSUMER DETAILS:
- Name: {user_info.get('name', 'User')}
- Email: {user_info.get('email', 'N/A')}
- Phone: {user_info.get('phone', 'N/A')}

COMPLAINT DETAILS:
- Nature: {data['scam_type'].replace('_', ' ').title()}
- Date: {data['incident_date']}
- Loss: ₹{data.get('amount_lost', 0):,.2f}

DETAILS:
{data['description']}

I request appropriate action under Consumer Protection Act 2019.

Yours sincerely,
{user_info.get('name', 'User')}
"""
    
    return {
        "subject": subject,
        "body": body,
        "recipient_email": data.get('recipient_email') or authority.get('email'),
        "recipient_name": data.get('recipient_name') or authority.get('name'),
        "portal_url": authority.get('portal'),
        "helpline": authority.get('phone')
    }


@router.post("/create-alert")
async def create_alert(request: Request, payload: AlertRequest, current_user: dict = Depends(get_current_user)):
    """
    Create auto-alert draft for reporting scam to authorities
    User must approve before sending
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Get user info
        user_query = text("""
            SELECT name, email, identity FROM users WHERE id = :uid
        """)
        user_row = (await db.execute(user_query, {"uid": user_id})).fetchone()
        
        user_info = {
            "name": user_row[0] if user_row else "User",
            "email": user_row[1] if user_row else "N/A",
            "phone": user_row[2] if user_row else "N/A"
        }
        
        # Prepare data
        alert_data = {
            "scam_type": payload.scam_type,
            "incident_date": payload.incident_date,
            "amount_lost": payload.amount_lost,
            "scammer_phone": payload.scammer_phone,
            "scammer_email": payload.scammer_email,
            "scammer_upi": payload.scammer_upi,
            "scammer_account": payload.scammer_account,
            "description": payload.description,
            "evidence_urls": payload.evidence_urls,
            "recipient_email": payload.recipient_email,
            "recipient_name": payload.recipient_name,
            "report_id": f"ECF-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        # Generate email
        email_content = generate_alert_email(payload.alert_type, alert_data, user_info)
        
        # Save to database (draft status)
        save_query = text("""
            INSERT INTO auto_alerts (
                user_id, alert_type, scam_incident_id, recipient_email,
                recipient_name, subject, body, status, user_confirmed, created_at
            ) VALUES (
                :uid, :type, NULL, :email, :name, :subject, :body, 'draft', FALSE, NOW()
            ) RETURNING id
        """)
        
        result = await db.execute(save_query, {
            "uid": user_id,
            "type": payload.alert_type,
            "email": email_content["recipient_email"],
            "name": email_content["recipient_name"],
            "subject": email_content["subject"],
            "body": email_content["body"]
        })
        
        alert_id = result.fetchone()[0]
        
        return {
            "ok": True,
            "alert_id": alert_id,
            "status": "draft",
            "email_content": email_content,
            "message": "Alert draft created. Please review and approve to send.",
            "next_steps": [
                "Review the email content carefully",
                "Make any necessary modifications",
                "Approve to send the email",
                "You can also copy the content and send manually"
            ],
            "authority_info": AUTHORITIES.get(payload.alert_type, {})
        }
    
    except Exception as e:
        raise HTTPException(500, f"Alert creation error: {str(e)}")


@router.post("/approve-alert")
async def approve_alert(request: Request, payload: AlertApproval, current_user: dict = Depends(get_current_user)):
    """
    Approve and send alert email to authorities
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Get alert
        alert_query = text("""
            SELECT user_id, recipient_email, subject, body, status
            FROM auto_alerts
            WHERE id = :aid
        """)
        alert = (await db.execute(alert_query, {"aid": payload.alert_id})).fetchone()
        
        if not alert:
            raise HTTPException(404, "Alert not found")
        
        if alert[0] != user_id:
            raise HTTPException(403, "Unauthorized")
        
        if alert[4] != "draft":
            raise HTTPException(400, "Alert already processed")
        
        if not payload.approved:
            # Mark as rejected
            await db.execute(text("""
                UPDATE auto_alerts
                SET status = 'rejected', user_confirmed = FALSE
                WHERE id = :aid
            """), {"aid": payload.alert_id})
            
            return {
                "ok": True,
                "status": "rejected",
                "message": "Alert rejected and not sent"
            }
        
        # Apply modifications if any
        body = alert[3]
        if payload.modifications:
            body = payload.modifications
        
        # Mark as approved (user will send manually from their email)
        await db.execute(text("""
            UPDATE auto_alerts
            SET status = 'approved', user_confirmed = TRUE, approved_at = NOW(), body = :body
            WHERE id = :aid
        """), {"aid": payload.alert_id, "body": body})
        
        # Get user email for "From" address
        user_email = current_user.get('email', 'your-email@example.com')
        
        return {
            "ok": True,
            "status": "approved",
            "alert_id": payload.alert_id,
            "message": "Email draft approved. Please copy and send from your email.",
            "email_draft": {
                "from": user_email,
                "to": alert[1],
                "subject": alert[2],
                "body": body
            },
            "instructions": [
                "1. Open your email client (Gmail, Outlook, etc.)",
                "2. Copy the email content below",
                "3. Send to: " + alert[1],
                "4. Mark as sent in the app after sending"
            ],
            "next_steps": [
                "Save the confirmation for your records",
                "Note down the report ID for future reference",
                "Follow up with authorities after 7 days if no response",
                "Keep all evidence safe"
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Approval error: {str(e)}")


@router.get("/my-alerts")
async def get_my_alerts(request: Request, current_user: dict = Depends(get_current_user), limit: int = 20):
    """
    Get user's alert history
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        alerts_query = text("""
            SELECT id, alert_type, subject, status, created_at, sent_at
            FROM auto_alerts
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT :lim
        """)
        
        alerts = (await db.execute(alerts_query, {"uid": user_id, "lim": limit})).fetchall()
        
        return {
            "ok": True,
            "total": len(alerts),
            "alerts": [
                {
                    "alert_id": a[0],
                    "alert_type": a[1],
                    "subject": a[2],
                    "status": a[3],
                    "created_at": str(a[4]),
                    "sent_at": str(a[5]) if a[5] else None
                }
                for a in alerts
            ]
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error fetching alerts: {str(e)}")


@router.get("/alert-details/{alert_id}")
async def get_alert_details(request: Request, alert_id: int, current_user: dict = Depends(get_current_user)):
    """
    Get full alert details
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        alert_query = text("""
            SELECT 
                id, alert_type, recipient_email, recipient_name,
                subject, body, status, user_confirmed, created_at, sent_at
            FROM auto_alerts
            WHERE id = :aid AND user_id = :uid
        """)
        
        alert = (await db.execute(alert_query, {"aid": alert_id, "uid": user_id})).fetchone()
        
        if not alert:
            raise HTTPException(404, "Alert not found")
        
        return {
            "ok": True,
            "alert": {
                "alert_id": alert[0],
                "alert_type": alert[1],
                "recipient_email": alert[2],
                "recipient_name": alert[3],
                "subject": alert[4],
                "body": alert[5],
                "status": alert[6],
                "user_confirmed": alert[7],
                "created_at": str(alert[8]),
                "sent_at": str(alert[9]) if alert[9] else None
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error fetching alert: {str(e)}")

@router.post("/mark-sent")
async def mark_alert_sent(request: Request, alert_id: int, current_user: dict = Depends(get_current_user)):
    """
    Mark alert as sent after user manually sends email from their email client
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Verify ownership
        alert = (await db.execute(text("""
            SELECT user_id, status FROM auto_alerts WHERE id = :aid
        """), {"aid": alert_id})).fetchone()
        
        if not alert:
            raise HTTPException(404, "Alert not found")
        
        if alert[0] != user_id:
            raise HTTPException(403, "Unauthorized")
        
        if alert[1] != "approved":
            raise HTTPException(400, "Alert must be approved first")
        
        # Mark as sent
        await db.execute(text("""
            UPDATE auto_alerts
            SET status = 'sent', sent_at = NOW()
            WHERE id = :aid
        """), {"aid": alert_id})
        
        return {
            "ok": True,
            "message": "Alert marked as sent successfully",
            "alert_id": alert_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

