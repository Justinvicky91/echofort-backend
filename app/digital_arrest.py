"""
Digital Arrest Detection API
AI-powered detection of fake police/CBI/court scam calls.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import psycopg
from app.deps import get_current_user, get_db
import os
import openai

router = APIRouter()

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")


class DigitalArrestAlert(BaseModel):
    id: Optional[str] = None
    user_id: str
    phone_number: str
    caller_claimed_identity: str  # "Police", "CBI", "Court", "Customs", etc.
    keywords_detected: List[str]  # ["arrest warrant", "money laundering", "immediate payment"]
    confidence_score: float  # 0.0 to 1.0
    is_scam: bool
    action_taken: str  # "blocked", "warned", "recorded"
    detected_at: datetime


class CallAnalysisRequest(BaseModel):
    phone_number: str
    call_transcript: Optional[str] = None
    caller_name: Optional[str] = None
    keywords: Optional[List[str]] = None


@router.post("/analyze-call")
async def analyze_call_for_digital_arrest(
    request: CallAnalysisRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Analyze incoming call for digital arrest scam patterns.
    Uses AI to detect fake law enforcement calls.
    """
    
    user_id = current_user["id"]
    
    # Digital arrest scam keywords
    scam_keywords = [
        "arrest warrant",
        "money laundering",
        "drug trafficking",
        "customs violation",
        "immediate payment",
        "bank account freeze",
        "legal action",
        "court summons",
        "CBI investigation",
        "police verification",
        "suspend your account",
        "verify your identity",
        "pay fine immediately",
        "arrest within 24 hours"
    ]
    
    # Check for keyword matches
    detected_keywords = []
    if request.call_transcript:
        transcript_lower = request.call_transcript.lower()
        detected_keywords = [kw for kw in scam_keywords if kw in transcript_lower]
    
    if request.keywords:
        detected_keywords.extend(request.keywords)
    
    # AI analysis using OpenAI
    is_scam = False
    confidence_score = 0.0
    caller_identity = request.caller_name or "Unknown"
    
    if request.call_transcript and len(request.call_transcript) > 20:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an AI scam detection expert specializing in "Digital Arrest" scams.
                        
Digital Arrest scams involve:
- Fake police/CBI/court officials calling victims
- Claiming arrest warrant, money laundering, or customs violations
- Demanding immediate payment to avoid arrest
- Threatening legal action or account freeze
- Creating panic and urgency

Analyze the call transcript and determine:
1. Is this a digital arrest scam? (true/false)
2. Confidence score (0.0 to 1.0)
3. Claimed identity (Police, CBI, Court, Customs, etc.)

Respond in JSON format:
{
  "is_scam": boolean,
  "confidence": float,
  "claimed_identity": string,
  "reasoning": string
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this call transcript:\n\n{request.call_transcript}"
                    }
                ],
                temperature=0.3
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            is_scam = result.get("is_scam", False)
            confidence_score = result.get("confidence", 0.0)
            caller_identity = result.get("claimed_identity", caller_identity)
            
        except Exception as e:
            print(f"OpenAI analysis error: {e}")
            # Fallback to keyword-based detection
            if len(detected_keywords) >= 2:
                is_scam = True
                confidence_score = min(len(detected_keywords) * 0.25, 0.95)
    
    else:
        # Keyword-based detection for calls without transcript
        if len(detected_keywords) >= 2:
            is_scam = True
            confidence_score = min(len(detected_keywords) * 0.25, 0.95)
    
    # Determine action
    action_taken = "monitored"
    if is_scam and confidence_score >= 0.7:
        action_taken = "blocked"
    elif is_scam and confidence_score >= 0.5:
        action_taken = "warned"
    
    # Save alert to database
    query = """
        INSERT INTO digital_arrest_alerts (
            user_id, phone_number, caller_claimed_identity,
            keywords_detected, confidence_score, is_scam,
            action_taken, detected_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    cursor = db.cursor()
    cursor.execute(query, (
        user_id,
        request.phone_number,
        caller_identity,
        detected_keywords,
        confidence_score,
        is_scam,
        action_taken,
        datetime.now()
    ))
    alert_id = cursor.fetchone()[0]
    db.commit()
    
    return {
        "alert_id": str(alert_id),
        "is_scam": is_scam,
        "confidence_score": confidence_score,
        "caller_claimed_identity": caller_identity,
        "keywords_detected": detected_keywords,
        "action_taken": action_taken,
        "recommendation": "BLOCK AND REPORT" if is_scam else "Monitor call",
        "warning_message": "⚠️ DIGITAL ARREST SCAM DETECTED! Do NOT pay any money. Real police/CBI never call for payments." if is_scam else None
    }


@router.get("/alerts", response_model=List[DigitalArrestAlert])
async def get_digital_arrest_alerts(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get user's digital arrest scam alerts"""
    
    user_id = current_user["id"]
    
    query = """
        SELECT * FROM digital_arrest_alerts
        WHERE user_id = %s
        ORDER BY detected_at DESC
        LIMIT %s OFFSET %s
    """
    
    cursor = db.cursor()
    cursor.execute(query, (user_id, limit, offset))
    alerts = cursor.fetchall()
    
    return [
        DigitalArrestAlert(
            id=str(a[0]),
            user_id=str(a[1]),
            phone_number=a[2],
            caller_claimed_identity=a[3],
            keywords_detected=a[4],
            confidence_score=a[5],
            is_scam=a[6],
            action_taken=a[7],
            detected_at=a[8]
        )
        for a in alerts
    ]


@router.get("/stats")
async def get_digital_arrest_stats(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get digital arrest detection statistics"""
    
    user_id = current_user["id"]
    
    query = """
        SELECT 
            COUNT(*) as total_alerts,
            COUNT(*) FILTER (WHERE is_scam = TRUE) as scams_detected,
            COUNT(*) FILTER (WHERE action_taken = 'blocked') as calls_blocked,
            AVG(confidence_score) FILTER (WHERE is_scam = TRUE) as avg_confidence
        FROM digital_arrest_alerts
        WHERE user_id = %s
    """
    
    cursor = db.cursor()
    cursor.execute(query, (user_id,))
    stats = cursor.fetchone()
    
    return {
        "total_alerts": stats[0] or 0,
        "scams_detected": stats[1] or 0,
        "calls_blocked": stats[2] or 0,
        "avg_confidence": float(stats[3]) if stats[3] else 0.0,
        "protection_rate": round((stats[2] or 0) / (stats[0] or 1) * 100, 2)
    }

