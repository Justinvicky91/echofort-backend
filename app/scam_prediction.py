# app/scam_prediction.py - Scam Prediction Engine
"""
Scam Prediction Engine - ML-based Scam Risk Assessment
Predicts scam likelihood based on multiple factors
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from .utils import get_current_user
import re

router = APIRouter(prefix="/api/scam-prediction", tags=["Scam Prediction"])


class PredictionRequest(BaseModel):
    caller_phone: Optional[str] = None
    caller_email: Optional[str] = None
    message_content: Optional[str] = None
    call_duration: Optional[int] = None  # seconds
    time_of_call: Optional[str] = None
    amount_mentioned: Optional[float] = None
    url_in_message: Optional[str] = None
    caller_location: Optional[str] = None


class PredictionResult(BaseModel):
    risk_score: float  # 0.0 to 1.0
    risk_level: str  # low, medium, high, critical
    scam_type: Optional[str]
    confidence: float
    factors: List[str]
    recommendation: str


def analyze_phone_number(phone: str) -> dict:
    """
    Analyze phone number for scam indicators
    Returns: {risk_score, factors}
    """
    risk_score = 0.0
    factors = []
    
    if not phone:
        return {"risk_score": 0.0, "factors": []}
    
    # Remove spaces and special characters
    clean_phone = re.sub(r'[^0-9+]', '', phone)
    
    # International number (higher risk)
    if clean_phone.startswith('+') and not clean_phone.startswith('+91'):
        risk_score += 0.3
        factors.append("International number")
    
    # Suspicious patterns
    if len(set(clean_phone[-4:])) == 1:  # Last 4 digits same
        risk_score += 0.2
        factors.append("Repetitive number pattern")
    
    # VoIP/Virtual numbers (often used by scammers)
    voip_prefixes = ['0000', '1111', '9999']
    if any(clean_phone.endswith(prefix) for prefix in voip_prefixes):
        risk_score += 0.25
        factors.append("Possible VoIP number")
    
    return {"risk_score": min(risk_score, 1.0), "factors": factors}


def analyze_message_content(content: str) -> dict:
    """
    Analyze message content for scam indicators
    Returns: {risk_score, scam_type, factors}
    """
    if not content:
        return {"risk_score": 0.0, "scam_type": None, "factors": []}
    
    content_lower = content.lower()
    risk_score = 0.0
    factors = []
    scam_type = None
    
    # Urgency keywords
    urgency_keywords = ['urgent', 'immediately', 'within 24 hours', 'expire', 'last chance', 'act now']
    urgency_count = sum(1 for kw in urgency_keywords if kw in content_lower)
    if urgency_count > 0:
        risk_score += urgency_count * 0.15
        factors.append(f"Urgency tactics ({urgency_count} keywords)")
    
    # Financial keywords
    financial_keywords = ['bank account', 'credit card', 'otp', 'pin', 'cvv', 'password', 'transfer money']
    financial_count = sum(1 for kw in financial_keywords if kw in content_lower)
    if financial_count >= 2:
        risk_score += 0.3
        factors.append("Multiple financial keywords")
    
    # Authority impersonation
    authority_keywords = ['police', 'cbi', 'income tax', 'customs', 'rbi', 'government']
    if any(kw in content_lower for kw in authority_keywords):
        risk_score += 0.35
        factors.append("Authority impersonation")
        scam_type = "digital_arrest"
    
    # Prize/Lottery scam
    prize_keywords = ['won', 'prize', 'lottery', 'congratulations', 'claim']
    if any(kw in content_lower for kw in prize_keywords):
        risk_score += 0.3
        factors.append("Prize/lottery language")
        scam_type = "lottery_scam"
    
    # Investment scam
    investment_keywords = ['guaranteed returns', 'risk-free', 'double your money', 'investment opportunity']
    if any(kw in content_lower for kw in investment_keywords):
        risk_score += 0.4
        factors.append("Investment fraud indicators")
        scam_type = "investment_fraud"
    
    # Suspicious links
    if re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content):
        risk_score += 0.2
        factors.append("Contains URL")
    
    # Shortened URLs (high risk)
    short_url_domains = ['bit.ly', 'tinyurl', 'goo.gl', 't.co', 'ow.ly']
    if any(domain in content_lower for domain in short_url_domains):
        risk_score += 0.3
        factors.append("Shortened URL detected")
    
    return {
        "risk_score": min(risk_score, 1.0),
        "scam_type": scam_type,
        "factors": factors
    }


def analyze_call_pattern(duration: int, time_of_call: str) -> dict:
    """
    Analyze call patterns for scam indicators
    Returns: {risk_score, factors}
    """
    risk_score = 0.0
    factors = []
    
    # Very short calls (likely robocalls)
    if duration and duration < 10:
        risk_score += 0.2
        factors.append("Very short call duration")
    
    # Very long calls (scammers keep victims engaged)
    if duration and duration > 600:  # 10 minutes
        risk_score += 0.15
        factors.append("Unusually long call")
    
    # Late night calls (suspicious)
    if time_of_call:
        try:
            hour = int(time_of_call.split(':')[0])
            if hour >= 22 or hour <= 6:
                risk_score += 0.2
                factors.append("Late night/early morning call")
        except:
            pass
    
    return {"risk_score": min(risk_score, 1.0), "factors": factors}


def analyze_amount(amount: float) -> dict:
    """
    Analyze mentioned amount for scam indicators
    Returns: {risk_score, factors}
    """
    risk_score = 0.0
    factors = []
    
    if not amount:
        return {"risk_score": 0.0, "factors": []}
    
    # Suspiciously round numbers
    if amount % 1000 == 0 and amount >= 10000:
        risk_score += 0.15
        factors.append("Round number amount")
    
    # Very large amounts
    if amount >= 100000:
        risk_score += 0.25
        factors.append("Large amount mentioned")
    
    # Common scam amounts
    common_scam_amounts = [999, 1999, 4999, 9999, 49999, 99999]
    if any(abs(amount - scam_amt) < 10 for scam_amt in common_scam_amounts):
        risk_score += 0.2
        factors.append("Common scam amount pattern")
    
    return {"risk_score": min(risk_score, 1.0), "factors": factors}


@router.post("/predict")
async def predict_scam(
    request: Request,
    payload: PredictionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Predict scam likelihood based on multiple factors
    Returns comprehensive risk assessment
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Analyze each factor
        phone_analysis = analyze_phone_number(payload.caller_phone)
        message_analysis = analyze_message_content(payload.message_content)
        call_analysis = analyze_call_pattern(payload.call_duration, payload.time_of_call)
        amount_analysis = analyze_amount(payload.amount_mentioned)
        
        # Combine risk scores (weighted average)
        total_risk = (
            phone_analysis["risk_score"] * 0.2 +
            message_analysis["risk_score"] * 0.4 +
            call_analysis["risk_score"] * 0.2 +
            amount_analysis["risk_score"] * 0.2
        )
        
        # Combine factors
        all_factors = (
            phone_analysis["factors"] +
            message_analysis["factors"] +
            call_analysis["factors"] +
            amount_analysis["factors"]
        )
        
        # Determine risk level
        if total_risk >= 0.75:
            risk_level = "critical"
            recommendation = "🚨 CRITICAL RISK - Block immediately and report to authorities"
        elif total_risk >= 0.5:
            risk_level = "high"
            recommendation = "⚠️ HIGH RISK - Do not share any information or make payments"
        elif total_risk >= 0.3:
            risk_level = "medium"
            recommendation = "⚡ MODERATE RISK - Proceed with extreme caution"
        else:
            risk_level = "low"
            recommendation = "✓ LOW RISK - Still verify before sharing sensitive information"
        
        # Determine scam type
        scam_type = message_analysis.get("scam_type")
        
        # Calculate confidence
        factor_count = len(all_factors)
        confidence = min(0.95, 0.5 + (factor_count * 0.1))
        
        # Save prediction to database
        save_query = text("""
            INSERT INTO scam_predictions (
                user_id, caller_phone, caller_email, message_content,
                risk_score, risk_level, scam_type, confidence,
                factors, recommendation, created_at
            ) VALUES (
                :uid, :phone, :email, :msg,
                :risk, :level, :type, :conf,
                :factors::jsonb, :rec, NOW()
            ) RETURNING id
        """)
        
        result = await db.execute(save_query, {
            "uid": user_id,
            "phone": payload.caller_phone,
            "email": payload.caller_email,
            "msg": payload.message_content,
            "risk": total_risk,
            "level": risk_level,
            "type": scam_type,
            "conf": confidence,
            "factors": str(all_factors),
            "rec": recommendation
        })
        
        prediction_id = result.fetchone()[0]
        
        return {
            "ok": True,
            "prediction_id": prediction_id,
            "risk_score": round(total_risk, 3),
            "risk_level": risk_level,
            "scam_type": scam_type,
            "confidence": round(confidence, 2),
            "factors_detected": all_factors,
            "factor_count": factor_count,
            "recommendation": recommendation,
            "breakdown": {
                "phone_risk": round(phone_analysis["risk_score"], 2),
                "message_risk": round(message_analysis["risk_score"], 2),
                "call_pattern_risk": round(call_analysis["risk_score"], 2),
                "amount_risk": round(amount_analysis["risk_score"], 2)
            }
        }
    
    except Exception as e:
        raise HTTPException(500, f"Prediction error: {str(e)}")


@router.get("/my-predictions")
async def get_my_predictions(
    request: Request,
    current_user: dict = Depends(get_current_user),
    limit: int = 50
):
    """
    Get user's scam prediction history
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        predictions_query = text("""
            SELECT 
                id, caller_phone, risk_score, risk_level,
                scam_type, confidence, created_at
            FROM scam_predictions
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT :lim
        """)
        
        predictions = (await db.execute(predictions_query, {"uid": user_id, "lim": limit})).fetchall()
        
        return {
            "ok": True,
            "total": len(predictions),
            "predictions": [
                {
                    "prediction_id": p[0],
                    "caller_phone": p[1],
                    "risk_score": float(p[2]),
                    "risk_level": p[3],
                    "scam_type": p[4],
                    "confidence": float(p[5]),
                    "predicted_at": str(p[6])
                }
                for p in predictions
            ]
        }
    
    except Exception as e:
        raise HTTPException(500, f"History fetch error: {str(e)}")


@router.get("/stats")
async def get_prediction_stats(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Get user's scam prediction statistics
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        stats_query = text("""
            SELECT 
                COUNT(*) as total_predictions,
                COUNT(*) FILTER (WHERE risk_level = 'critical') as critical_count,
                COUNT(*) FILTER (WHERE risk_level = 'high') as high_count,
                COUNT(*) FILTER (WHERE risk_level = 'medium') as medium_count,
                COUNT(*) FILTER (WHERE risk_level = 'low') as low_count,
                AVG(risk_score) as avg_risk_score
            FROM scam_predictions
            WHERE user_id = :uid
        """)
        
        stats = (await db.execute(stats_query, {"uid": user_id})).fetchone()
        
        return {
            "ok": True,
            "stats": {
                "total_predictions": stats[0] or 0,
                "critical_threats": stats[1] or 0,
                "high_threats": stats[2] or 0,
                "medium_threats": stats[3] or 0,
                "low_threats": stats[4] or 0,
                "average_risk_score": round(float(stats[5]), 3) if stats[5] else 0.0
            }
        }
    
    except Exception as e:
        raise HTTPException(500, f"Stats error: {str(e)}")

