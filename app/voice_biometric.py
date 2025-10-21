# app/voice_biometric.py - Voice Biometric System
"""
Voice Biometric - Voice Fingerprinting for Caller Identification
Creates unique voice signatures to identify known scammers
"""

from fastapi import APIRouter, Request, HTTPException, Depends, File, UploadFile
from sqlalchemy import text
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from .utils import get_current_user
import hashlib
import numpy as np

router = APIRouter(prefix="/api/voice-biometric", tags=["Voice Biometric"])


class VoiceMatch(BaseModel):
    caller_phone: str
    match_score: float
    is_known_scammer: bool
    previous_reports: int


def extract_voice_features(audio_data: bytes) -> dict:
    """
    Extract voice features for biometric matching
    In production, use advanced audio processing libraries
    """
    try:
        # Simple feature extraction (placeholder)
        # In production, use librosa, pyAudioAnalysis, or cloud services
        
        # Create a simple hash-based fingerprint
        voice_hash = hashlib.sha256(audio_data).hexdigest()[:32]
        
        # Extract basic features (mock)
        features = {
            "voice_hash": voice_hash,
            "sample_length": len(audio_data),
            "pitch_estimate": 150.0,  # Mock pitch in Hz
            "energy_level": 0.75,  # Mock energy
            "spectral_centroid": 2000.0  # Mock spectral centroid
        }
        
        return features
    
    except Exception as e:
        print(f"Feature extraction error: {e}")
        return None


def calculate_voice_similarity(features1: dict, features2: dict) -> float:
    """
    Calculate similarity score between two voice samples
    Returns: similarity score (0.0 to 1.0)
    """
    try:
        # Simple similarity calculation (placeholder)
        # In production, use advanced voice comparison algorithms
        
        # Compare voice hashes
        if features1["voice_hash"] == features2["voice_hash"]:
            return 1.0
        
        # Compare features
        pitch_diff = abs(features1["pitch_estimate"] - features2["pitch_estimate"])
        energy_diff = abs(features1["energy_level"] - features2["energy_level"])
        spectral_diff = abs(features1["spectral_centroid"] - features2["spectral_centroid"])
        
        # Normalize and combine
        pitch_similarity = max(0, 1 - (pitch_diff / 200))
        energy_similarity = max(0, 1 - energy_diff)
        spectral_similarity = max(0, 1 - (spectral_diff / 3000))
        
        # Weighted average
        similarity = (pitch_similarity * 0.4) + (energy_similarity * 0.3) + (spectral_similarity * 0.3)
        
        return round(similarity, 3)
    
    except Exception as e:
        print(f"Similarity calculation error: {e}")
        return 0.0


