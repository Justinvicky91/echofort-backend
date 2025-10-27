"""
Whisper API Integration for Call Analysis
Compatible with OpenAI SDK v1.12.0+
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import uuid
import json

router = APIRouter(prefix="/api/calls", tags=["call-analysis"])


# Lazy import OpenAI to prevent startup crashes
def get_openai_client():
    """Get OpenAI client with lazy import"""
    try:
        from openai import OpenAI
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="OpenAI package not available. Please contact support."
        )


# Request Models
class CallAnalysisRequest(BaseModel):
    audio_url: str
    caller_id: Optional[str] = None
    duration: Optional[int] = None
    language: str = "en"
    metadata: Optional[Dict[str, Any]] = None


class QuickScamCheck(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None


# Analysis Functions
def analyze_text_for_scam(client, text: str) -> Dict[str, Any]:
    """
    Analyze text for scam indicators using GPT-4
    """
    prompt = f"""Analyze this phone call transcription for scam indicators.
Focus on Indian scam patterns: digital arrest, fake police, investment schemes, loan harassment.

Call Transcription:
{text}

Provide analysis in JSON format:
{{
    "is_scam": true/false,
    "scam_type": "digital_arrest|investment|loan_harassment|prize_lottery|tech_support|romance|job_offer|bank_fraud|none",
    "threat_level": 0-10,
    "confidence": 0-100,
    "caller_intent": "brief description",
    "victim_state": "confused|scared|convinced|suspicious|calm",
    "urgency": "low|medium|high|critical",
    "red_flags": ["list of warning signs"],
    "recommendations": ["list of actions to take"],
    "summary": "brief summary"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use mini for cost efficiency
            messages=[
                {"role": "system", "content": "You are an expert scam detection AI."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "is_scam": False,
            "error": str(e),
            "scam_type": "none",
            "threat_level": 0,
            "confidence": 0
        }


def transcribe_audio(client, audio_url: str, language: str = "en") -> str:
    """
    Transcribe audio using Whisper API
    Note: This is a placeholder - actual implementation needs file download
    """
    # TODO: Download audio file from URL
    # TODO: Upload to Whisper API
    # For now, return placeholder
    return "[Transcription will be implemented when audio file access is configured]"


# API Endpoints
@router.post("/analyze-text")
async def analyze_call_text(request: QuickScamCheck):
    """
    Quick scam analysis from text (for testing without audio)
    """
    try:
        client = get_openai_client()
        analysis = analyze_text_for_scam(client, request.text)
        
        # Generate alert message
        alert = None
        if analysis.get("is_scam") and analysis.get("threat_level", 0) >= 7:
            threat = analysis.get("threat_level", 0)
            scam_type = analysis.get("scam_type", "unknown").replace("_", " ").title()
            alert = f"🚨 HIGH THREAT DETECTED\n\nScam Type: {scam_type}\nThreat Level: {threat}/10\n\nRecommended Actions:\n"
            for rec in analysis.get("recommendations", [])[:3]:
                alert += f"• {rec}\n"
        
        return {
            "call_id": f"CALL-{uuid.uuid4().hex[:12].upper()}",
            "status": "completed",
            "analysis": analysis,
            "alert_message": alert,
            "analyzed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-check")
async def quick_scam_check(request: QuickScamCheck):
    """
    Real-time scam detection during call (for mobile app)
    Returns instant threat assessment
    """
    try:
        client = get_openai_client()
        analysis = analyze_text_for_scam(client, request.text)
        
        return {
            "is_scam": analysis.get("is_scam", False),
            "scam_type": analysis.get("scam_type"),
            "threat_level": analysis.get("threat_level", 0),
            "confidence": analysis.get("confidence", 0),
            "urgency": analysis.get("urgency", "low"),
            "recommendations": analysis.get("recommendations", [])[:3]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test")
async def test_whisper_api():
    """
    Test endpoint to verify Whisper API is configured
    """
    try:
        client = get_openai_client()
        
        # Test with sample scam text
        test_text = """
        Hello sir, this is Officer Kumar from Delhi Police Cyber Crime Department.
        Your Aadhaar card has been used for illegal activities. 
        We have issued an arrest warrant in your name.
        You must transfer Rs 50,000 immediately to avoid arrest.
        Do not disconnect this call or we will send police to your home.
        """
        
        analysis = analyze_text_for_scam(client, test_text)
        
        return {
            "status": "success",
            "message": "Whisper API is configured and working",
            "test_analysis": analysis,
            "openai_configured": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "openai_configured": False
        }


@router.get("/stats")
async def get_analysis_stats():
    """
    Get call analysis statistics
    TODO: Connect to database
    """
    return {
        "total_calls_analyzed": 0,
        "scams_detected": 0,
        "scam_rate": 0.0,
        "average_threat_level": 0.0,
        "top_scam_types": []
    }


# Placeholder endpoints for future implementation
@router.post("/upload")
async def upload_call_recording(request: CallAnalysisRequest):
    """
    Upload call recording for analysis
    TODO: Implement S3 upload and Whisper transcription
    """
    return {
        "call_id": f"CALL-{uuid.uuid4().hex[:12].upper()}",
        "status": "pending",
        "message": "Audio upload endpoint will be implemented when S3 is configured",
        "created_at": datetime.now().isoformat()
    }


@router.get("/{call_id}")
async def get_call_analysis(call_id: str):
    """
    Get analysis results
    TODO: Connect to database
    """
    return {
        "call_id": call_id,
        "status": "not_found",
        "message": "Database integration pending"
    }

