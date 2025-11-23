"""
Block 5: Minimal Consent Integration
Provides endpoints to log user consent for testing
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class ConsentRequest(BaseModel):
    user_id: str
    consent_type: str  # signup, login_upgrade
    consent_channel: str  # mobile, web
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@router.post("/api/consent/log")
async def log_consent(request: ConsentRequest, req: Request):
    """
    Log user consent to Terms v2.0 and Privacy v2.0
    
    This endpoint should be called:
    - On new user signup (consent_type='signup')
    - When existing user accepts updated terms (consent_type='login_upgrade')
    """
    from .consent_logger import log_user_consent, CURRENT_TERMS_VERSION, CURRENT_PRIVACY_VERSION
    
    # Get IP and user agent from request if not provided
    ip_address = request.ip_address or req.client.host
    user_agent = request.user_agent or req.headers.get("user-agent", "unknown")
    
    try:
        consent_id = await log_user_consent(
            db=None,  # Will use DATABASE_URL from env
            user_id=request.user_id,
            terms_version=CURRENT_TERMS_VERSION,
            privacy_version=CURRENT_PRIVACY_VERSION,
            consent_type=request.consent_type,
            consent_channel=request.consent_channel,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return {
            "ok": True,
            "consent_id": consent_id,
            "terms_version": CURRENT_TERMS_VERSION,
            "privacy_version": CURRENT_PRIVACY_VERSION,
            "message": "Consent logged successfully"
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


@router.get("/api/consent/check")
async def check_consent(user_id: str):
    """
    Check if user has consented to current Terms & Privacy versions
    """
    from .consent_logger import get_latest_consent, CURRENT_TERMS_VERSION, CURRENT_PRIVACY_VERSION
    
    try:
        latest = await get_latest_consent(db=None, user_id=user_id)
        
        if not latest:
            return {
                "ok": True,
                "has_consented": False,
                "needs_consent": True,
                "current_terms_version": CURRENT_TERMS_VERSION,
                "current_privacy_version": CURRENT_PRIVACY_VERSION
            }
        
        needs_consent = (
            latest["terms_version"] != CURRENT_TERMS_VERSION or
            latest["privacy_version"] != CURRENT_PRIVACY_VERSION
        )
        
        return {
            "ok": True,
            "has_consented": True,
            "needs_consent": needs_consent,
            "latest_consent": latest,
            "current_terms_version": CURRENT_TERMS_VERSION,
            "current_privacy_version": CURRENT_PRIVACY_VERSION
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }
