"""
Legal Documents API
Provides Terms of Service and Privacy Policy endpoints
Required for DPDP Act 2023 compliance
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
from datetime import datetime

router = APIRouter()

# Path to legal text files
LEGAL_TEXTS_DIR = Path(__file__).resolve().parents[1] / "legal_texts"

def load_legal_document(filename: str) -> str:
    """
    Load legal document from markdown file
    This approach avoids encoding issues with hardcoded strings
    """
    try:
        file_path = LEGAL_TEXTS_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Legal document not found: {filename}")
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(500, f"Failed to load legal document: {str(e)}")


@router.get("/legal/terms")
async def get_terms_of_service():
    """
    Get Terms of Service
    Public endpoint - no authentication required
    """
    content = load_legal_document("terms.md")
    return JSONResponse(
        content={
            "ok": True,
            "document": "terms_of_service",
            "version": "2.0",
            "last_updated": "2025-11-23",
            "language": "en-IN",
            "content": content,
            "content_type": "markdown",
        }
    )


@router.get("/legal/privacy")
async def get_privacy_policy():
    """
    Get Privacy Policy
    Public endpoint - no authentication required
    """
    content = load_legal_document("privacy.md")
    return JSONResponse(
        content={
            "ok": True,
            "document": "privacy_policy",
            "version": "2.0",
            "last_updated": "2025-11-23",
            "language": "en-IN",
            "content": content,
            "content_type": "markdown",
        }
    )


@router.get("/legal/refund")
async def get_refund_policy():
    """
    Get Refund Policy
    Public endpoint - no authentication required
    """
    refund_policy = """# EchoFort Refund Policy

**Last Updated:** November 15, 2025

## 1. 24-Hour Money-Back Guarantee

- Full refund if requested within 24 hours of first subscription
- No questions asked
- Refund processed within 5-7 business days

## 2. Subscription Cancellation

- Cancel anytime from app settings
- No refund for remaining subscription period
- Access continues until end of billing cycle

## 3. Service Issues

- Refund if service is unavailable for 48+ hours
- Partial refund for major feature failures
- Contact support@echofort.ai for claims

## 4. Refund Process

- Request via app or email refund@echofort.ai
- Provide order ID and reason
- Refund to original payment method
- Processing time: 5-7 business days

## 5. Non-Refundable

- Subscription renewals (after 24 hours)
- Promotional discounts
- Third-party service fees

## 6. Contact

For refund requests:
- Email: refund@echofort.ai
- Phone: +91-XXXXXXXXXX

---

(c) 2025 EchoFort. All rights reserved.
"""
    
    return JSONResponse(
        content={
            "ok": True,
            "document": "refund_policy",
            "version": "1.0",
            "last_updated": "2025-11-15",
            "language": "en-IN",
            "content": refund_policy,
            "content_type": "markdown",
        }
    )