@router.post("/register-voice")
async def register_voice(
    request: Request,
    file: UploadFile = File(...),
    caller_phone: str = None,
    caller_name: str = None,
    is_scammer: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Register a voice sample for biometric matching
    Used to identify known scammers or trusted contacts
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Read audio file
        audio_data = await file.read()
        
        # Extract voice features
        features = extract_voice_features(audio_data)
        
        if not features:
            raise HTTPException(500, "Failed to extract voice features")
        
        # Save voice biometric
        insert_query = text("""
            INSERT INTO voice_biometrics (
                user_id, caller_phone, caller_name, voice_hash,
                voice_features, is_scammer, sample_count, created_at, updated_at
            ) VALUES (
                :uid, :phone, :name, :hash,
                :features::jsonb, :scammer, 1, NOW(), NOW()
            )
            ON CONFLICT (voice_hash) DO UPDATE SET
                sample_count = voice_biometrics.sample_count + 1,
                updated_at = NOW()
            RETURNING id
        """)
        
        result = await db.execute(insert_query, {
            "uid": user_id,
            "phone": caller_phone,
            "name": caller_name,
            "hash": features["voice_hash"],
            "features": str(features),
            "scammer": is_scammer
        })
        
        biometric_id = result.fetchone()[0]
        
        return {
            "ok": True,
            "biometric_id": biometric_id,
            "voice_hash": features["voice_hash"],
            "message": "Voice registered successfully",
            "caller_phone": caller_phone,
            "is_scammer": is_scammer
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Voice registration error: {str(e)}")


@router.post("/match-voice")
async def match_voice(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Match incoming voice against database of known voices
    Returns: list of matches with similarity scores
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Read audio file
        audio_data = await file.read()
        
        # Extract voice features
        features = extract_voice_features(audio_data)
        
        if not features:
            raise HTTPException(500, "Failed to extract voice features")
        
        # Get all registered voices
        voices_query = text("""
            SELECT 
                id, caller_phone, caller_name, voice_hash,
                voice_features, is_scammer, sample_count
            FROM voice_biometrics
            ORDER BY created_at DESC
            LIMIT 1000
        """)
        
        voices = (await db.execute(voices_query)).fetchall()
        
        # Find matches
        matches = []
        
        for voice in voices:
            # Parse stored features
            try:
                stored_features = eval(voice[4])  # In production, use json.loads
            except:
                continue
            
            # Calculate similarity
            similarity = calculate_voice_similarity(features, stored_features)
            
            # Consider it a match if similarity > 0.7
            if similarity >= 0.7:
                matches.append({
                    "biometric_id": voice[0],
                    "caller_phone": voice[1],
                    "caller_name": voice[2],
                    "match_score": similarity,
                    "is_scammer": voice[5],
                    "confidence": "high" if similarity >= 0.9 else "medium" if similarity >= 0.8 else "low",
                    "sample_count": voice[6]
                })
        
        # Sort by match score
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        
        # Determine if scammer
        is_scammer = any(m["is_scammer"] for m in matches if m["match_score"] >= 0.8)
        
        return {
            "ok": True,
            "total_matches": len(matches),
            "matches": matches[:10],  # Top 10 matches
            "is_known_scammer": is_scammer,
            "recommendation": "🚨 BLOCK - Known scammer detected!" if is_scammer else "✓ No scammer match found",
            "voice_hash": features["voice_hash"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Voice matching error: {str(e)}")


@router.get("/my-voice-database")
async def get_voice_database(
    request: Request,
    current_user: dict = Depends(get_current_user),
    limit: int = 50
):
    """
    Get user's registered voice biometrics
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        voices_query = text("""
            SELECT 
                id, caller_phone, caller_name, is_scammer,
                sample_count, created_at, updated_at
            FROM voice_biometrics
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT :lim
        """)
        
        voices = (await db.execute(voices_query, {"uid": user_id, "lim": limit})).fetchall()
        
        return {
            "ok": True,
            "total": len(voices),
            "voices": [
                {
                    "biometric_id": v[0],
                    "caller_phone": v[1],
                    "caller_name": v[2],
                    "is_scammer": v[3],
                    "sample_count": v[4],
                    "registered_at": str(v[5]),
                    "last_updated": str(v[6])
                }
                for v in voices
            ]
        }
    
    except Exception as e:
        raise HTTPException(500, f"Database fetch error: {str(e)}")


@router.delete("/delete-voice/{biometric_id}")
async def delete_voice(
    request: Request,
    biometric_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a voice biometric entry
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Verify ownership
        verify_query = text("""
            SELECT user_id FROM voice_biometrics WHERE id = :bid
        """)
        
        owner = (await db.execute(verify_query, {"bid": biometric_id})).fetchone()
        
        if not owner:
            raise HTTPException(404, "Voice biometric not found")
        
        if owner[0] != user_id:
            raise HTTPException(403, "Unauthorized")
        
        # Delete
        await db.execute(text("""
            DELETE FROM voice_biometrics WHERE id = :bid
        """), {"bid": biometric_id})
        
        return {
            "ok": True,
            "message": "Voice biometric deleted"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Deletion error: {str(e)}")


@router.get("/scammer-database")
async def get_scammer_voice_database(request: Request, limit: int = 100):
    """
    Get global database of known scammer voices
    """
    try:
        db = request.app.state.db
        
        scammers_query = text("""
            SELECT 
                caller_phone, caller_name, sample_count,
                COUNT(DISTINCT user_id) as reported_by_count,
                MAX(created_at) as last_reported
            FROM voice_biometrics
            WHERE is_scammer = TRUE
            GROUP BY caller_phone, caller_name, sample_count
            ORDER BY reported_by_count DESC, last_reported DESC
            LIMIT :lim
        """)
        
        scammers = (await db.execute(scammers_query, {"lim": limit})).fetchall()
        
        return {
            "ok": True,
            "total_scammers": len(scammers),
            "scammers": [
                {
                    "caller_phone": s[0],
                    "caller_name": s[1],
                    "sample_count": s[2],
                    "reported_by": s[3],
                    "last_reported": str(s[4])
                }
                for s in scammers
            ],
            "message": "Global scammer voice database"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

