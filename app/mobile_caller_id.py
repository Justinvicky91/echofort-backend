"""
Mobile Caller ID API
Truecaller-like functionality for global caller identification
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy import text
from .deps import get_db, get_current_user

router = APIRouter(prefix="/api/mobile/caller-id", tags=["Mobile Caller ID"])


# Pydantic Models
class CallerIDLookupRequest(BaseModel):
    phoneNumber: str = Field(..., description="Phone number with country code")
    countryCode: Optional[str] = Field(None, description="ISO country code")


class CallerIDResponse(BaseModel):
    phoneNumber: str
    name: Optional[str] = None
    carrier: Optional[str] = None
    location: Optional[str] = None
    numberType: Optional[str] = None
    spamScore: int = 0
    totalReports: int = 0
    spamReports: int = 0
    safeReports: int = 0
    businessName: Optional[str] = None
    isVerified: bool = False
    tags: List[str] = []
    recommendation: str  # "safe", "caution", "block"


class ReportSpamRequest(BaseModel):
    phoneNumber: str
    reportType: str = Field(..., description="spam, scam, telemarketer, safe, wrong_number")
    spamCategory: Optional[str] = None
    description: Optional[str] = None
    confidence: int = Field(50, ge=0, le=100)


class BlockNumberRequest(BaseModel):
    phoneNumber: str
    reason: Optional[str] = None


class CallHistoryRequest(BaseModel):
    phoneNumber: str
    callType: str  # incoming, outgoing, missed
    duration: Optional[int] = None
    timestamp: datetime
    wasBlocked: bool = False
    spamScore: Optional[int] = None
    callerName: Optional[str] = None


@router.post("/lookup")
async def lookup_caller_id(
    request: CallerIDLookupRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Lookup caller ID information for a phone number
    Returns spam score, reports, and recommendation
    """
    try:
        phone = request.phoneNumber.strip()
        
        # Query caller ID database
        query = text("""
            SELECT 
                phone_number,
                name,
                carrier,
                location,
                number_type,
                spam_score,
                total_reports,
                spam_reports,
                safe_reports,
                business_name,
                is_verified,
                tags
            FROM caller_id_database
            WHERE phone_number = :phone
        """)
        
        result = db.execute(query, {"phone": phone}).fetchone()
        
        if result:
            spam_score = result[5] or 0
            
            # Determine recommendation
            if spam_score >= 70:
                recommendation = "block"
            elif spam_score >= 40:
                recommendation = "caution"
            else:
                recommendation = "safe"
            
            return {
                "ok": True,
                "caller": {
                    "phoneNumber": result[0],
                    "name": result[1],
                    "carrier": result[2],
                    "location": result[3],
                    "numberType": result[4],
                    "spamScore": spam_score,
                    "totalReports": result[6] or 0,
                    "spamReports": result[7] or 0,
                    "safeReports": result[8] or 0,
                    "businessName": result[9],
                    "isVerified": result[10] or False,
                    "tags": result[11] or [],
                    "recommendation": recommendation
                }
            }
        else:
            # Number not in database - return default
            return {
                "ok": True,
                "caller": {
                    "phoneNumber": phone,
                    "name": None,
                    "carrier": None,
                    "location": None,
                    "numberType": "unknown",
                    "spamScore": 0,
                    "totalReports": 0,
                    "spamReports": 0,
                    "safeReports": 0,
                    "businessName": None,
                    "isVerified": False,
                    "tags": [],
                    "recommendation": "unknown"
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lookup failed: {str(e)}")


@router.post("/report-spam")
async def report_spam(
    request: ReportSpamRequest,
    req: Request,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Report a phone number as spam/scam
    """
    try:
        # Get client IP
        client_ip = req.client.host
        
        # Insert report
        query = text("""
            INSERT INTO caller_id_reports 
            (phone_number, reported_by, report_type, spam_category, description, confidence, ip_address)
            VALUES (:phone, :user_id, :report_type, :category, :description, :confidence, :ip)
            RETURNING id
        """)
        
        result = db.execute(query, {
            "phone": request.phoneNumber,
            "user_id": current_user["id"],
            "report_type": request.reportType,
            "category": request.spamCategory,
            "description": request.description,
            "confidence": request.confidence,
            "ip": client_ip
        })
        
        report_id = result.fetchone()[0]
        db.commit()
        
        # Update user trust score
        trust_query = text("""
            INSERT INTO user_trust_scores (user_id, reports_submitted, trust_score)
            VALUES (:user_id, 1, 50)
            ON CONFLICT (user_id) DO UPDATE
            SET reports_submitted = user_trust_scores.reports_submitted + 1,
                last_updated = CURRENT_TIMESTAMP
        """)
        db.execute(trust_query, {"user_id": current_user["id"]})
        db.commit()
        
        return {
            "ok": True,
            "reportId": report_id,
            "message": "Thank you for reporting. Your contribution helps protect the community."
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Report failed: {str(e)}")


@router.get("/my-reports")
async def get_my_reports(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user's spam reports
    """
    try:
        query = text("""
            SELECT 
                id,
                phone_number,
                report_type,
                spam_category,
                description,
                confidence,
                reported_at
            FROM caller_id_reports
            WHERE reported_by = :user_id
            ORDER BY reported_at DESC
            LIMIT 100
        """)
        
        results = db.execute(query, {"user_id": current_user["id"]}).fetchall()
        
        reports = []
        for row in results:
            reports.append({
                "id": row[0],
                "phoneNumber": row[1],
                "reportType": row[2],
                "spamCategory": row[3],
                "description": row[4],
                "confidence": row[5],
                "reportedAt": row[6].isoformat() if row[6] else None
            })
        
        return {"ok": True, "reports": reports}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/block-number")
async def block_number(
    request: BlockNumberRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Block a phone number for the current user
    """
    try:
        query = text("""
            INSERT INTO blocked_numbers (user_id, phone_number, reason)
            VALUES (:user_id, :phone, :reason)
            ON CONFLICT (user_id, phone_number) DO NOTHING
            RETURNING id
        """)
        
        result = db.execute(query, {
            "user_id": current_user["id"],
            "phone": request.phoneNumber,
            "reason": request.reason
        })
        
        db.commit()
        
        return {
            "ok": True,
            "message": f"Number {request.phoneNumber} has been blocked"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blocked-numbers")
async def get_blocked_numbers(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user's blocked numbers
    """
    try:
        query = text("""
            SELECT phone_number, reason, blocked_at
            FROM blocked_numbers
            WHERE user_id = :user_id
            ORDER BY blocked_at DESC
        """)
        
        results = db.execute(query, {"user_id": current_user["id"]}).fetchall()
        
        blocked = []
        for row in results:
            blocked.append({
                "phoneNumber": row[0],
                "reason": row[1],
                "blockedAt": row[2].isoformat() if row[2] else None
            })
        
        return {"ok": True, "blockedNumbers": blocked}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/unblock/{phoneNumber}")
async def unblock_number(
    phoneNumber: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Unblock a phone number
    """
    try:
        query = text("""
            DELETE FROM blocked_numbers
            WHERE user_id = :user_id AND phone_number = :phone
            RETURNING id
        """)
        
        result = db.execute(query, {
            "user_id": current_user["id"],
            "phone": phoneNumber
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Number not found in blocked list")
        
        db.commit()
        
        return {
            "ok": True,
            "message": f"Number {phoneNumber} has been unblocked"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whitelist")
async def add_to_whitelist(
    phoneNumber: str,
    name: Optional[str] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Add a phone number to whitelist (always allow)
    """
    try:
        query = text("""
            INSERT INTO whitelisted_numbers (user_id, phone_number, name)
            VALUES (:user_id, :phone, :name)
            ON CONFLICT (user_id, phone_number) DO UPDATE
            SET name = :name
            RETURNING id
        """)
        
        db.execute(query, {
            "user_id": current_user["id"],
            "phone": phoneNumber,
            "name": name
        })
        
        db.commit()
        
        return {
            "ok": True,
            "message": f"Number {phoneNumber} added to whitelist"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/whitelist")
async def get_whitelist(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user's whitelisted numbers
    """
    try:
        query = text("""
            SELECT phone_number, name, whitelisted_at
            FROM whitelisted_numbers
            WHERE user_id = :user_id
            ORDER BY whitelisted_at DESC
        """)
        
        results = db.execute(query, {"user_id": current_user["id"]}).fetchall()
        
        whitelist = []
        for row in results:
            whitelist.append({
                "phoneNumber": row[0],
                "name": row[1],
                "whitelistedAt": row[2].isoformat() if row[2] else None
            })
        
        return {"ok": True, "whitelist": whitelist}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/call-history")
async def log_call_history(
    request: CallHistoryRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Log a call to history (for pattern detection)
    """
    try:
        query = text("""
            INSERT INTO call_history 
            (user_id, phone_number, call_type, duration, timestamp, was_blocked, spam_score, caller_name)
            VALUES (:user_id, :phone, :call_type, :duration, :timestamp, :was_blocked, :spam_score, :caller_name)
            RETURNING id
        """)
        
        result = db.execute(query, {
            "user_id": current_user["id"],
            "phone": request.phoneNumber,
            "call_type": request.callType,
            "duration": request.duration,
            "timestamp": request.timestamp,
            "was_blocked": request.wasBlocked,
            "spam_score": request.spamScore,
            "caller_name": request.callerName
        })
        
        call_id = result.fetchone()[0]
        db.commit()
        
        return {"ok": True, "callId": call_id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/call-history")
async def get_call_history(
    limit: int = 50,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user's call history
    """
    try:
        query = text("""
            SELECT 
                phone_number,
                call_type,
                duration,
                timestamp,
                was_blocked,
                spam_score,
                caller_name
            FROM call_history
            WHERE user_id = :user_id
            ORDER BY timestamp DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {
            "user_id": current_user["id"],
            "limit": limit
        }).fetchall()
        
        history = []
        for row in results:
            history.append({
                "phoneNumber": row[0],
                "callType": row[1],
                "duration": row[2],
                "timestamp": row[3].isoformat() if row[3] else None,
                "wasBlocked": row[4],
                "spamScore": row[5],
                "callerName": row[6]
            })
        
        return {"ok": True, "callHistory": history}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get caller ID protection statistics
    """
    try:
        # Get various stats
        stats_query = text("""
            SELECT 
                (SELECT COUNT(*) FROM blocked_numbers WHERE user_id = :user_id) as blocked_count,
                (SELECT COUNT(*) FROM whitelisted_numbers WHERE user_id = :user_id) as whitelist_count,
                (SELECT COUNT(*) FROM caller_id_reports WHERE reported_by = :user_id) as reports_count,
                (SELECT COUNT(*) FROM call_history WHERE user_id = :user_id AND was_blocked = true) as calls_blocked,
                (SELECT COUNT(*) FROM call_history WHERE user_id = :user_id) as total_calls
        """)
        
        result = db.execute(stats_query, {"user_id": current_user["id"]}).fetchone()
        
        return {
            "ok": True,
            "statistics": {
                "blockedNumbers": result[0] or 0,
                "whitelistedNumbers": result[1] or 0,
                "reportsSubmitted": result[2] or 0,
                "callsBlocked": result[3] or 0,
                "totalCalls": result[4] or 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
