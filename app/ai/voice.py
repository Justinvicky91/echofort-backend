# app/ai/voice.py - Enhanced Voice AI with OpenAI Whisper
"""
Voice AI - Speech-to-Text and Scam Detection
Uses OpenAI Whisper for transcription + rule-based scam detection
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import Optional
import io
import os
import tempfile
from openai import OpenAI

router = APIRouter(prefix="/api/ai/voice", tags=["Voice AI"])

# Lazy OpenAI client initialization
_client = None

def get_openai_client():
    """Lazy load OpenAI client"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(500, "OpenAI API key not configured")
        _client = OpenAI(api_key=api_key)
    return _client

# Scam keywords database
SCAM_KEYWORDS = {
    "digital_arrest": [
        "arrest warrant", "police", "cbi", "court", "money laundering",
        "drug trafficking", "customs", "immediate payment", "bank account freeze",
        "legal action", "suspend your account", "verify your identity",
        "pay fine", "arrest within 24 hours"
    ],
    "investment_fraud": [
        "guaranteed returns", "risk-free investment", "double your money",
        "limited time offer", "exclusive opportunity", "high returns",
        "quick profit", "insider information", "stock tip"
    ],
    "impersonation": [
        "bank representative", "tax officer", "government official",
        "courier company", "electricity board", "gas agency",
        "update kyc", "verify account", "confirm details"
    ],
    "lottery_scam": [
        "you won", "lottery", "prize money", "claim your reward",
        "lucky draw", "processing fee", "tax payment", "claim now"
    ],
    "tech_support": [
        "virus detected", "computer infected", "security alert",
        "microsoft support", "apple support", "google support",
        "remote access", "teamviewer", "anydesk"
    ]
}

# Threat indicators
THREAT_INDICATORS = [
    "immediately", "urgent", "within 24 hours", "last chance",
    "don't tell anyone", "keep this confidential", "secret",
    "transfer money", "send payment", "pay now", "wire transfer",
    "bitcoin", "cryptocurrency", "gift card", "itunes card"
]


def detect_scam_type(transcript: str) -> tuple[str, float, list]:
    """
    Detect scam type from transcript using keyword matching
    Returns: (scam_type, confidence_score, detected_keywords)
    """
    transcript_lower = transcript.lower()
    
    detected_scams = {}
    all_detected_keywords = []
    
    # Check each scam category
    for scam_type, keywords in SCAM_KEYWORDS.items():
        matches = [kw for kw in keywords if kw in transcript_lower]
        if matches:
            detected_scams[scam_type] = len(matches)
            all_detected_keywords.extend(matches)
    
    # Check threat indicators
    threat_matches = [ti for ti in THREAT_INDICATORS if ti in transcript_lower]
    all_detected_keywords.extend(threat_matches)
    
    if not detected_scams:
        return "none", 0.0, []
    
    # Get scam type with most matches
    primary_scam = max(detected_scams, key=detected_scams.get)
    keyword_count = detected_scams[primary_scam]
    
    # Calculate confidence score
    confidence = min(0.95, (keyword_count * 0.15) + (len(threat_matches) * 0.10))
    
    return primary_scam, confidence, all_detected_keywords


def calculate_trust_factor(transcript: str, scam_type: str, confidence: float) -> int:
    """
    Calculate trust factor (0-10) based on scam detection
    0 = Highly suspicious, 10 = Trustworthy
    """
    if scam_type == "none":
        return 8  # Likely legitimate
    
    # Inverse of confidence (high scam confidence = low trust)
    trust = int((1.0 - confidence) * 10)
    
    return max(0, min(10, trust))


