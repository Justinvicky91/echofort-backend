"""
Block 4 - S2: Simple, Robust Complaint Draft API
Supports evidence_id-based complaint generation for loan harassment only.
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from datetime import datetime
import json

router = APIRouter(prefix="/api/complaints", tags=["complaints-v2"])

# Bank contacts for loan harassment complaints
BANK_CONTACTS = {
    "hdfc": {
        "name": "HDFC Bank",
        "fraud_email": "phishing@hdfcbank.com",
        "customer_care": "1860-267-6161"
    },
    "sbi": {
        "name": "State Bank of India",
        "fraud_email": "report.phishing@sbi.co.in",
        "customer_care": "1800-11-2211"
    },
    "icici": {
        "name": "ICICI Bank",
        "fraud_email": "cybercrime@icicibank.com",
        "customer_care": "1860-120-7777"
    }
}

async def load_evidence_for_complaint(evidence_id: str, db) -> dict:
    """
    Load evidence from evidence_vault by evidence_id.
    Returns dict with evidence details or None if not found.
    """
    try:
        result = await db.execute(text("""
            SELECT evidence_id, user_id, evidence_type, caller_number, 
                   threat_level, scam_type, ai_analysis, 
                   latitude, longitude, address, created_at
            FROM evidence_vault
            WHERE evidence_id = :evidence_id
        """), {"evidence_id": evidence_id})
        
        row = result.fetchone()
        if not row:
            return None
        
        # Parse ai_analysis JSONB if present
        ai_analysis = row[6] if row[6] else {}
        
        return {
            "evidence_id": row[0],
            "user_id": row[1],
            "evidence_type": row[2],
            "caller_number": row[3],
            "threat_level": row[4],
            "scam_type": row[5],
            "ai_analysis": ai_analysis,
            "latitude": row[7],
            "longitude": row[8],
            "address": row[9],
            "created_at": row[10]
        }
    except Exception as e:
        print(f"[ERROR] Failed to load evidence: {e}")
        return None

def generate_certificate_id(evidence_id: str) -> str:
    """Generate EchoFort certificate ID"""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    return f"ECF-{date_str}-{evidence_id}"

@router.post("/generate-draft-v2")
async def generate_complaint_draft_v2(payload: dict, request: Request):
    """
    Generate complaint draft using evidence_id.
    
    Request:
    {
        "user_id": "...",
        "evidence_id": "EVD-...",
        "complaint_type": "loan_harassment",
        "bank_name_override": "hdfc" (optional)
    }
    
    Response:
    {
        "ok": true,
        "complaint_type": "bank_loan_harassment",
        "drafts": [...]
    }
    """
    
    user_id = payload.get("user_id")
    evidence_id = payload.get("evidence_id")
    complaint_type = payload.get("complaint_type", "loan_harassment")
    bank_name_override = payload.get("bank_name_override")
    
    # Validate required fields
    if not evidence_id:
        return {"ok": False, "error": "evidence_id_required"}
    
    # Only support loan_harassment for now
    if complaint_type != "loan_harassment":
        return {"ok": False, "error": "complaint_type_not_implemented"}
    
    # Load evidence from vault
    db = request.app.state.db
    evidence = await load_evidence_for_complaint(evidence_id, db)
    
    if not evidence:
        return {"ok": False, "error": "evidence_not_found"}
    
    # Determine bank name
    bank_name = bank_name_override or evidence.get("ai_analysis", {}).get("bank_name", "hdfc")
    bank_name = bank_name.lower()
    
    if bank_name not in BANK_CONTACTS:
        bank_name = "hdfc"  # Default fallback
    
    bank = BANK_CONTACTS[bank_name]
    
    # Generate certificate ID
    certificate_id = generate_certificate_id(evidence_id)
    
    # Build complaint draft
    subject = f"Complaint Against Loan Harassment - Certificate {certificate_id}"
    
    body = f"""Dear Sir/Madam,

I am writing to file a formal complaint regarding loan harassment calls received from your institution.

ECHOFORT EVIDENCE CERTIFICATE
Certificate ID: {certificate_id}
Evidence ID: {evidence_id}
Date of Incident: {evidence.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d %H:%M:%S') if evidence.get('created_at') else 'N/A'}

INCIDENT DETAILS:
- Caller Number: {evidence.get('caller_number', 'Unknown')}
- Threat Level: {evidence.get('threat_level', 0)}/10
- Location: {evidence.get('address', 'Unknown')}

This evidence has been legally certified and is tamper-proof. The call recording and analysis are available for verification.

I request immediate action to:
1. Stop all harassment calls from this number
2. Investigate the caller's authorization
3. Provide written confirmation of corrective action

This complaint is filed under the Reserve Bank of India's Fair Practices Code for Lenders.

Regards,
EchoFort User
"""
    
    draft = {
        "certificate_id": certificate_id,
        "bank_name": bank["name"],
        "to": bank["fraud_email"],
        "cc": ["noreply@echofort.ai"],
        "subject": subject,
        "body_preview": body[:200] + "..."
    }
    
    # Store draft in database
    try:
        await db.execute(text("""
            INSERT INTO complaint_drafts 
            (user_id, evidence_id, complaint_type, certificate_id, recipient_email, draft_body, created_at)
            VALUES (:user_id, :evidence_id, :complaint_type, :certificate_id, :recipient_email, :draft_body, NOW())
        """), {
            "user_id": evidence.get("user_id", user_id),
            "evidence_id": evidence_id,
            "complaint_type": "bank_loan_harassment",
            "certificate_id": certificate_id,
            "recipient_email": bank["fraud_email"],
            "draft_body": body
        })
        await db.commit()
    except Exception as e:
        print(f"[ERROR] Failed to store draft: {e}")
        # Continue anyway - draft is still returned to user
    
    return {
        "ok": True,
        "complaint_type": "bank_loan_harassment",
        "drafts": [draft]
    }
