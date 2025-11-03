"""
Mobile SMS Scam Detection API
Real-time SMS scanning and threat detection
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy import text
from .utils import get_current_user
from .deps import get_db

router = APIRouter(prefix="/api/mobile/sms", tags=["Mobile SMS Detection"])


# Pydantic Models
class SMSScanRequest(BaseModel):
    sender: str = Field(..., description="SMS sender ID or phone number")
    message: str = Field(..., description="SMS message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SMSReportRequest(BaseModel):
    sender: str
    message: str
    scamType: str
    description: Optional[str] = None


@router.post("/scan")
async def scan_sms(
    request: SMSScanRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Scan an SMS message for scam indicators
    Returns scam score and detected threats
    """
    try:
        # Use the database function to calculate scam score
        query = text("""
            SELECT * FROM calculate_sms_scam_score(:message, :sender)
        """)
        
        result = db.execute(query, {
            "message": request.message,
            "sender": request.sender
        }).fetchone()
        
        scam_score = result[0] if result else 0
        scam_type = result[1] if result else "unknown"
        indicators = result[2] if result else []
        
        is_scam = scam_score >= 60
        
        # Determine action
        if scam_score >= 80:
            action = "block"
        elif scam_score >= 60:
            action = "quarantine"
        else:
            action = "allow"
        
        # Log the threat
        log_query = text("""
            INSERT INTO sms_threats 
            (user_id, sender, message_text, received_at, is_scam, scam_score, scam_type, indicators, action_taken)
            VALUES (:user_id, :sender, :message, :timestamp, :is_scam, :score, :type, :indicators, :action)
            RETURNING id
        """)
        
        threat_id = db.execute(log_query, {
            "user_id": current_user["id"],
            "sender": request.sender,
            "message": request.message,
            "timestamp": request.timestamp,
            "is_scam": is_scam,
            "score": scam_score,
            "type": scam_type,
            "indicators": indicators,
            "action": action
        }).fetchone()[0]
        
        # Update statistics
        stats_query = text("""
            INSERT INTO sms_statistics (user_id, total_sms_scanned, threats_detected, threats_blocked, last_scan_at, last_threat_at)
            VALUES (:user_id, 1, :threats, :blocked, :now, :threat_time)
            ON CONFLICT (user_id) DO UPDATE
            SET total_sms_scanned = sms_statistics.total_sms_scanned + 1,
                threats_detected = sms_statistics.threats_detected + :threats,
                threats_blocked = sms_statistics.threats_blocked + :blocked,
                last_scan_at = :now,
                last_threat_at = CASE WHEN :is_scam THEN :threat_time ELSE sms_statistics.last_threat_at END,
                updated_at = :now
        """)
        
        db.execute(stats_query, {
            "user_id": current_user["id"],
            "threats": 1 if is_scam else 0,
            "blocked": 1 if action == "block" else 0,
            "now": datetime.utcnow(),
            "threat_time": request.timestamp if is_scam else None,
            "is_scam": is_scam
        })
        
        db.commit()
        
        return {
            "ok": True,
            "threatId": threat_id,
            "isScam": is_scam,
            "scamScore": scam_score,
            "scamType": scam_type,
            "indicators": indicators,
            "action": action,
            "recommendation": "Block this sender" if action == "block" else "Be cautious" if action == "quarantine" else "Safe"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"SMS scan failed: {str(e)}")


@router.get("/threats")
async def get_sms_threats(
    limit: int = 50,
    scam_only: bool = False,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get detected SMS threats for the user
    """
    try:
        scam_filter = "AND is_scam = true" if scam_only else ""
        
        query = text(f"""
            SELECT 
                id,
                sender,
                message_text,
                received_at,
                is_scam,
                scam_score,
                scam_type,
                indicators,
                action_taken
            FROM sms_threats
            WHERE user_id = :user_id {scam_filter}
            ORDER BY received_at DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {
            "user_id": current_user["id"],
            "limit": limit
        }).fetchall()
        
        threats = []
        for row in results:
            threats.append({
                "id": row[0],
                "sender": row[1],
                "message": row[2],
                "receivedAt": row[3].isoformat() if row[3] else None,
                "isScam": row[4],
                "scamScore": row[5],
                "scamType": row[6],
                "indicators": row[7],
                "actionTaken": row[8]
            })
        
        return {"ok": True, "threats": threats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report")
async def report_sms_scam(
    request: SMSReportRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Report an SMS as scam to help the community
    """
    try:
        query = text("""
            INSERT INTO sms_scam_reports 
            (sender, message_text, reported_by, scam_type, description)
            VALUES (:sender, :message, :user_id, :scam_type, :description)
            RETURNING id
        """)
        
        report_id = db.execute(query, {
            "sender": request.sender,
            "message": request.message,
            "user_id": current_user["id"],
            "scam_type": request.scamType,
            "description": request.description
        }).fetchone()[0]
        
        # Update user statistics
        stats_query = text("""
            UPDATE sms_statistics
            SET reports_submitted = reports_submitted + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
        """)
        db.execute(stats_query, {"user_id": current_user["id"]})
        
        db.commit()
        
        return {
            "ok": True,
            "reportId": report_id,
            "message": "Thank you for reporting. Your contribution helps protect others."
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_sms_statistics(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get SMS protection statistics for the user
    """
    try:
        query = text("""
            SELECT 
                total_sms_scanned,
                threats_detected,
                threats_blocked,
                reports_submitted,
                last_scan_at,
                last_threat_at
            FROM sms_statistics
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": current_user["id"]}).fetchone()
        
        if result:
            return {
                "ok": True,
                "statistics": {
                    "totalSmsScanned": result[0] or 0,
                    "threatsDetected": result[1] or 0,
                    "threatsBlocked": result[2] or 0,
                    "reportsSubmitted": result[3] or 0,
                    "lastScanAt": result[4].isoformat() if result[4] else None,
                    "lastThreatAt": result[5].isoformat() if result[5] else None
                }
            }
        else:
            return {
                "ok": True,
                "statistics": {
                    "totalSmsScanned": 0,
                    "threatsDetected": 0,
                    "threatsBlocked": 0,
                    "reportsSubmitted": 0,
                    "lastScanAt": None,
                    "lastThreatAt": None
                }
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/threat/{threat_id}")
async def delete_sms_threat(
    threat_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Delete an SMS threat from history
    """
    try:
        query = text("""
            DELETE FROM sms_threats
            WHERE id = :threat_id AND user_id = :user_id
            RETURNING id
        """)
        
        result = db.execute(query, {
            "threat_id": threat_id,
            "user_id": current_user["id"]
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Threat not found")
        
        db.commit()
        
        return {"ok": True, "message": "Threat deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-scams")
async def get_recent_scams(
    limit: int = 20,
    db=Depends(get_db)
):
    """
    Get recent community-reported scams (public endpoint)
    """
    try:
        query = text("""
            SELECT 
                sender,
                scam_type,
                COUNT(*) as report_count,
                MAX(reported_at) as last_reported
            FROM sms_scam_reports
            WHERE reported_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
            GROUP BY sender, scam_type
            HAVING COUNT(*) >= 3
            ORDER BY report_count DESC, last_reported DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {"limit": limit}).fetchall()
        
        scams = []
        for row in results:
            scams.append({
                "sender": row[0],
                "scamType": row[1],
                "reportCount": row[2],
                "lastReported": row[3].isoformat() if row[3] else None
            })
        
        return {"ok": True, "recentScams": scams}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
