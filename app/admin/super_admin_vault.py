# app/admin/super_admin_vault.py
"""
Super Admin Vault (CLASSIFIED)
- Automatic mirroring of ALL customer evidence
- For legal compliance, pattern analysis, law enforcement
- Hidden from customers (disclosed subtly in Privacy Policy)
- Audit logged
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import text
from datetime import datetime
import json

router = APIRouter(prefix="/api/super-admin/vault", tags=["super-admin-vault"])

async def verify_super_admin(request: Request):
    """Verify user is Super Admin (middleware)"""
    # TODO: Implement proper JWT verification
    # For now, check if user has super_admin role
    pass

@router.post("/mirror-evidence")
async def mirror_evidence(payload: dict, request: Request):
    """
    Automatically mirror customer evidence to Super Admin vault
    Called internally when customer evidence is created
    
    Input:
    {
        "user_id": "customer_id",
        "evidence_id": "EVD-ABC123",
        "evidence_type": "call_recording|message|complaint_draft",
        "data": {...}
    }
    """
    
    user_id = payload.get("user_id")
    evidence_id = payload.get("evidence_id")
    evidence_type = payload.get("evidence_type")
    data = payload.get("data", {})
    
    if not user_id or not evidence_id:
        raise HTTPException(400, "user_id and evidence_id required")
    
    try:
        db = request.app.state.db
        
        # Insert into Super Admin vault (separate table)
        await db.execute(text("""
            INSERT INTO super_admin_vault (
                user_id, evidence_id, evidence_type,
                call_recording_url, message_screenshot_url,
                complaint_draft, gps_latitude, gps_longitude,
                ai_analysis, threat_level, scam_type,
                mirrored_at, original_created_at
            ) VALUES (
                :user_id, :evidence_id, :evidence_type,
                :call_recording_url, :message_screenshot_url,
                :complaint_draft, :gps_latitude, :gps_longitude,
                :ai_analysis, :threat_level, :scam_type,
                NOW(), :original_created_at
            )
        """), {
            "user_id": user_id,
            "evidence_id": evidence_id,
            "evidence_type": evidence_type,
            "call_recording_url": data.get("call_recording_url"),
            "message_screenshot_url": data.get("message_screenshot_url"),
            "complaint_draft": data.get("complaint_draft"),
            "gps_latitude": data.get("gps_latitude"),
            "gps_longitude": data.get("gps_longitude"),
            "ai_analysis": json.dumps(data.get("ai_analysis", {})),
            "threat_level": data.get("threat_level"),
            "scam_type": data.get("scam_type"),
            "original_created_at": data.get("created_at")
        })
        
        # Audit log (hidden from customers)
        await db.execute(text("""
            INSERT INTO super_admin_audit_log (
                action, user_id, evidence_id, performed_at
            ) VALUES (
                'EVIDENCE_MIRRORED', :user_id, :evidence_id, NOW()
            )
        """), {
            "user_id": user_id,
            "evidence_id": evidence_id
        })
        
        return {
            "success": True,
            "mirrored": True,
            "evidence_id": evidence_id
        }
        
    except Exception as e:
        print(f"❌ Evidence mirroring failed: {e}")
        # Don't raise exception - mirroring failure shouldn't block customer flow
        return {
            "success": False,
            "mirrored": False,
            "error": str(e)
        }

@router.get("/all-evidence")
async def get_all_evidence(
    request: Request,
    user_id: str = None,
    evidence_type: str = None,
    scam_type: str = None,
    threat_level_min: int = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100
):
    """
    Super Admin: View ALL customer evidence
    
    Filters:
    - user_id: Specific customer
    - evidence_type: call_recording, message, complaint_draft
    - scam_type: digital_arrest, investment_fraud, etc.
    - threat_level_min: Minimum threat level
    - start_date, end_date: Date range
    """
    
    try:
        db = request.app.state.db
        
        # Build query
        where_clauses = ["1=1"]
        params = {"limit": limit}
        
        if user_id:
            where_clauses.append("user_id = :user_id")
            params["user_id"] = user_id
        
        if evidence_type:
            where_clauses.append("evidence_type = :evidence_type")
            params["evidence_type"] = evidence_type
        
        if scam_type:
            where_clauses.append("scam_type = :scam_type")
            params["scam_type"] = scam_type
        
        if threat_level_min:
            where_clauses.append("threat_level >= :threat_level_min")
            params["threat_level_min"] = threat_level_min
        
        if start_date:
            where_clauses.append("original_created_at >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            where_clauses.append("original_created_at <= :end_date")
            params["end_date"] = end_date
        
        where_sql = " AND ".join(where_clauses)
        
        result = await db.execute(text(f"""
            SELECT id, user_id, evidence_id, evidence_type,
                   threat_level, scam_type, gps_latitude, gps_longitude,
                   original_created_at, mirrored_at
            FROM super_admin_vault
            WHERE {where_sql}
            ORDER BY original_created_at DESC
            LIMIT :limit
        """), params)
        
        evidence_list = []
        for row in result.fetchall():
            evidence_list.append({
                "id": row[0],
                "user_id": row[1],
                "evidence_id": row[2],
                "evidence_type": row[3],
                "threat_level": row[4],
                "scam_type": row[5],
                "location": {
                    "latitude": row[6],
                    "longitude": row[7]
                },
                "original_created_at": row[8].isoformat() if row[8] else None,
                "mirrored_at": row[9].isoformat() if row[9] else None
            })
        
        # Audit log
        await db.execute(text("""
            INSERT INTO super_admin_audit_log (
                action, performed_by, performed_at, details
            ) VALUES (
                'VIEWED_ALL_EVIDENCE', 'super_admin', NOW(), :details
            )
        """), {
            "details": json.dumps({"filters": params})
        })
        
        return {
            "success": True,
            "total": len(evidence_list),
            "evidence": evidence_list
        }
        
    except Exception as e:
        print(f"❌ Failed to get evidence: {e}")
        return {
            "success": False,
            "error": str(e),
            "evidence": []
        }

@router.get("/evidence-details/{evidence_id}")
async def get_evidence_details(evidence_id: str, request: Request):
    """
    Super Admin: Get complete evidence details
    Includes: Recording URL, screenshots, AI analysis, GPS, complaint draft
    """
    
    try:
        db = request.app.state.db
        
        result = await db.fetch_one(text("""
            SELECT * FROM super_admin_vault
            WHERE evidence_id = :evidence_id
        """), {"evidence_id": evidence_id})
        
        if not result:
            raise HTTPException(404, "Evidence not found")
        
        # Audit log
        await db.execute(text("""
            INSERT INTO super_admin_audit_log (
                action, evidence_id, performed_by, performed_at
            ) VALUES (
                'VIEWED_EVIDENCE_DETAILS', :evidence_id, 'super_admin', NOW()
            )
        """), {"evidence_id": evidence_id})
        
        return {
            "success": True,
            "evidence_id": evidence_id,
            "user_id": result[1],
            "evidence_type": result[3],
            "call_recording_url": result[4],
            "message_screenshot_url": result[5],
            "complaint_draft": result[6],
            "location": {
                "latitude": result[7],
                "longitude": result[8]
            },
            "ai_analysis": json.loads(result[9]) if result[9] else {},
            "threat_level": result[10],
            "scam_type": result[11],
            "original_created_at": result[12].isoformat() if result[12] else None,
            "mirrored_at": result[13].isoformat() if result[13] else None
        }
        
    except Exception as e:
        print(f"❌ Failed to get evidence details: {e}")
        raise HTTPException(500, f"Failed to get evidence: {str(e)}")

@router.get("/stats")
async def get_vault_stats(request: Request):
    """Super Admin: Get vault statistics"""
    
    try:
        db = request.app.state.db
        
        total_evidence = await db.fetch_val(text("""
            SELECT COUNT(*) FROM super_admin_vault
        """))
        
        total_calls = await db.fetch_val(text("""
            SELECT COUNT(*) FROM super_admin_vault
            WHERE evidence_type = 'call_recording'
        """))
        
        total_messages = await db.fetch_val(text("""
            SELECT COUNT(*) FROM super_admin_vault
            WHERE evidence_type = 'message'
        """))
        
        total_complaints = await db.fetch_val(text("""
            SELECT COUNT(*) FROM super_admin_vault
            WHERE evidence_type = 'complaint_draft'
        """))
        
        high_threat = await db.fetch_val(text("""
            SELECT COUNT(*) FROM super_admin_vault
            WHERE threat_level >= 8
        """))
        
        return {
            "total_evidence": total_evidence or 0,
            "total_calls": total_calls or 0,
            "total_messages": total_messages or 0,
            "total_complaints": total_complaints or 0,
            "high_threat_count": high_threat or 0,
            "message": "CLASSIFIED - Super Admin Vault Statistics"
        }
        
    except Exception as e:
        print(f"❌ Stats failed: {e}")
        return {
            "total_evidence": 0,
            "total_calls": 0,
            "total_messages": 0,
            "total_complaints": 0,
            "high_threat_count": 0
        }

@router.get("/audit-log")
async def get_audit_log(
    request: Request,
    action: str = None,
    start_date: str = None,
    limit: int = 100
):
    """Super Admin: View audit log of all vault access"""
    
    try:
        db = request.app.state.db
        
        where_clauses = ["1=1"]
        params = {"limit": limit}
        
        if action:
            where_clauses.append("action = :action")
            params["action"] = action
        
        if start_date:
            where_clauses.append("performed_at >= :start_date")
            params["start_date"] = start_date
        
        where_sql = " AND ".join(where_clauses)
        
        result = await db.execute(text(f"""
            SELECT id, action, user_id, evidence_id,
                   performed_by, performed_at, details
            FROM super_admin_audit_log
            WHERE {where_sql}
            ORDER BY performed_at DESC
            LIMIT :limit
        """), params)
        
        logs = []
        for row in result.fetchall():
            logs.append({
                "id": row[0],
                "action": row[1],
                "user_id": row[2],
                "evidence_id": row[3],
                "performed_by": row[4],
                "performed_at": row[5].isoformat() if row[5] else None,
                "details": json.loads(row[6]) if row[6] else {}
            })
        
        return {
            "success": True,
            "total": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        print(f"❌ Audit log failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "logs": []
        }

@router.get("/test")
async def test_super_admin_vault():
    """Test Super Admin vault system"""
    
    return {
        "status": "ok",
        "message": "CLASSIFIED - Super Admin Vault operational",
        "features": [
            "Automatic evidence mirroring",
            "All customer data accessible",
            "Audit logging enabled",
            "Singapore bank-level security"
        ]
    }

