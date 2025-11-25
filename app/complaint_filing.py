# app/complaint_filing.py
"""
Automated Complaint Draft Generation System
- Generate evidence packages
- Draft complaint emails (NOT auto-send)
- Add EchoFort Seal & GPS marker
- Intelligent routing: Bank vs Cybercrime
- Country → State → District level routing
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from datetime import datetime
import json

router = APIRouter(prefix="/api/complaints", tags=["complaints"])

# Cybercrime contact database (India)
CYBERCRIME_CONTACTS = {
    "national": {
        "name": "National Cybercrime Reporting Portal",
        "email": "complaints@cybercrime.gov.in",
        "phone": "1930",
        "website": "https://cybercrime.gov.in"
    },
    "states": {
        "maharashtra": {
            "name": "Maharashtra Cyber Cell",
            "email": "cyber@mahapolice.gov.in",
            "districts": {
                "mumbai": {"email": "cybercrime.mumbai@mahapolice.gov.in"},
                "pune": {"email": "cybercrime.pune@mahapolice.gov.in"}
            }
        },
        "karnataka": {
            "name": "Karnataka Cyber Cell",
            "email": "cybercrime@ksp.gov.in",
            "districts": {
                "bengaluru": {"email": "cybercrime.bengaluru@ksp.gov.in"}
            }
        },
        "delhi": {
            "name": "Delhi Cyber Cell",
            "email": "cybercrime@delhipolice.gov.in"
        }
        # Add more states as needed
    }
}

# Bank contact database
BANK_CONTACTS = {
    "sbi": {
        "name": "State Bank of India",
        "fraud_email": "report.phishing@sbi.co.in",
        "customer_care": "1800-11-2211"
    },
    "hdfc": {
        "name": "HDFC Bank",
        "fraud_email": "phishing@hdfcbank.com",
        "customer_care": "1800-202-6161"
    },
    "icici": {
        "name": "ICICI Bank",
        "fraud_email": "cybercrime@icicibank.com",
        "customer_care": "1860-120-7777"
    },
    "axis": {
        "name": "Axis Bank",
        "fraud_email": "report.phishing@axisbank.com",
        "customer_care": "1860-419-5555"
    }
    # Add more banks
}

def determine_complaint_type(scam_type: str, evidence: dict) -> str:
    """
    Determine if complaint should go to Bank or Cybercrime
    
    Returns: "bank", "cybercrime", or "both"
    """
    loan_related = ["loan_harassment", "loan_recovery", "emi_pressure"]
    bank_related = ["upi_fraud", "card_fraud", "net_banking_fraud", "impersonation"]
    
    if scam_type in loan_related:
        return "bank"
    elif scam_type in bank_related:
        return "both"
    else:
        return "cybercrime"

def get_cybercrime_contact(state: str = None, district: str = None) -> dict:
    """Get appropriate cybercrime contact based on location"""
    
    if state and state.lower() in CYBERCRIME_CONTACTS["states"]:
        state_data = CYBERCRIME_CONTACTS["states"][state.lower()]
        
        if district and "districts" in state_data:
            district_lower = district.lower()
            if district_lower in state_data["districts"]:
                return {
                    "level": "district",
                    "name": f"{district} Cyber Cell",
                    "email": state_data["districts"][district_lower]["email"],
                    "state": state,
                    "district": district
                }
        
        return {
            "level": "state",
            "name": state_data["name"],
            "email": state_data["email"],
            "state": state
        }
    
    # Fallback to national
    return {
        "level": "national",
        **CYBERCRIME_CONTACTS["national"]
    }

def generate_echofort_seal() -> str:
    """Generate EchoFort official seal/stamp"""
    return """
    ╔══════════════════════════════════════════╗
    ║                                          ║
    ║          🛡️  ECHOFORT VERIFIED  🛡️       ║
    ║                                          ║
    ║   This evidence package is certified     ║
    ║   by EchoFort AI Scam Protection        ║
    ║                                          ║
    ║   Certificate ID: {cert_id}              ║
    ║   Generated: {timestamp}                 ║
    ║   Verification: echofort.ai/verify       ║
    ║                                          ║
    ╚══════════════════════════════════════════╝
    """

def generate_complaint_email(
    complaint_type: str,
    scam_type: str,
    evidence: dict,
    recipient: dict,
    user_info: dict
) -> dict:
    """
    Generate complaint email draft
    
    Returns:
    {
        "to": "email@example.com",
        "cc": ["email2@example.com"],
        "subject": "...",
        "body": "...",
        "attachments": [...]
    }
    """
    
    # Generate certificate ID
    cert_id = f"ECF-{datetime.utcnow().strftime('%Y%m%d')}-{evidence.get('id', '000')}"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # EchoFort Seal
    seal = generate_echofort_seal().format(
        cert_id=cert_id,
        timestamp=timestamp
    )
    
    # GPS Marker
    gps_marker = f"""
    📍 LOCATION INFORMATION:
    Latitude: {evidence.get('latitude', 'N/A')}
    Longitude: {evidence.get('longitude', 'N/A')}
    Address: {evidence.get('address', 'N/A')}
    Timestamp: {evidence.get('location_timestamp', 'N/A')}
    """
    
    # Evidence Timeline
    timeline = "\n".join([
        f"  {i+1}. [{item['timestamp']}] {item['description']}"
        for i, item in enumerate(evidence.get('timeline', []))
    ])
    
    # Generate subject
    if complaint_type == "bank":
        subject = f"[URGENT] Loan Harassment Complaint - {user_info['name']} - Ref: {cert_id}"
    else:
        subject = f"[CYBERCRIME] {scam_type.replace('_', ' ').title()} Scam Report - Ref: {cert_id}"
    
    # Generate body
    if complaint_type == "bank":
        body = f"""