@router.post("/analyze")
async def analyze_voice(file: UploadFile = File(...)):
    """
    Analyze voice recording for scam detection
    1. Transcribe using OpenAI Whisper
    2. Detect scam patterns using keyword matching
    3. Calculate trust factor
    """
    try:
        # Read audio file
        audio_data = await file.read()
        
        # Save to temporary file (Whisper requires file path)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name
        
        try:
            # Transcribe using OpenAI Whisper
            with open(temp_audio_path, "rb") as audio_file:
                transcript_response = get_openai_client().audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"  # Can be auto-detected or set to "hi" for Hindi
                )
            
            transcript = transcript_response.text
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
        
        # Detect scam patterns
        scam_type, confidence, keywords = detect_scam_type(transcript)
        
        # Calculate trust factor
        trust_factor = calculate_trust_factor(transcript, scam_type, confidence)
        
        # Determine if scam
        is_scam = confidence >= 0.5
        
        # Determine action
        if is_scam and confidence >= 0.7:
            action = "block"
            recommendation = "🚨 HIGH RISK - Block this call immediately!"
        elif is_scam and confidence >= 0.5:
            action = "warn"
            recommendation = "⚠️ SUSPICIOUS - Proceed with caution"
        else:
            action = "monitor"
            recommendation = "✓ Appears safe, but stay alert"
        
        return {
            "ok": True,
            "transcript": transcript,
            "scam_detected": is_scam,
            "scam_type": scam_type if is_scam else None,
            "confidence_score": round(confidence, 2),
            "trust_factor": trust_factor,
            "keywords_detected": keywords,
            "action": action,
            "recommendation": recommendation,
            "analysis": {
                "total_keywords": len(keywords),
                "transcript_length": len(transcript),
                "language": "english",  # Can be enhanced to detect language
                "processing_method": "OpenAI Whisper + Rule-based Detection"
            }
        }
    
    except Exception as e:
        # Fallback to basic analysis if Whisper fails
        print(f"Whisper transcription error: {e}")
        
        return {
            "ok": False,
            "error": "Transcription failed",
            "message": "Could not transcribe audio. Please ensure audio quality is good.",
            "fallback_analysis": {
                "trust_factor": 5,  # Neutral
                "recommendation": "Manual review recommended"
            }
        }


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), language: Optional[str] = "en"):
    """
    Transcribe audio to text using OpenAI Whisper
    Supports multiple languages (en, hi, etc.)
    """
    try:
        audio_data = await file.read()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name
        
        try:
            # Transcribe using OpenAI Whisper
            with open(temp_audio_path, "rb") as audio_file:
                transcript_response = get_openai_client().audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language if language else None
                )
            
            transcript = transcript_response.text
            
        finally:
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
        
        return {
            "ok": True,
            "transcript": transcript,
            "language": language,
            "word_count": len(transcript.split()),
            "character_count": len(transcript)
        }
    
    except Exception as e:
        raise HTTPException(500, f"Transcription error: {str(e)}")


@router.post("/quick-scan")
async def quick_voice_scan(file: UploadFile = File(...)):
    """
    Quick voice scan without full transcription
    Uses basic audio analysis for fast results
    """
    try:
        import numpy as np
        from scipy.io import wavfile
        
        audio_data = await file.read()
        
        # Try to load as WAV
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                temp_audio.write(audio_data)
                temp_audio_path = temp_audio.name
            
            rate, data = wavfile.read(temp_audio_path)
            
            # Convert to mono if stereo
            if len(data.shape) > 1:
                data = data.mean(axis=1)
            
            # Normalize
            data = data.astype(float) / np.max(np.abs(data))
            
            # Calculate basic metrics
            rms = float(np.sqrt(np.mean(data ** 2)))
            zcr = float(((data[:-1] * data[1:]) < 0).mean())
            
            # Heuristic scoring
            score = 10.0 - (zcr * 10.0) + (rms * 8.0)
            trust_factor = int(np.clip(score, 0, 10))
            
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            
            return {
                "ok": True,
                "trust_factor": trust_factor,
                "analysis_type": "quick_scan",
                "recommendation": "Use full analysis for detailed results",
                "metrics": {
                    "rms_energy": round(rms, 3),
                    "zero_crossing_rate": round(zcr, 3)
                }
            }
        
        except:
            # If WAV fails, return neutral score
            return {
                "ok": True,
                "trust_factor": 5,
                "analysis_type": "quick_scan",
                "recommendation": "Use full analysis with transcription for accurate results"
            }
    
    except Exception as e:
        raise HTTPException(500, f"Quick scan error: {str(e)}")

