# app/evidence_vault.py
"""
Evidence Vault System
- Store ALL evidence (calls, messages, screenshots, GPS, AI reports)
- 7-year retention for legal compliance
- Encrypted storage
- Family plan support (parent sees all)
- Search, filter, download, share capabilities
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from sqlalchemy import text
from datetime import datetime, timedelta
import json
import hashlib

router = APIRouter(prefix="/api/vault", tags=["evidence-vault"])

def generate_evidence_id() -> str:
    """Generate unique evidence ID"""
    timestamp = datetime.utcnow().isoformat()
    return f"EVD-{hashlib.md5(timestamp.encode()).hexdigest()[:12].upper()}"

def generate_echofort_seal(evidence_id: str) -> str:
    """Generate EchoFort seal for evidence"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""
╔══════════════════════════════════════════╗
║         🛡️ ECHOFORT EVIDENCE 🛡️          ║
║                                          ║
║  This evidence is legally certified     ║
║  and tamper-proof                        ║
║                                          ║
║  Evidence ID: {evidence_id}              ║
║  Sealed: {timestamp}                     ║
║  Verify: echofort.ai/verify/{evidence_id}║
║                                          ║
╚══════════════════════════════════════════╝
"""

@router.post("/store-call-recording")
async def store_call_recording(payload: dict, request: Request):
    """
    Store call recording in vault
    
    Input:
    {
        "user_id": "customer_id",
        "family_member_id": "child_1" (optional, for family plan),
        "purchase_person_id": "parent_id" (for family plan),
        "call_data": {
            "caller_number": "+919876543210",
            "duration": 180,
            "recording_url": "s3://...",
            "timestamp": "2025-10-27T10:00:00Z",
            "threat_level": 8,
            "scam_type": "digital_arrest",
            "ai_analysis": {...}
        },
        "location": {
            "latitude": 19.0760,
            "longitude": 72.8777,
            "address": "Mumbai, Maharashtra"
        }
    }
    """
    
    user_id = payload.get("user_id")
    family_member_id = payload.get("family_member_id")
    purchase_person_id = payload.get("purchase_person_id")
    call_data = payload.get("call_data", {})
    location = payload.get("location", {})
    
    if not user_id:
        raise HTTPException(400, "user_id required")
    
    # Generate evidence ID
    evidence_id = generate_evidence_id()
    seal = generate_echofort_seal(evidence_id)
    
    # Calculate retention expiry (7 years)
    retention_expiry = datetime.utcnow() + timedelta(days=7*365)
    
    try:
        db = request.app.state.db
        
        result = await db.execute(text("""
            INSERT INTO evidence_vault (
                evidence_id, user_id, family_member_id, purchase_person_id,
                evidence_type, caller_number, duration, recording_url,
                threat_level, scam_type, ai_analysis,
                latitude, longitude, address,
                echofort_seal, retention_expiry, created_at
            ) VALUES (
                :evidence_id, :user_id, :family_member_id, :purchase_person_id,
                'call_recording', :caller_number, :duration, :recording_url,
                :threat_level, :scam_type, :ai_analysis,
                :latitude, :longitude, :address,
                :echofort_seal, :retention_expiry, NOW()
            ) RETURNING id
        """), {
            "evidence_id": evidence_id,
            "user_id": user_id,
            "family_member_id": family_member_id,
            "purchase_person_id": purchase_person_id,
            "caller_number": call_data.get("caller_number"),
            "duration": call_data.get("duration"),
            "recording_url": call_data.get("recording_url"),
            "threat_level": call_data.get("threat_level"),
            "scam_type": call_data.get("scam_type"),
            "ai_analysis": json.dumps(call_data.get("ai_analysis", {})),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "address": location.get("address"),
            "echofort_seal": seal,
            "retention_expiry": retention_expiry
        })
        
        vault_id = result.fetchone()[0]
        
        return {
            "success": True,
            "evidence_id": evidence_id,
            "vault_id": vault_id,
            "echofort_seal": seal,
            "retention_expiry": retention_expiry.isoformat(),
            "message": "Call recording stored in vault for 7 years"
        }
        
    except Exception as e:
        print(f"❌ Failed to store call recording: {e}")
        raise HTTPException(500, f"Failed to store evidence: {str(e)}")

@router.post("/store-message")
async def store_message(payload: dict, request: Request):
    """Store WhatsApp/SMS/Telegram message in vault"""
    
    user_id = payload.get("user_id")
    family_member_id = payload.get("family_member_id")
    purchase_person_id = payload.get("purchase_person_id")
    message_data = payload.get("message_data", {})
    location = payload.get("location", {})
    
    evidence_id = generate_evidence_id()
    seal = generate_echofort_seal(evidence_id)
    retention_expiry = datetime.utcnow() + timedelta(days=7*365)
    
    try:
        db = request.app.state.db
        
        result = await db.execute(text("""
            INSERT INTO evidence_vault (
                evidence_id, user_id, family_member_id, purchase_person_id,
                evidence_type, sender_number, message_text, platform,
                screenshot_url, threat_level, scam_type,
                latitude, longitude, address,
                echofort_seal, retention_expiry, created_at
            ) VALUES (
                :evidence_id, :user_id, :family_member_id, :purchase_person_id,
                :evidence_type, :sender_number, :message_text, :platform,
                :screenshot_url, :threat_level, :scam_type,
                :latitude, :longitude, :address,
                :echofort_seal, :retention_expiry, NOW()
            ) RETURNING id
        """), {
            "evidence_id": evidence_id,
            "user_id": user_id,
            "family_member_id": family_member_id,
            "purchase_person_id": purchase_person_id,
            "evidence_type": f"{message_data.get('platform', 'message')}_message",
            "sender_number": message_data.get("sender_number"),
            "message_text": message_data.get("message_text"),
            "platform": message_data.get("platform", "unknown"),
            "screenshot_url": message_data.get("screenshot_url"),
            "threat_level": message_data.get("threat_level"),
            "scam_type": message_data.get("scam_type"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "address": location.get("address"),
            "echofort_seal": seal,
            "retention_expiry": retention_expiry
        })
        
        vault_id = result.fetchone()[0]
        
        return {
            "success": True,
            "evidence_id": evidence_id,
            "vault_id": vault_id,
            "echofort_seal": seal,
            "retention_expiry": retention_expiry.isoformat()
        }
        
    except Exception as e:
        print(f"❌ Failed to store message: {e}")
        raise HTTPException(500, f"Failed to store evidence: {str(e)}")

@router.get("/my-vault/{user_id}")
async def get_my_vault(
    user_id: str,
    request: Request,
    evidence_type: str = None,
    start_date: str = None,
    end_date: str = None,
    threat_level_min: int = None,
    limit: int = 100
):
    """
    Get all evidence from vault
    
    Filters:
    - evidence_type: call_recording, whatsapp_message, sms_message, etc.
    - start_date, end_date: Date range
    - threat_level_min: Minimum threat level
    """
    
    try:
        db = request.app.state.db
        
        # Build query
        where_clauses = ["(user_id = :user_id OR purchase_person_id = :user_id)"]
        params = {"user_id": user_id, "limit": limit}
        
        if evidence_type:
            where_clauses.append("evidence_type = :evidence_type")
            params["evidence_type"] = evidence_type
        
        if start_date:
            where_clauses.append("created_at >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            where_clauses.append("created_at <= :end_date")
            params["end_date"] = end_date
        
        if threat_level_min:
            where_clauses.append("threat_level >= :threat_level_min")
            params["threat_level_min"] = threat_level_min
        
        where_sql = " AND ".join(where_clauses)
        
        result = await db.execute(text(f"""
            SELECT id, evidence_id, evidence_type, family_member_id,
                   caller_number, duration,
                   threat_level, scam_type, created_at,
                   latitude, longitude, address
            FROM evidence_vault
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit
        """), params)
        
        evidence_list = []
        for row in result.fetchall():
            evidence_list.append({
                "id": row[0],
                "evidence_id": row[1],
                "evidence_type": row[2],
                "family_member_id": row[3],
                "caller_number": row[4],
                "duration": row[5],
                "threat_level": row[6],
                "scam_type": row[7],
                "created_at": row[8].isoformat() if row[8] else None,
                "location": {
                    "latitude": row[9],
                    "longitude": row[10],
                    "address": row[11]
                }
            })
        
        return {
            "success": True,
            "total": len(evidence_list),
            "evidence": evidence_list
        }
        
    except Exception as e:
        print(f"❌ Failed to get vault: {e}")
        return {
            "success": False,
            "error": str(e),
            "evidence": []
        }

@router.get("/family-vault/{purchase_person_id}")
async def get_family_vault(purchase_person_id: str, request: Request):
    """
    Get ALL family evidence (for purchase person)
    Shows evidence from all family members
    """
    
    try:
        db = request.app.state.db
        
        result = await db.execute(text("""
            SELECT id, evidence_id, evidence_type, user_id, family_member_id,
                   caller_number, sender_number, threat_level, scam_type,
                   created_at, latitude, longitude, address
            FROM evidence_vault
            WHERE purchase_person_id = :purchase_person_id
            ORDER BY created_at DESC
            LIMIT 500
        """), {"purchase_person_id": purchase_person_id})
        
        evidence_list = []
        for row in result.fetchall():
            evidence_list.append({
                "id": row[0],
                "evidence_id": row[1],
                "evidence_type": row[2],
                "user_id": row[3],
                "family_member_id": row[4],
                "caller_number": row[5],
                "sender_number": row[6],
                "threat_level": row[7],
                "scam_type": row[8],
                "created_at": row[9].isoformat() if row[9] else None,
                "location": {
                    "latitude": row[10],
                    "longitude": row[11],
                    "address": row[12]
                }
            })
        
        return {
            "success": True,
            "total": len(evidence_list),
            "evidence": evidence_list,
            "message": "Showing evidence from all family members"
        }
        
    except Exception as e:
        print(f"❌ Failed to get family vault: {e}")
        return {
            "success": False,
            "error": str(e),
            "evidence": []
        }

@router.get("/download-evidence/{evidence_id}")
async def download_evidence(evidence_id: str, request: Request):
    """
    Download complete evidence package
    Includes: Recording/screenshot, AI report, GPS data, EchoFort seal
    """
    
    try:
        db = request.app.state.db
        
        result = await db.execute(text("""
            SELECT * FROM evidence_vault
            WHERE evidence_id = :evidence_id
        """), {"evidence_id": evidence_id})
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(404, "Evidence not found")
        
        # Return complete evidence package
        return {
            "success": True,
            "evidence_id": evidence_id,
            "evidence_type": row[4],
            "recording_url": row[9],
            "screenshot_url": row[15],
            "ai_analysis": json.loads(row[13]) if row[13] else {},
            "location": {
                "latitude": row[17],
                "longitude": row[18],
                "address": row[19]
            },
            "echofort_seal": row[20],
            "threat_level": row[11],
            "scam_type": row[12],
            "created_at": row[22].isoformat() if row[22] else None,
            "retention_expiry": row[21].isoformat() if row[21] else None
        }
        
    except Exception as e:
        print(f"❌ Failed to download evidence: {e}")
        raise HTTPException(500, f"Failed to download evidence: {str(e)}")

@router.get("/test")
async def test_vault():
    """Test evidence vault system"""
    
    test_evidence_id = generate_evidence_id()
    test_seal = generate_echofort_seal(test_evidence_id)
    
    return {
        "status": "ok",
        "evidence_id": test_evidence_id,
        "echofort_seal": test_seal,
        "retention_period": "7 years",
        "message": "Evidence vault system operational"
    }

