"""
Email Phishing Detection API
Detects phishing attempts in emails using ML-based analysis
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import re
from datetime import datetime

router = APIRouter(prefix="/api/email-phishing", tags=["Email Security"])


class EmailAnalysisRequest(BaseModel):
    """Request model for email phishing detection"""
    sender_email: EmailStr
    sender_name: Optional[str] = None
    subject: str
    body: str
    links: Optional[List[str]] = []
    attachments: Optional[List[str]] = []
    user_id: Optional[int] = None


class EmailAnalysisResponse(BaseModel):
    """Response model for email phishing detection"""
    is_phishing: bool
    confidence_score: float  # 0.0 to 1.0
    risk_level: str  # "safe", "suspicious", "dangerous"
    threat_indicators: List[str]
    recommendations: List[str]
    analysis_timestamp: str
    # Block 5: New risk dimensions
    content_category: Optional[str] = "benign"
    violence_or_extremism_risk: Optional[int] = 0
    tags: Optional[List[str]] = []


# Phishing indicators database
PHISHING_KEYWORDS = [
    "urgent", "verify", "suspend", "account", "click here", "confirm",
    "password", "credit card", "social security", "bank account",
    "winner", "prize", "lottery", "inheritance", "tax refund",
    "act now", "limited time", "expires", "suspended", "locked",
    "verify identity", "update payment", "unusual activity"
]

SUSPICIOUS_DOMAINS = [
    "tk", "ml", "ga", "cf", "gq",  # Free TLD domains often used for phishing
    "bit.ly", "tinyurl", "goo.gl"  # URL shorteners (can hide real destination)
]

TRUSTED_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "echofort.ai", "government.in", "nic.in"
]

# Block 5: Harmful extremism / violence keywords (content-based)
EXTREMISM_KEYWORDS = [
    "kill infidel", "death to", "destroy enemy", "holy war",
    "martyr operation", "join fight", "recruit soldier",
    "bomb making", "weapon instruction", "attack plan",
    "hate group", "eliminate group", "praise terror",
    "glory attack", "training camp"
]

# Self-harm keywords
SELF_HARM_KEYWORDS = [
    "how to die", "suicide method", "end my life",
    "kill myself", "self harm", "cutting guide"
]


def analyze_sender(sender_email: str, sender_name: Optional[str]) -> tuple[int, List[str]]:
    """
    Analyze sender email and name for phishing indicators
    Returns: (risk_score, indicators)
    """
    risk_score = 0
    indicators = []
    
    # Check if sender domain is suspicious
    domain = sender_email.split('@')[1].lower()
    
    if any(susp in domain for susp in SUSPICIOUS_DOMAINS):
        risk_score += 30
        indicators.append(f"Suspicious domain: {domain}")
    
    # Check for domain spoofing (e.g., "paypa1.com" instead of "paypal.com")
    common_brands = ["paypal", "amazon", "microsoft", "google", "apple", "netflix"]
    for brand in common_brands:
        if brand in domain and not domain.endswith(f"{brand}.com"):
            risk_score += 40
            indicators.append(f"Possible domain spoofing: {domain} (looks like {brand})")
    
    # Check if sender name doesn't match email
    if sender_name:
        if "@" in sender_name:  # Email in display name is suspicious
            risk_score += 20
            indicators.append("Email address in sender display name")
    
    return risk_score, indicators


def analyze_subject(subject: str) -> tuple[int, List[str]]:
    """
    Analyze email subject for phishing indicators
    Returns: (risk_score, indicators)
    """
    risk_score = 0
    indicators = []
    subject_lower = subject.lower()
    
    # Check for urgency keywords
    urgency_words = ["urgent", "immediate", "act now", "expires", "limited time"]
    for word in urgency_words:
        if word in subject_lower:
            risk_score += 15
            indicators.append(f"Urgency keyword in subject: '{word}'")
            break
    
    # Check for suspicious patterns
    if "re:" in subject_lower and "fwd:" in subject_lower:
        risk_score += 10
        indicators.append("Suspicious reply/forward pattern")
    
    # Check for excessive punctuation
    if subject.count("!") > 2 or subject.count("?") > 2:
        risk_score += 10
        indicators.append("Excessive punctuation in subject")
    
    return risk_score, indicators


def analyze_body(body: str) -> tuple[int, List[str]]:
    """
    Analyze email body for phishing indicators
    Returns: (risk_score, indicators)
    """
    risk_score = 0
    indicators = []
    body_lower = body.lower()
    
    # Count phishing keywords
    keyword_count = sum(1 for keyword in PHISHING_KEYWORDS if keyword in body_lower)
    
    if keyword_count >= 5:
        risk_score += 40
        indicators.append(f"High concentration of phishing keywords ({keyword_count} found)")
    elif keyword_count >= 3:
        risk_score += 25
        indicators.append(f"Multiple phishing keywords detected ({keyword_count} found)")
    
    # Check for requests for sensitive information
    sensitive_requests = ["password", "credit card", "ssn", "social security", "bank account", "pin"]
    for request in sensitive_requests:
        if request in body_lower:
            risk_score += 30
            indicators.append(f"Requests sensitive information: {request}")
            break
    
    # Check for suspicious links
    if "click here" in body_lower or "click this link" in body_lower:
        risk_score += 20
        indicators.append("Suspicious link text ('click here')")
    
    # Check for poor grammar/spelling (simple heuristic)
    if body.count("  ") > 5:  # Multiple double spaces
        risk_score += 10
        indicators.append("Poor formatting detected")
    
    return risk_score, indicators


def analyze_links(links: List[str]) -> tuple[int, List[str]]:
    """
    Analyze links in email for phishing indicators
    Returns: (risk_score, indicators)
    """
    risk_score = 0
    indicators = []
    
    if not links:
        return risk_score, indicators
    
    # Check each link
    for link in links:
        link_lower = link.lower()
        
        # Check for IP addresses instead of domains
        if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', link):
            risk_score += 30
            indicators.append("Link uses IP address instead of domain")
        
        # Check for suspicious TLDs
        for susp_domain in SUSPICIOUS_DOMAINS:
            if susp_domain in link_lower:
                risk_score += 25
                indicators.append(f"Link contains suspicious domain: {susp_domain}")
                break
        
        # Check for URL shorteners
        if any(shortener in link_lower for shortener in ["bit.ly", "tinyurl", "goo.gl", "t.co"]):
            risk_score += 15
            indicators.append("Link uses URL shortener (hides destination)")
        
        # Check for excessive subdomains
        if link_lower.count(".") > 4:
            risk_score += 15
            indicators.append("Link has excessive subdomains")
    
    # Too many links is suspicious
    if len(links) > 10:
        risk_score += 20
        indicators.append(f"Excessive number of links ({len(links)})")
    
    return risk_score, indicators


def analyze_attachments(attachments: List[str]) -> tuple[int, List[str]]:
    """
    Analyze email attachments for phishing indicators
    Returns: (risk_score, indicators)
    """
    risk_score = 0
    indicators = []
    
    if not attachments:
        return risk_score, indicators
    
    # Dangerous file extensions
    dangerous_extensions = [".exe", ".scr", ".bat", ".cmd", ".com", ".pif", ".vbs", ".js"]
    
    for attachment in attachments:
        attachment_lower = attachment.lower()
        
        # Check for dangerous extensions
        for ext in dangerous_extensions:
            if attachment_lower.endswith(ext):
                risk_score += 50
                indicators.append(f"Dangerous attachment type: {attachment}")
                break
        
        # Check for double extensions (e.g., "invoice.pdf.exe")
        if attachment_lower.count(".") > 1:
            risk_score += 30
            indicators.append(f"Suspicious double extension: {attachment}")
    
    return risk_score, indicators


@router.post("/detect", response_model=EmailAnalysisResponse)
async def detect_phishing(request: EmailAnalysisRequest):
    """
    Detect phishing attempts in emails
    
    Analyzes email content using multiple indicators:
    - Sender email and display name
    - Subject line patterns
    - Body content and keywords
    - Links and URLs
    - Attachments
    
    Returns risk assessment with confidence score and recommendations.
    """
    try:
        # Analyze all components
        sender_score, sender_indicators = analyze_sender(request.sender_email, request.sender_name)
        subject_score, subject_indicators = analyze_subject(request.subject)
        body_score, body_indicators = analyze_body(request.body)
        links_score, links_indicators = analyze_links(request.links or [])
        attachments_score, attachments_indicators = analyze_attachments(request.attachments or [])
        
        # Block 5: Check for extremism / self-harm content
        violence_or_extremism_risk = 0
        content_category = "benign"
        tags = []
        body_lower = request.body.lower()
        
        extremism_count = sum(1 for kw in EXTREMISM_KEYWORDS if kw in body_lower)
        self_harm_count = sum(1 for kw in SELF_HARM_KEYWORDS if kw in body_lower)
        
        if extremism_count >= 2:
            violence_or_extremism_risk = min(10, extremism_count * 2)
            content_category = "harmful_extremist_content"
            tags.append("extremism")
        elif self_harm_count >= 1:
            violence_or_extremism_risk = min(10, self_harm_count * 3)
            content_category = "self_harm_risk"
            tags.append("self_harm")
        
        # Calculate total risk score (0-100)
        total_score = min(100, sender_score + subject_score + body_score + links_score + attachments_score)
        
        # Combine all indicators
        all_indicators = (
            sender_indicators + 
            subject_indicators + 
            body_indicators + 
            links_indicators + 
            attachments_indicators
        )
        
        # Determine risk level and phishing status
        if total_score >= 70:
            risk_level = "dangerous"
            is_phishing = True
            recommendations = [
                "⛔ DO NOT click any links in this email",
                "⛔ DO NOT download any attachments",
                "⛔ DO NOT reply with personal information",
                "✅ Delete this email immediately",
                "✅ Report as phishing to your email provider",
                "✅ If you clicked any links, change your passwords immediately"
            ]
        elif total_score >= 40:
            risk_level = "suspicious"
            is_phishing = True
            recommendations = [
                "⚠️ Be very cautious with this email",
                "⚠️ Verify sender identity through official channels",
                "⚠️ Do not click links or download attachments",
                "✅ Contact the organization directly using official contact info",
                "✅ Report as suspicious if confirmed phishing"
            ]
        else:
            risk_level = "safe"
            is_phishing = False
            recommendations = [
                "✅ Email appears legitimate",
                "💡 Still verify sender if requesting sensitive actions",
                "💡 Hover over links before clicking to see destination",
                "💡 Be cautious with attachments from unknown senders"
            ]
        
        # If no indicators found but score is low, add positive note
        if not all_indicators and total_score < 20:
            all_indicators.append("No phishing indicators detected")
        
        confidence_score = min(1.0, total_score / 100.0)
        
        # Block 5: Determine final content category
        if content_category == "benign" and is_phishing:
            content_category = "scam_fraud"
        
        # Block 5: Log high-risk content to evidence vault
        evidence_id = None
        if violence_or_extremism_risk >= 7 and request.user_id:
            try:
                from .block5_vault_helper import log_high_risk_to_vault
                evidence_id = await log_high_risk_to_vault(
                    db=None,  # Will use env DATABASE_URL
                    user_id=str(request.user_id),
                    evidence_type="email",
                    content_category=content_category,
                    violence_or_extremism_risk=violence_or_extremism_risk,
                    tags=tags,
                    analysis_data={
                        "sender_email": request.sender_email,
                        "subject": request.subject,
                        "body_preview": request.body[:200],
                        "extremism_indicators": [kw for kw in EXTREMISM_KEYWORDS if kw in body_lower],
                        "self_harm_indicators": [kw for kw in SELF_HARM_KEYWORDS if kw in body_lower]
                    }
                )
            except Exception as vault_error:
                # Don't fail the whole request if vault logging fails
                print(f"Vault logging failed: {vault_error}")
        
        return EmailAnalysisResponse(
            is_phishing=is_phishing,
            confidence_score=confidence_score,
            risk_level=risk_level,
            threat_indicators=all_indicators,
            recommendations=recommendations,
            analysis_timestamp=datetime.utcnow().isoformat(),
            # Block 5: New risk dimensions
            content_category=content_category,
            violence_or_extremism_risk=violence_or_extremism_risk,
            tags=tags
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email analysis failed: {str(e)}")


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify email phishing detection is working"""
    return {
        "status": "operational",
        "service": "Email Phishing Detection",
        "version": "1.0.0",
        "features": [
            "Sender analysis",
            "Subject line analysis",
            "Body content analysis",
            "Link analysis",
            "Attachment analysis"
        ]
    }