Dear {recipient['name']} Support Team,

I am writing to file a formal complaint regarding loan harassment/fraudulent activities.

{seal}

COMPLAINANT DETAILS:
Name: {user_info['name']}
Phone: {user_info['phone']}
Email: {user_info['email']}
Customer ID: {user_info.get('customer_id', 'N/A')}

INCIDENT DETAILS:
Type: {scam_type.replace('_', ' ').title()}
Date & Time: {evidence.get('incident_date', 'N/A')}
Caller Number: {evidence.get('caller_number', 'N/A')}
Threat Level: {evidence.get('threat_level', 'N/A')}/10

EVIDENCE TIMELINE:
{timeline}

{gps_marker}

SCAM ANALYSIS:
{evidence.get('analysis_summary', 'N/A')}

RED FLAGS DETECTED:
{chr(10).join([f"  • {flag}" for flag in evidence.get('red_flags', [])])}

REQUESTED ACTION:
1. Investigate the caller/agent involved
2. Stop harassment calls immediately
3. Review loan recovery practices
4. Provide written confirmation of action taken

ATTACHMENTS:
- Call recording (if available)
- Screenshots of messages
- EchoFort AI analysis report
- GPS location proof

This complaint is generated with the assistance of EchoFort AI Scam Protection System.
For verification, visit: https://echofort.ai/verify/{cert_id}

Regards,
{user_info['name']}
{user_info['phone']}

---
Powered by EchoFort - India's Most Advanced Scam Protection
        """
    else:
        body = f"""
Dear Cybercrime Cell,

I am filing a complaint regarding a cybercrime/scam attempt.

{seal}

COMPLAINANT DETAILS:
Name: {user_info['name']}
Phone: {user_info['phone']}
Email: {user_info['email']}
Address: {user_info.get('address', 'N/A')}
State: {user_info.get('state', 'N/A')}
District: {user_info.get('district', 'N/A')}

INCIDENT DETAILS:
Type: {scam_type.replace('_', ' ').title()}
Date & Time: {evidence.get('incident_date', 'N/A')}
Scammer Contact: {evidence.get('caller_number', 'N/A')}
Platform: {evidence.get('platform', 'Phone Call')}
Threat Level: {evidence.get('threat_level', 'N/A')}/10 (AI-Assessed)

EVIDENCE TIMELINE:
{timeline}

{gps_marker}

SCAM ANALYSIS (AI-Generated):
{evidence.get('analysis_summary', 'N/A')}

RED FLAGS DETECTED:
{chr(10).join([f"  • {flag}" for flag in evidence.get('red_flags', [])])}

FINANCIAL LOSS:
Amount Lost: ₹{evidence.get('amount_lost', '0')}
Transaction Details: {evidence.get('transaction_details', 'N/A')}

REQUESTED ACTION:
1. Register FIR under relevant IPC/IT Act sections
2. Investigate and trace the scammer
3. Block fraudulent numbers/accounts
4. Provide case reference number

ATTACHMENTS:
- Call recording/audio evidence
- Screenshots of messages/transactions
- EchoFort AI analysis report
- GPS location proof
- Bank statements (if applicable)

LEGAL REFERENCES:
- IT Act 2000, Section 66C (Identity Theft)
- IT Act 2000, Section 66D (Cheating by Personation)
- IPC Section 420 (Cheating)
- IPC Section 384 (Extortion)

This complaint is generated with the assistance of EchoFort AI Scam Protection System.
Evidence authenticity can be verified at: https://echofort.ai/verify/{cert_id}

