"""
Content Filter API - Child Protection System
Filters inappropriate content across apps, websites, and media
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
import re

router = APIRouter(prefix="/api/child-protection", tags=["Child Protection"])


class ContentFilterRequest(BaseModel):
    """Request model for content filtering"""
    content_type: str  # "url", "text", "app_name", "image_url"
    content: str  # The content to analyze
    user_id: Optional[int] = None
    child_age: Optional[int] = None  # Age of child (helps with age-appropriate filtering)


class ContentFilterResponse(BaseModel):
    """Response model for content filtering"""
    is_blocked: bool
    risk_level: str  # "safe", "moderate", "high", "extreme"
    category: Optional[str] = None  # "adult", "violence", "gambling", "drugs", etc.
    reason: str
    age_rating: Optional[str] = None  # "G", "PG", "PG-13", "R", "18+"
    recommendations: List[str]
    timestamp: str


# Blocked keywords database (18+ content)
ADULT_KEYWORDS = [
    "porn", "xxx", "sex", "nude", "naked", "adult", "18+", "nsfw",
    "erotic", "explicit", "mature content"
]

VIOLENCE_KEYWORDS = [
    "gore", "brutal", "murder", "kill", "weapon", "gun", "knife",
    "blood", "death", "torture", "violence"
]

GAMBLING_KEYWORDS = [
    "casino", "poker", "betting", "gamble", "lottery", "jackpot",
    "slot machine", "roulette", "blackjack"
]

DRUGS_KEYWORDS = [
    "drugs", "cocaine", "heroin", "marijuana", "weed", "cannabis",
    "meth", "addiction", "substance abuse"
]

HATE_KEYWORDS = [
    "hate speech", "racist", "discrimination", "terrorism",
    "extremist", "radical"
]

# Blocked domains/apps
BLOCKED_DOMAINS = [
    # Adult content
    "pornhub.com", "xvideos.com", "xnxx.com", "redtube.com",
    "youporn.com", "xhamster.com", "porn.com",
    
    # Gambling
    "bet365.com", "888casino.com", "pokerstars.com",
    
    # Social media (optional - can be age-restricted)
    # "tiktok.com", "snapchat.com", "instagram.com"
]

BLOCKED_APPS = [
    # Adult apps
    "tinder", "bumble", "grindr", "onlyfans",
    
    # Gambling apps
    "draftkings", "fanduel", "betmgm",
    
    # Dating apps
    "match", "okcupid", "hinge"
]

# Safe/Educational domains (whitelist)
SAFE_DOMAINS = [
    "youtube.com/kids", "pbskids.org", "nationalgeographic.com",
    "khanacademy.org", "scratch.mit.edu", "code.org",
    "wikipedia.org", "britannica.com", "nasa.gov"
]

# Age ratings
AGE_RATINGS = {
    "G": 0,      # General Audiences
    "PG": 8,     # Parental Guidance
    "PG-13": 13, # Parents Strongly Cautioned
    "R": 17,     # Restricted
    "18+": 18    # Adults Only
}


def analyze_url(url: str, child_age: Optional[int]) -> tuple[bool, str, Optional[str], str, List[str]]:
    """
    Analyze URL for inappropriate content
    Returns: (is_blocked, risk_level, category, reason, recommendations)
    """
    url_lower = url.lower()
    
    # Check whitelist first
    for safe_domain in SAFE_DOMAINS:
        if safe_domain in url_lower:
            return (
                False,
                "safe",
                None,
                "Whitelisted educational/safe domain",
                ["✅ This website is safe for children"]
            )
    
    # Check blocked domains
    for blocked_domain in BLOCKED_DOMAINS:
        if blocked_domain in url_lower:
            return (
                True,
                "extreme",
                "adult",
                f"Blocked domain: {blocked_domain}",
                [
                    "⛔ This website is blocked for child safety",
                    "🔒 Content is inappropriate for minors",
                    "👨‍👩‍👧 Parents: Consider using parental controls"
                ]
            )
    
    # Check for adult keywords in URL
    for keyword in ADULT_KEYWORDS:
        if keyword in url_lower:
            return (
                True,
                "extreme",
                "adult",
                f"Adult content detected in URL: '{keyword}'",
                [
                    "⛔ Adult content detected",
                    "🔒 Blocked for child protection"
                ]
            )
    
    # Check for gambling keywords
    for keyword in GAMBLING_KEYWORDS:
        if keyword in url_lower:
            return (
                True,
                "high",
                "gambling",
                f"Gambling content detected: '{keyword}'",
                [
                    "⛔ Gambling website blocked",
                    "💰 Not appropriate for minors"
                ]
            )
    
    # Age-based restrictions
    if child_age and child_age < 13:
        social_media = ["facebook.com", "instagram.com", "tiktok.com", "snapchat.com", "twitter.com"]
        for social in social_media:
            if social in url_lower:
                return (
                    True,
                    "moderate",
                    "social_media",
                    f"Social media requires age 13+ (child is {child_age})",
                    [
                        f"⚠️ Minimum age requirement: 13 years",
                        f"👶 Child age: {child_age} years",
                        "👨‍👩‍👧 Consider age-appropriate alternatives"
                    ]
                )
    
    # Default: Allow but monitor
    return (
        False,
        "safe",
        None,
        "No inappropriate content detected",
        [
            "✅ Website appears safe",
            "💡 Continue monitoring browsing activity"
        ]
    )


def analyze_app(app_name: str, child_age: Optional[int]) -> tuple[bool, str, Optional[str], str, List[str]]:
    """
    Analyze app name for inappropriate content
    Returns: (is_blocked, risk_level, category, reason, recommendations)
    """
    app_lower = app_name.lower()
    
    # Check blocked apps
    for blocked_app in BLOCKED_APPS:
        if blocked_app in app_lower:
            return (
                True,
                "high",
                "adult",
                f"Blocked app: {blocked_app}",
                [
                    "⛔ This app is blocked for child safety",
                    "🔒 Not appropriate for minors"
                ]
            )
    
    # Age-based app restrictions
    if child_age and child_age < 13:
        teen_apps = ["tiktok", "snapchat", "instagram", "facebook", "whatsapp"]
        for teen_app in teen_apps:
            if teen_app in app_lower:
                return (
                    True,
                    "moderate",
                    "social_media",
                    f"App requires age 13+ (child is {child_age})",
                    [
                        f"⚠️ Minimum age: 13 years",
                        f"👶 Child age: {child_age} years"
                    ]
                )
    
    # Default: Allow
    return (
        False,
        "safe",
        None,
        "App appears safe",
        ["✅ No restrictions for this app"]
    )


def analyze_text(text: str) -> tuple[bool, str, Optional[str], str, List[str]]:
    """
    Analyze text content for inappropriate material
    Returns: (is_blocked, risk_level, category, reason, recommendations)
    """
    text_lower = text.lower()
    
    # Check for adult content
    for keyword in ADULT_KEYWORDS:
        if keyword in text_lower:
            return (
                True,
                "extreme",
                "adult",
                f"Adult content detected: '{keyword}'",
                [
                    "⛔ Adult content blocked",
                    "🔒 Inappropriate for children"
                ]
            )
    
    # Check for violence
    violence_count = sum(1 for keyword in VIOLENCE_KEYWORDS if keyword in text_lower)
    if violence_count >= 2:
        return (
            True,
            "high",
            "violence",
            f"Violent content detected ({violence_count} indicators)",
            [
                "⛔ Violent content blocked",
                "⚠️ Not suitable for children"
            ]
        )
    
    # Check for drugs
    for keyword in DRUGS_KEYWORDS:
        if keyword in text_lower:
            return (
                True,
                "high",
                "drugs",
                f"Drug-related content detected: '{keyword}'",
                [
                    "⛔ Drug-related content blocked",
                    "⚠️ Inappropriate for minors"
                ]
            )
    
    # Check for hate speech
    for keyword in HATE_KEYWORDS:
        if keyword in text_lower:
            return (
                True,
                "extreme",
                "hate_speech",
                f"Hate speech detected: '{keyword}'",
                [
                    "⛔ Hate speech blocked",
                    "🚫 Harmful content filtered"
                ]
            )
    
    # Default: Safe
    return (
        False,
        "safe",
        None,
        "Content appears safe",
        ["✅ No inappropriate content detected"]
    )


@router.post("/filter", response_model=ContentFilterResponse)
async def filter_content(request: ContentFilterRequest):
    """
    Filter content for child protection
    
    Supports multiple content types:
    - URLs/websites
    - App names
    - Text content
    - Image URLs
    
    Returns blocking decision with risk assessment and recommendations.
    """
    try:
        content_type = request.content_type.lower()
        
        if content_type == "url":
            is_blocked, risk_level, category, reason, recommendations = analyze_url(
                request.content, 
                request.child_age
            )
        elif content_type == "app_name":
            is_blocked, risk_level, category, reason, recommendations = analyze_app(
                request.content,
                request.child_age
            )
        elif content_type == "text":
            is_blocked, risk_level, category, reason, recommendations = analyze_text(
                request.content
            )
        elif content_type == "image_url":
            # For images, analyze the URL first
            is_blocked, risk_level, category, reason, recommendations = analyze_url(
                request.content,
                request.child_age
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content_type: {request.content_type}. Use 'url', 'app_name', 'text', or 'image_url'"
            )
        
        # Determine age rating
        age_rating = None
        if risk_level == "safe":
            age_rating = "G"
        elif risk_level == "moderate":
            age_rating = "PG-13"
        elif risk_level == "high":
            age_rating = "R"
        elif risk_level == "extreme":
            age_rating = "18+"
        
        return ContentFilterResponse(
            is_blocked=is_blocked,
            risk_level=risk_level,
            category=category,
            reason=reason,
            age_rating=age_rating,
            recommendations=recommendations,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content filtering failed: {str(e)}")


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify content filter is working"""
    return {
        "status": "operational",
        "service": "Child Protection Content Filter",
        "version": "1.0.0",
        "features": [
            "URL filtering",
            "App filtering",
            "Text content filtering",
            "Age-based restrictions",
            "Category detection (adult, violence, gambling, drugs, hate speech)"
        ],
        "blocked_categories": [
            "Adult content (18+)",
            "Violence",
            "Gambling",
            "Drugs",
            "Hate speech",
            "Age-inappropriate social media"
        ]
    }
