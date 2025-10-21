# app/ai/image.py - Enhanced Image AI with OCR and Scam Detection
"""
Image AI - Screenshot Analysis and Document Verification
Uses PIL + OCR for text extraction + rule-based scam detection
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
from PIL import Image
import io
import numpy as np
import re

router = APIRouter(prefix="/api/ai/image", tags=["Image AI"])

# Scam indicators in images
SCAM_TEXT_PATTERNS = [
    r"congratulations.*won",
    r"claim.*prize",
    r"urgent.*action",
    r"verify.*account",
    r"suspended.*account",
    r"click.*link",
    r"limited.*time.*offer",
    r"guaranteed.*returns",
    r"double.*money",
    r"risk.*free",
    r"act.*now",
    r"expire.*\d+.*hours",
    r"lottery.*winner",
    r"tax.*refund",
    r"inheritance.*claim"
]

# Suspicious domains
SUSPICIOUS_DOMAINS = [
    "bit.ly", "tinyurl.com", "goo.gl", "ow.ly",
    "t.co", "is.gd", "buff.ly", "adf.ly"
]

# Payment-related keywords (high risk in scam context)
PAYMENT_KEYWORDS = [
    "bank account", "credit card", "debit card", "cvv", "pin",
    "otp", "password", "upi", "paytm", "phonepe", "googlepay",
    "net banking", "card number", "expiry date", "account number",
    "ifsc code", "aadhaar", "pan card"
]


def extract_text_from_image(image: Image.Image) -> str:
    """
    Extract text from image using basic OCR
    For production, use pytesseract or cloud OCR services
    """
    try:
        # Try to use pytesseract if available
        import pytesseract
        text = pytesseract.image_to_string(image)
        return text
    except ImportError:
        # Fallback: Return empty string if pytesseract not available
        # In production, you would use a cloud OCR service here
        return ""
    except Exception as e:
        print(f"OCR error: {e}")
        return ""


def analyze_image_content(image: Image.Image) -> dict:
    """
    Analyze image for scam indicators
    Returns: {risk_score, flags, detected_patterns}
    """
    # Convert to numpy array
    img_array = np.asarray(image.convert("RGB"))
    
    # Basic image analysis
    height, width = img_array.shape[:2]
    
    # Calculate color statistics
    mean_color = img_array.mean(axis=(0, 1))
    std_color = img_array.std(axis=(0, 1))
    
    # Check for suspicious patterns
    flags = []
    risk_score = 0.0
    
    # Low variance might indicate fake/generated image
    if std_color.mean() < 15:
        flags.append("low_variance")
        risk_score += 0.2
    
    # Very bright or very dark images
    if mean_color.mean() > 240:
        flags.append("very_bright")
        risk_score += 0.1
    elif mean_color.mean() < 15:
        flags.append("very_dark")
        risk_score += 0.1
    
    # Small image size (common in phishing)
    if width < 200 or height < 200:
        flags.append("small_size")
        risk_score += 0.15
    
    # Extract text using OCR
    extracted_text = extract_text_from_image(image)
    
    detected_patterns = []
    
    if extracted_text:
        text_lower = extracted_text.lower()
        
        # Check for scam text patterns
        for pattern in SCAM_TEXT_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                detected_patterns.append(pattern)
                risk_score += 0.15
        
        # Check for suspicious domains
        for domain in SUSPICIOUS_DOMAINS:
            if domain in text_lower:
                flags.append(f"suspicious_domain_{domain}")
                risk_score += 0.2
        
        # Check for payment keywords
        payment_count = sum(1 for kw in PAYMENT_KEYWORDS if kw in text_lower)
        if payment_count >= 2:
            flags.append("multiple_payment_keywords")
            risk_score += 0.25
    
    # Cap risk score at 1.0
    risk_score = min(1.0, risk_score)
    
    return {
        "risk_score": risk_score,
        "flags": flags,
        "detected_patterns": detected_patterns,
        "extracted_text": extracted_text,
        "image_stats": {
            "width": width,
            "height": height,
            "mean_brightness": float(mean_color.mean()),
            "color_variance": float(std_color.mean())
        }
    }


@router.post("/scan")
async def scan_image(file: UploadFile = File(...)):
    """
    Scan image for scam indicators
    Analyzes screenshots, documents, and suspicious images
    """
    try:
        # Read image
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Analyze image
        analysis = analyze_image_content(image)
        
        # Determine if scam
        is_suspicious = analysis["risk_score"] >= 0.5
        
        # Generate recommendation
        if analysis["risk_score"] >= 0.7:
            recommendation = "🚨 HIGH RISK - This appears to be a scam. Do not click links or share information."
        elif analysis["risk_score"] >= 0.5:
            recommendation = "⚠️ SUSPICIOUS - Exercise caution. Verify authenticity before proceeding."
        elif analysis["risk_score"] >= 0.3:
            recommendation = "⚡ MODERATE RISK - Some suspicious elements detected. Be careful."
        else:
            recommendation = "✓ Appears safe, but always verify before sharing personal information."
        
        return {
            "ok": True,
            "is_suspicious": is_suspicious,
            "risk_score": round(analysis["risk_score"], 2),
            "flags": analysis["flags"],
            "detected_patterns": analysis["detected_patterns"],
            "extracted_text": analysis["extracted_text"][:500] if analysis["extracted_text"] else None,  # Limit text length
            "recommendation": recommendation,
            "image_stats": analysis["image_stats"],
            "analysis_method": "PIL + OCR + Rule-based Detection"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Image scan error: {str(e)}")


@router.post("/verify-document")
async def verify_document(file: UploadFile = File(...)):
    """
    Verify government ID documents
    Checks for tampering, fake documents, etc.
    """
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Extract text
        extracted_text = extract_text_from_image(image)
        
        # Check for common ID keywords
        id_keywords = ["aadhaar", "pan", "passport", "driving license", "voter id"]
        detected_id_type = None
        
        if extracted_text:
            text_lower = extracted_text.lower()
            for id_type in id_keywords:
                if id_type in text_lower:
                    detected_id_type = id_type
                    break
        
        # Basic image quality checks
        img_array = np.asarray(image.convert("RGB"))
        height, width = img_array.shape[:2]
        
        quality_score = 1.0
        issues = []
        
        # Check resolution
        if width < 600 or height < 400:
            quality_score -= 0.3
            issues.append("low_resolution")
        
        # Check for excessive compression artifacts
        std_color = img_array.std(axis=(0, 1))
        if std_color.mean() < 10:
            quality_score -= 0.2
            issues.append("possible_compression_artifacts")
        
        # Check for tampering indicators (very basic)
        # In production, use specialized tampering detection algorithms
        edges = np.abs(np.diff(img_array, axis=0)).mean()
        if edges < 5:
            quality_score -= 0.2
            issues.append("suspicious_uniformity")
        
        quality_score = max(0.0, quality_score)
        
        is_valid = quality_score >= 0.6 and detected_id_type is not None
        
        return {
            "ok": True,
            "is_valid": is_valid,
            "detected_id_type": detected_id_type,
            "quality_score": round(quality_score, 2),
            "issues": issues,
            "extracted_text": extracted_text[:300] if extracted_text else None,
            "recommendation": "Document appears valid" if is_valid else "Manual verification required",
            "note": "This is a basic verification. Manual review is recommended for KYC."
        }
    
    except Exception as e:
        raise HTTPException(500, f"Document verification error: {str(e)}")


@router.post("/detect-qr")
async def detect_qr_code(file: UploadFile = File(...)):
    """
    Detect and analyze QR codes in images
    Warns about suspicious payment QR codes
    """
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Try to decode QR code
        try:
            from pyzbar.pyzbar import decode
            decoded_objects = decode(image)
            
            if not decoded_objects:
                return {
                    "ok": True,
                    "qr_detected": False,
                    "message": "No QR code found in image"
                }
            
            qr_data = decoded_objects[0].data.decode("utf-8")
            
            # Analyze QR code content
            is_payment_qr = any(keyword in qr_data.lower() for keyword in ["upi://", "paytm", "phonepe", "googlepay"])
            is_url = qr_data.startswith("http://") or qr_data.startswith("https://")
            
            risk_score = 0.0
            warnings = []
            
            if is_payment_qr:
                warnings.append("This is a payment QR code. Verify recipient before paying.")
                risk_score += 0.4
            
            if is_url:
                # Check for suspicious domains
                for domain in SUSPICIOUS_DOMAINS:
                    if domain in qr_data:
                        warnings.append(f"Suspicious URL shortener detected: {domain}")
                        risk_score += 0.5
            
            return {
                "ok": True,
                "qr_detected": True,
                "qr_content": qr_data,
                "is_payment_qr": is_payment_qr,
                "is_url": is_url,
                "risk_score": round(risk_score, 2),
                "warnings": warnings,
                "recommendation": "Verify QR code authenticity before scanning" if risk_score > 0.3 else "QR code appears safe"
            }
        
        except ImportError:
            return {
                "ok": False,
                "error": "QR code detection not available",
                "message": "Install pyzbar library for QR code detection"
            }
    
    except Exception as e:
        raise HTTPException(500, f"QR detection error: {str(e)}")