I request immediate action on this matter.

Regards,
{user_info['name']}
{user_info['phone']}
{user_info['email']}

---
Powered by EchoFort - India's Most Advanced Scam Protection
Report ID: {cert_id}
        """
    
    return {
        "to": recipient.get('email') or recipient.get('fraud_email'),
        "cc": recipient.get('cc', []),
        "subject": subject,
        "body": body.strip(),
        "certificate_id": cert_id,
        "echofort_seal": seal,
        "gps_marker": gps_marker
    }

@router.post("/generate-draft")
async def generate_complaint_draft(payload: dict, request: Request):
    """
    Generate complaint email draft (NOT auto-send)
    
    Input:
    {
        "scam_type": "loan_harassment|digital_arrest|...",
        "evidence": {
            "id": "call_123",
            "incident_date": "2025-10-27T10:00:00Z",
            "caller_number": "+919876543210",
            "threat_level": 8,
            "analysis_summary": "...",
            "red_flags": [...],
            "timeline": [...],
            "latitude": 19.0760,
            "longitude": 72.8777,
            "address": "Mumbai, Maharashtra",
            "amount_lost": 0,
            "platform": "Phone Call"
        },
        "user_info": {
            "name": "John Doe",
            "phone": "+919123456789",
            "email": "john@example.com",
            "state": "Maharashtra",
            "district": "Mumbai",
            "customer_id": "CUST123"
        },
        "bank_name": "sbi" (optional, for loan harassment)
    }
    
    Returns:
    {
        "complaint_type": "bank|cybercrime|both",
        "drafts": [
            {
                "recipient_type": "bank|cybercrime",
                "recipient_name": "...",
                "to": "email@example.com",
                "subject": "...",
                "body": "...",
                "certificate_id": "ECF-..."
            }
        ],
        "next_steps": [...]
    }
    """
    
    scam_type = payload.get("scam_type", "unknown")
    evidence = payload.get("evidence", {})
    evidence_id = payload.get("evidence_id")
    user_info = payload.get("user_info", {})
    bank_name = payload.get("bank_name")
    family_info = payload.get("family_info")  # For family plan
    purchase_person = payload.get("purchase_person")  # Parent/guardian who purchased
    
    if not user_info.get("name") or not user_info.get("phone"):
        raise HTTPException(400, "user_info.name and user_info.phone required")
    
    # BLOCK 4 FIX: If evidence_id is provided, fetch evidence from vault
    if evidence_id and (not evidence or len(evidence) == 0):
        try:
            db = request.app.state.db
            print(f"[DEBUG] Fetching evidence for ID: {evidence_id}")
            result = await db.execute(text("""
                SELECT evidence_type, caller_number, threat_level, scam_type,
                       latitude, longitude, address, created_at, ai_analysis
                FROM evidence_vault
                WHERE evidence_id = :evidence_id
            """), {"evidence_id": evidence_id})
            row = result.fetchone()
            print(f"[DEBUG] Row fetched: {row is not None}")
            if row:
                # Extract analysis summary from ai_analysis JSONB if available
                ai_analysis = row[8] if row[8] else {}
                analysis_summary = ai_analysis.get("summary", "Loan harassment call detected")
                
                evidence = {
                    "id": evidence_id,
                    "incident_date": row[7].isoformat() if row[7] else datetime.utcnow().isoformat(),
                    "caller_number": row[1] or "Unknown",
                    "threat_level": row[2] or 0,
                    "analysis_summary": analysis_summary,
                    "red_flags": ["Threatening language", "Loan harassment"],
                    "timeline": [],
                    "latitude": row[4],
                    "longitude": row[5],
                    "address": row[6] or "Unknown",
                    "amount_lost": 0,
                    "platform": "Phone Call"
                }
                print(f"[DEBUG] Evidence object created: {evidence.get('id')}")
            else:
                print(f"[DEBUG] No evidence found for ID: {evidence_id}")
        except Exception as e:
            print(f"[ERROR] Failed to fetch evidence: {e}")
            import traceback
            traceback.print_exc()
    
    # Determine complaint routing
    complaint_type = determine_complaint_type(scam_type, evidence)
    
    drafts = []
    
    # Generate bank complaint if needed
    if complaint_type in ["bank", "both"]:
        if bank_name and bank_name.lower() in BANK_CONTACTS:
            bank = BANK_CONTACTS[bank_name.lower()]
            draft = generate_complaint_email(
                "bank",
                scam_type,
                evidence,
                bank,
                user_info
            )
            draft["recipient_type"] = "bank"
            draft["recipient_name"] = bank["name"]
            draft["customer_care_phone"] = bank["customer_care"]
            drafts.append(draft)
    
    # Generate cybercrime complaint if needed
    if complaint_type in ["cybercrime", "both"]:
        cybercrime_contact = get_cybercrime_contact(
            user_info.get("state"),
            user_info.get("district")
        )
        draft = generate_complaint_email(
            "cybercrime",
            scam_type,
            evidence,
            cybercrime_contact,
            user_info
        )
        draft["recipient_type"] = "cybercrime"
        draft["recipient_name"] = cybercrime_contact["name"]
        draft["level"] = cybercrime_contact["level"]
        draft["helpline"] = "1930"
        drafts.append(draft)
    
    # Store complaint draft in database
    try:
        db = request.app.state.db
        
        for draft in drafts:
            await db.execute(text("""
                INSERT INTO complaint_drafts (
                    user_id, scam_type, recipient_type, recipient_email,
                    subject, body, certificate_id, status, created_at
                ) VALUES (
                    :user_id, :scam_type, :recipient_type, :recipient_email,
                    :subject, :body, :certificate_id, 'draft', NOW()
                )
            """), {
                "user_id": user_info.get("id"),
                "scam_type": scam_type,
                "recipient_type": draft["recipient_type"],
                "recipient_email": draft["to"],
                "subject": draft["subject"],
                "body": draft["body"],
                "certificate_id": draft["certificate_id"]
            })
    except Exception as e:
        print(f"❌ Failed to store complaint draft: {e}")
    
    # Generate next steps
    next_steps = [
        "1. Review the generated email draft carefully",
        "2. Add any additional details or evidence",
        "3. Attach call recordings, screenshots, or documents",
        "4. Copy the email content to your email client",
        "5. Send the email to the provided address",
        "6. Save the certificate ID for tracking",
        "7. Follow up after 7 days if no response"
    ]
    
    if complaint_type == "bank":
        next_steps.append("8. Also call customer care if urgent")
    else:
        next_steps.append("8. Also file online at cybercrime.gov.in")
    
    return {
        "success": True,
        "complaint_type": complaint_type,
        "drafts": drafts,
        "next_steps": next_steps,
        "total_drafts": len(drafts),
        "message": "Complaint draft(s) generated successfully. Review and send manually."
    }

@router.get("/my-complaints/{user_id}")
async def get_my_complaints(user_id: str, request: Request):
    """Get all complaint drafts for a user"""
    try:
        db = request.app.state.db
        
        result = await db.execute(text("""
            SELECT id, scam_type, recipient_type, recipient_email,
                   subject, certificate_id, status, created_at
            FROM complaint_drafts
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """), {"user_id": user_id})
        
        complaints = []
        for row in result.fetchall():
            complaints.append({
                "id": row[0],
                "scam_type": row[1],
                "recipient_type": row[2],
                "recipient_email": row[3],
                "subject": row[4],
                "certificate_id": row[5],
                "status": row[6],
                "created_at": row[7].isoformat() if row[7] else None
            })
        
        return {
            "success": True,
            "total": len(complaints),
            "complaints": complaints
        }
        
    except Exception as e:
        print(f"❌ Failed to get complaints: {e}")
        return {
            "success": False,
            "error": str(e),
            "complaints": []
        }

@router.get("/test")
async def test_complaint_system():
    """Test complaint filing system"""
    
    # Test data
    test_evidence = {
        "id": "test_123",
        "incident_date": "2025-10-27T10:00:00Z",
        "caller_number": "+919876543210",
        "threat_level": 9,
        "analysis_summary": "Digital arrest scam with high urgency and threat indicators",
        "red_flags": [
            "Impersonation of law enforcement",
            "Immediate payment demand",
            "Threat of arrest",
            "Pressure tactics"
        ],
        "timeline": [
            {"timestamp": "10:00:00", "description": "Call received from unknown number"},
            {"timestamp": "10:02:30", "description": "Caller claimed to be CBI officer"},
            {"timestamp": "10:05:00", "description": "Demanded immediate payment"}
        ],
        "latitude": 19.0760,
        "longitude": 72.8777,
        "address": "Mumbai, Maharashtra, India"
    }
    
    test_user = {
        "name": "Test User",
        "phone": "+919123456789",
        "email": "test@example.com",
        "state": "Maharashtra",
        "district": "Mumbai"
    }
    
    complaint_type = determine_complaint_type("digital_arrest", test_evidence)
    cybercrime_contact = get_cybercrime_contact("Maharashtra", "Mumbai")
    
    return {
        "status": "ok",
        "complaint_type": complaint_type,
        "cybercrime_contact": cybercrime_contact,
        "message": "Complaint filing system operational"
    }

