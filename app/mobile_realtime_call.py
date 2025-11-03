"""
Mobile Real-Time Call Analysis API
AI-powered real-time call monitoring and scam detection
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import text
from .utils import get_current_user
from .deps import get_db

router = APIRouter(prefix="/api/mobile/realtime-call", tags=["Mobile Real-Time Call"])


class StartCallRequest(BaseModel):
    phoneNumber: str
    callerName: Optional[str] = None
    callDirection: str = Field(..., description="incoming or outgoing")


class TranscriptionRequest(BaseModel):
    sessionId: int
    speaker: str = Field(..., description="user or caller")
    text: str
    language: str = "en"
    confidence: Optional[float] = None
    timestampOffset: Optional[int] = None  # Milliseconds from call start


class EndCallRequest(BaseModel):
    sessionId: int
    callDurationSeconds: int
    recordingUrl: Optional[str] = None


class AlertResponseRequest(BaseModel):
    alertId: int
    userResponse: str = Field(..., description="dismissed, blocked_call, reported, etc.")


@router.post("/start")
async def start_call_session(
    request: StartCallRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Start a new real-time call analysis session
    """
    try:
        query = text("""
            INSERT INTO realtime_call_sessions 
            (user_id, phone_number, caller_name, call_direction, is_active)
            VALUES (:user_id, :phone_number, :caller_name, :call_direction, TRUE)
            RETURNING id
        """)
        
        session_id = db.execute(query, {
            "user_id": current_user["id"],
            "phone_number": request.phoneNumber,
            "caller_name": request.callerName,
            "call_direction": request.callDirection
        }).fetchone()[0]
        
        db.commit()
        
        return {
            "ok": True,
            "sessionId": session_id,
            "message": "Call session started"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcription")
async def add_transcription(
    request: TranscriptionRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Add transcription segment and analyze for scam patterns
    """
    try:
        # Verify session belongs to user
        verify_query = text("""
            SELECT user_id FROM realtime_call_sessions WHERE id = :session_id
        """)
        result = db.execute(verify_query, {"session_id": request.sessionId}).fetchone()
        
        if not result or result[0] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Insert transcription
        trans_query = text("""
            INSERT INTO realtime_call_transcription 
            (session_id, speaker, text, language, confidence, timestamp_offset)
            VALUES (:session_id, :speaker, :text, :language, :confidence, :timestamp_offset)
            RETURNING id
        """)
        
        trans_id = db.execute(trans_query, {
            "session_id": request.sessionId,
            "speaker": request.speaker,
            "text": request.text,
            "language": request.language,
            "confidence": request.confidence,
            "timestamp_offset": request.timestampOffset
        }).fetchone()[0]
        
        # Analyze transcription for scam patterns
        analysis_query = text("""
            SELECT analyze_call_realtime(:session_id, :text, :speaker)
        """)
        
        analysis_result = db.execute(analysis_query, {
            "session_id": request.sessionId,
            "text": request.text,
            "speaker": request.speaker
        }).fetchone()[0]
        
        db.commit()
        
        return {
            "ok": True,
            "transcriptionId": trans_id,
            "analysis": analysis_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/alerts")
async def get_session_alerts(
    session_id: int,
    unread_only: bool = False,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get alerts for a call session
    """
    try:
        # Verify session belongs to user
        verify_query = text("""
            SELECT user_id FROM realtime_call_sessions WHERE id = :session_id
        """)
        result = db.execute(verify_query, {"session_id": session_id}).fetchone()
        
        if not result or result[0] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Session not found")
        
        shown_filter = "AND was_shown = FALSE" if unread_only else ""
        
        query = text(f"""
            SELECT 
                id, alert_type, severity, title, message, 
                recommended_action, was_shown, user_response, triggered_at
            FROM realtime_call_alerts
            WHERE session_id = :session_id {shown_filter}
            ORDER BY triggered_at DESC
        """)
        
        results = db.execute(query, {"session_id": session_id}).fetchall()
        
        alerts = []
        for row in results:
            alerts.append({
                "id": row[0],
                "alertType": row[1],
                "severity": row[2],
                "title": row[3],
                "message": row[4],
                "recommendedAction": row[5],
                "wasShown": row[6],
                "userResponse": row[7],
                "triggeredAt": row[8].isoformat() if row[8] else None
            })
        
        return {"ok": True, "alerts": alerts}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/alert/{alert_id}/respond")
async def respond_to_alert(
    alert_id: int,
    request: AlertResponseRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Record user response to an alert
    """
    try:
        # Verify alert belongs to user's session
        verify_query = text("""
            SELECT rcs.user_id 
            FROM realtime_call_alerts rca
            JOIN realtime_call_sessions rcs ON rca.session_id = rcs.id
            WHERE rca.id = :alert_id
        """)
        result = db.execute(verify_query, {"alert_id": alert_id}).fetchone()
        
        if not result or result[0] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        query = text("""
            UPDATE realtime_call_alerts
            SET was_shown = TRUE,
                user_response = :user_response
            WHERE id = :alert_id
            RETURNING id
        """)
        
        db.execute(query, {
            "alert_id": alert_id,
            "user_response": request.userResponse
        })
        
        db.commit()
        
        return {"ok": True, "message": "Response recorded"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end")
async def end_call_session(
    request: EndCallRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    End a call session and finalize analysis
    """
    try:
        # Verify session belongs to user
        verify_query = text("""
            SELECT user_id FROM realtime_call_sessions WHERE id = :session_id
        """)
        result = db.execute(verify_query, {"session_id": request.sessionId}).fetchone()
        
        if not result or result[0] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # End session
        query = text("""
            UPDATE realtime_call_sessions
            SET is_active = FALSE,
                call_ended_at = CURRENT_TIMESTAMP,
                call_duration_seconds = :duration,
                recording_url = :recording_url,
                analysis_status = 'completed'
            WHERE id = :session_id
            RETURNING id
        """)
        
        db.execute(query, {
            "session_id": request.sessionId,
            "duration": request.callDurationSeconds,
            "recording_url": request.recordingUrl
        })
        
        # Update statistics
        stats_query = text("""
            INSERT INTO call_analysis_statistics (user_id, total_calls_analyzed, last_analysis_at)
            VALUES (:user_id, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE
            SET total_calls_analyzed = call_analysis_statistics.total_calls_analyzed + 1,
                last_analysis_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """)
        db.execute(stats_query, {"user_id": current_user["id"]})
        
        db.commit()
        
        return {"ok": True, "message": "Call session ended"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/analysis")
async def get_session_analysis(
    session_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get complete analysis for a call session
    """
    try:
        # Verify session belongs to user
        verify_query = text("""
            SELECT user_id FROM realtime_call_sessions WHERE id = :session_id
        """)
        result = db.execute(verify_query, {"session_id": session_id}).fetchone()
        
        if not result or result[0] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get all analysis results
        query = text("""
            SELECT 
                scam_probability, threat_level, detected_patterns, 
                keywords_detected, voice_analysis, sentiment_score,
                confidence_score, recommended_action, ai_explanation,
                analysis_timestamp
            FROM realtime_call_analysis
            WHERE session_id = :session_id
            ORDER BY analysis_timestamp DESC
        """)
        
        results = db.execute(query, {"session_id": session_id}).fetchall()
        
        analyses = []
        for row in results:
            analyses.append({
                "scamProbability": float(row[0]) if row[0] else 0,
                "threatLevel": row[1],
                "detectedPatterns": row[2],
                "keywordsDetected": row[3],
                "voiceAnalysis": row[4],
                "sentimentScore": float(row[5]) if row[5] else None,
                "confidenceScore": float(row[6]) if row[6] else None,
                "recommendedAction": row[7],
                "aiExplanation": row[8],
                "analysisTimestamp": row[9].isoformat() if row[9] else None
            })
        
        # Get final summary
        if analyses:
            final_analysis = analyses[0]  # Most recent
            return {
                "ok": True,
                "finalAnalysis": final_analysis,
                "allAnalyses": analyses
            }
        else:
            return {
                "ok": True,
                "finalAnalysis": None,
                "allAnalyses": []
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/transcription")
async def get_session_transcription(
    session_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get full transcription for a call session
    """
    try:
        # Verify session belongs to user
        verify_query = text("""
            SELECT user_id FROM realtime_call_sessions WHERE id = :session_id
        """)
        result = db.execute(verify_query, {"session_id": session_id}).fetchone()
        
        if not result or result[0] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Session not found")
        
        query = text("""
            SELECT 
                speaker, text, language, confidence, 
                timestamp_offset, is_suspicious, flagged_keywords, created_at
            FROM realtime_call_transcription
            WHERE session_id = :session_id
            ORDER BY timestamp_offset ASC, created_at ASC
        """)
        
        results = db.execute(query, {"session_id": session_id}).fetchall()
        
        transcription = []
        for row in results:
            transcription.append({
                "speaker": row[0],
                "text": row[1],
                "language": row[2],
                "confidence": float(row[3]) if row[3] else None,
                "timestampOffset": row[4],
                "isSuspicious": row[5],
                "flaggedKeywords": row[6],
                "createdAt": row[7].isoformat() if row[7] else None
            })
        
        return {"ok": True, "transcription": transcription}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_call_analysis_statistics(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user's call analysis statistics
    """
    try:
        query = text("""
            SELECT 
                total_calls_analyzed, total_scams_detected, total_warnings_shown,
                total_calls_blocked, average_scam_probability, highest_threat_level,
                last_analysis_at
            FROM call_analysis_statistics
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": current_user["id"]}).fetchone()
        
        if result:
            return {
                "ok": True,
                "statistics": {
                    "totalCallsAnalyzed": result[0] or 0,
                    "totalScamsDetected": result[1] or 0,
                    "totalWarningsShown": result[2] or 0,
                    "totalCallsBlocked": result[3] or 0,
                    "averageScamProbability": float(result[4]) if result[4] else 0,
                    "highestThreatLevel": result[5],
                    "lastAnalysisAt": result[6].isoformat() if result[6] else None
                }
            }
        else:
            return {
                "ok": True,
                "statistics": {
                    "totalCallsAnalyzed": 0,
                    "totalScamsDetected": 0,
                    "totalWarningsShown": 0,
                    "totalCallsBlocked": 0,
                    "averageScamProbability": 0,
                    "highestThreatLevel": None,
                    "lastAnalysisAt": None
                }
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-sessions")
async def get_recent_sessions(
    limit: int = 20,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get recent call sessions
    """
    try:
        query = text("""
            SELECT 
                id, phone_number, caller_name, call_direction,
                call_started_at, call_ended_at, call_duration_seconds,
                is_active, was_recorded, analysis_status
            FROM realtime_call_sessions
            WHERE user_id = :user_id
            ORDER BY call_started_at DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {
            "user_id": current_user["id"],
            "limit": limit
        }).fetchall()
        
        sessions = []
        for row in results:
            sessions.append({
                "id": row[0],
                "phoneNumber": row[1],
                "callerName": row[2],
                "callDirection": row[3],
                "callStartedAt": row[4].isoformat() if row[4] else None,
                "callEndedAt": row[5].isoformat() if row[5] else None,
                "callDurationSeconds": row[6],
                "isActive": row[7],
                "wasRecorded": row[8],
                "analysisStatus": row[9]
            })
        
        return {"ok": True, "sessions": sessions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
