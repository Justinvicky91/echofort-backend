# app/whatsapp_sms_protection.py
"""
WhatsApp/SMS/Telegram Protection System
- Scan messages for scam patterns
- Real-time threat detection
- Evidence collection
- Alert generation
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from datetime import datetime
import re
import json

router = APIRouter(prefix="/api/messaging", tags=["messaging-protection"])

# Scam pattern database
SCAM_PATTERNS = {
    "digital_arrest": [
        r"(?i)(police|cbi|ed|income tax|customs).*arrest",
        r"(?i)warrant.*issued",
        r"(?i)legal action.*immediately",
        r"(?i)court.*summons",
        r"(?i)arrest warrant",
    ],
    "investment": [
        r"(?i)guaranteed.*returns?",
        r"(?i)double.*money",
        r"(?i)investment.*opportunity",
        r"(?i)\d+%.*profit",
        r"(?i)limited.*slots?",
    ],
    "loan_harassment": [
        r"(?i)loan.*overdue",
        r"(?i)pay.*immediately",
        r"(?i)legal.*consequences",
        r"(?i)credit.*score.*damaged",
    ],
    "impersonation": [
        r"(?i)(bank|paytm|phonepe|gpay).*verify",
        r"(?i)account.*blocked",
        r"(?i)kyc.*update",
        r"(?i)otp.*share",
        r"(?i)card.*expired",
    ],
    "prize_lottery": [
        r"(?i)won.*prize",
        r"(?i)lottery.*winner",
        r"(?i)claim.*reward",
        r"(?i)congratulations.*selected",
    ],
    "job_scam": [
        r"(?i)work.*from.*home",
        r"(?i)earn.*\d+.*per.*day",
        r"(?i)part.*time.*job",
        r"(?i)registration.*fee",
    ]
}

URGENCY_KEYWORDS = [
    "immediately", "urgent", "within 24 hours", "last chance",
    "limited time", "act now", "expire", "deadline"
]

THREAT_KEYWORDS = [
    "arrest", "police", "legal action", "court", "warrant",
    "fine", "penalty", "blocked", "suspended"
]

def analyze_message(message_text: str, sender_info: dict) -> dict:
    """
    Analyze message for scam patterns
    
    Returns:
    - threat_level: 0-10
    - scam_type: detected scam category
    - red_flags: list of suspicious elements
    - confidence: 0-100%
    """
    message_lower = message_text.lower()
    red_flags = []
    scam_types_detected = []
    
    # Check scam patterns
    for scam_type, patterns in SCAM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_text):
                scam_types_detected.append(scam_type)
                red_flags.append(f"Matches {scam_type} pattern")
                break
    
    # Check urgency
    urgency_count = sum(1 for keyword in URGENCY_KEYWORDS if keyword in message_lower)
    if urgency_count > 0:
        red_flags.append(f"Contains {urgency_count} urgency keywords")
    
    # Check threats
    threat_count = sum(1 for keyword in THREAT_KEYWORDS if keyword in message_lower)
    if threat_count > 0:
        red_flags.append(f"Contains {threat_count} threat keywords")
    
    # Check for phone numbers
    phone_numbers = re.findall(r'\+?\d[\d\s-]{8,}\d', message_text)
    if phone_numbers:
        red_flags.append(f"Contains {len(phone_numbers)} phone numbers")
    
    # Check for URLs
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message_text)
    if urls:
        red_flags.append(f"Contains {len(urls)} URLs")
    
    # Check for suspicious sender
    if sender_info.get("is_unknown", False):
        red_flags.append("Unknown sender")
    
    if sender_info.get("country_code") and sender_info["country_code"] != "+91":
        red_flags.append(f"International number: {sender_info['country_code']}")
    
    # Calculate threat level
    threat_level = 0
    if scam_types_detected:
        threat_level += 5
    threat_level += min(urgency_count, 2)
    threat_level += min(threat_count, 2)
    if urls:
        threat_level += 1
    
    threat_level = min(threat_level, 10)
    
    # Calculate confidence
    confidence = 0
    if scam_types_detected:
        confidence += 40
    if urgency_count > 0:
        confidence += 20
    if threat_count > 0:
        confidence += 20
    if urls or phone_numbers:
        confidence += 10
    if sender_info.get("is_unknown"):
        confidence += 10
    
    confidence = min(confidence, 100)
    
    return {
        "threat_level": threat_level,
        "scam_type": scam_types_detected[0] if scam_types_detected else "unknown",
        "all_scam_types": scam_types_detected,
        "red_flags": red_flags,
        "confidence": confidence,
        "is_scam": threat_level >= 6,
        "urgency_count": urgency_count,
        "threat_count": threat_count,
        "urls": urls,
        "phone_numbers": phone_numbers
    }

@router.post("/scan-message")
async def scan_message(payload: dict, request: Request):
    """
    Scan WhatsApp/SMS/Telegram message for scams
    
    Input:
    {
        "message_text": "Your account will be blocked...",
        "sender": {
            "phone": "+919876543210",
            "name": "Unknown",
            "is_unknown": true,
            "country_code": "+91"
        },
        "platform": "whatsapp|sms|telegram",
        "user_id": "customer_id",
        "timestamp": "2025-10-27T10:00:00Z"
    }
    
    Returns:
    {
        "threat_level": 8,
        "scam_type": "digital_arrest",
        "is_scam": true,
        "confidence": 85,
        "red_flags": [...],
        "recommendation": "Block and report",
        "evidence_id": "msg_123"
    }
    """
    message_text = payload.get("message_text", "")
    sender = payload.get("sender", {})
    platform = payload.get("platform", "unknown")
    user_id = payload.get("user_id")
    timestamp = payload.get("timestamp", datetime.utcnow().isoformat())
    
    if not message_text:
        raise HTTPException(400, "message_text required")
    
    # Analyze message
    analysis = analyze_message(message_text, sender)
    
    # Store in database for evidence
    try:
        db = request.app.state.db
        
        result = await db.execute(text("""
            INSERT INTO message_scans (
                user_id, platform, sender_phone, sender_name,
                message_text, threat_level, scam_type, confidence,
                red_flags, is_scam, scanned_at
            ) VALUES (
                :user_id, :platform, :sender_phone, :sender_name,
                :message_text, :threat_level, :scam_type, :confidence,
                :red_flags, :is_scam, NOW()
            ) RETURNING id
        """), {
            "user_id": user_id,
            "platform": platform,
            "sender_phone": sender.get("phone", "unknown"),
            "sender_name": sender.get("name", "Unknown"),
            "message_text": message_text,
            "threat_level": analysis["threat_level"],
            "scam_type": analysis["scam_type"],
            "confidence": analysis["confidence"],
            "red_flags": json.dumps(analysis["red_flags"]),
            "is_scam": analysis["is_scam"]
        })
        
        evidence_id = result.fetchone()[0]
        
    except Exception as e:
        print(f"❌ Failed to store message scan: {e}")
        evidence_id = None
    
    # Generate recommendation
    if analysis["threat_level"] >= 8:
        recommendation = "🚨 HIGH RISK: Block sender immediately and report to cybercrime"
    elif analysis["threat_level"] >= 6:
        recommendation = "⚠️ SUSPICIOUS: Do not respond, block if continues"
    elif analysis["threat_level"] >= 4:
        recommendation = "⚡ CAUTION: Be careful, verify sender identity"
    else:
        recommendation = "✅ LOW RISK: Appears safe, but stay vigilant"
    
    return {
        "threat_level": analysis["threat_level"],
        "scam_type": analysis["scam_type"],
        "all_scam_types": analysis["all_scam_types"],
        "is_scam": analysis["is_scam"],
        "confidence": analysis["confidence"],
        "red_flags": analysis["red_flags"],
        "recommendation": recommendation,
        "evidence_id": f"msg_{evidence_id}" if evidence_id else None,
        "urls_detected": analysis["urls"],
        "phone_numbers_detected": analysis["phone_numbers"],
        "analysis": {
            "urgency_indicators": analysis["urgency_count"],
            "threat_indicators": analysis["threat_count"],
            "platform": platform,
            "sender": sender.get("phone", "unknown")
        }
    }

@router.post("/bulk-scan")
async def bulk_scan_messages(payload: dict):
    """
    Scan multiple messages at once
    
    Input:
    {
        "messages": [
            {"message_text": "...", "sender": {...}, ...},
            ...
        ],
        "user_id": "customer_id"
    }
    
    Returns list of scan results
    """
    messages = payload.get("messages", [])
    user_id = payload.get("user_id")
    
    if not messages:
        raise HTTPException(400, "messages array required")
    
    results = []
    for msg in messages:
        try:
            analysis = analyze_message(
                msg.get("message_text", ""),
                msg.get("sender", {})
            )
            results.append({
                "message_id": msg.get("id"),
                "threat_level": analysis["threat_level"],
                "is_scam": analysis["is_scam"],
                "scam_type": analysis["scam_type"],
                "confidence": analysis["confidence"]
            })
        except Exception as e:
            results.append({
                "message_id": msg.get("id"),
                "error": str(e)
            })
    
    return {
        "total_scanned": len(messages),
        "scams_detected": sum(1 for r in results if r.get("is_scam")),
        "results": results
    }

@router.get("/scan-history/{user_id}")
async def get_scan_history(user_id: str, request: Request, limit: int = 50):
    """Get message scan history for a user"""
    try:
        db = request.app.state.db
        
        result = await db.execute(text("""
            SELECT id, platform, sender_phone, sender_name,
                   LEFT(message_text, 100) as message_preview,
                   threat_level, scam_type, confidence, is_scam,
                   scanned_at
            FROM message_scans
            WHERE user_id = :user_id
            ORDER BY scanned_at DESC
            LIMIT :limit
        """), {"user_id": user_id, "limit": limit})
        
        scans = []
        for row in result.fetchall():
            scans.append({
                "id": row[0],
                "platform": row[1],
                "sender_phone": row[2],
                "sender_name": row[3],
                "message_preview": row[4],
                "threat_level": row[5],
                "scam_type": row[6],
                "confidence": row[7],
                "is_scam": row[8],
                "scanned_at": row[9].isoformat() if row[9] else None
            })
        
        return {
            "success": true,
            "total": len(scans),
            "scans": scans
        }
        
    except Exception as e:
        print(f"❌ Failed to get scan history: {e}")
        return {
            "success": False,
            "error": str(e),
            "scans": []
        }

@router.get("/test")
async def test_messaging_protection():
    """Test messaging protection system"""
    
    # Test message
    test_message = "URGENT! Your account will be arrested by CBI within 24 hours. Call +919876543210 immediately to avoid legal action. Click http://scam.com"
    
    analysis = analyze_message(test_message, {
        "phone": "+919876543210",
        "is_unknown": True,
        "country_code": "+91"
    })
    
    return {
        "status": "ok",
        "test_message": test_message[:100] + "...",
        "analysis": analysis,
        "message": "WhatsApp/SMS protection system operational"
    }

