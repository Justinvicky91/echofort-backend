"""
Mobile Website/URL Checker API
ScamAdviser-like functionality for URL and email verification
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from urllib.parse import urlparse
from sqlalchemy import text
from .deps import get_db, get_current_user
import re

router = APIRouter(prefix="/api/mobile/web", tags=["Mobile URL Checker"])


class URLCheckRequest(BaseModel):
    url: str = Field(..., description="URL to check")


class EmailCheckRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address to verify")


class ReportPhishingRequest(BaseModel):
    url: str
    phishingType: Optional[str] = None
    targetBrand: Optional[str] = None
    description: Optional[str] = None


@router.post("/check-url")
async def check_url(
    request: URLCheckRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Check if a URL is safe or potentially malicious
    Returns trust score and risk factors
    """
    try:
        url = request.url.strip()
        
        # Parse URL
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split('/')[0]
        except:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Calculate trust score using database function
        query = text("""
            SELECT * FROM calculate_url_trust_score(:url, :domain)
        """)
        
        result = db.execute(query, {
            "url": url,
            "domain": domain
        }).fetchone()
        
        trust_score = result[0] if result else 50
        risk_level = result[1] if result else "unknown"
        risk_factors = result[2] if result else []
        
        # Determine if phishing/malware/scam
        is_phishing = trust_score < 30
        is_malware = trust_score < 20
        is_scam = trust_score < 40
        
        # Check SSL (simplified - in production would use actual SSL check)
        ssl_valid = url.startswith('https://')
        
        # Save check result
        save_query = text("""
            INSERT INTO url_check_results 
            (user_id, url, domain, trust_score, is_phishing, is_malware, is_scam, 
             risk_level, risk_factors, ssl_valid)
            VALUES (:user_id, :url, :domain, :trust_score, :is_phishing, :is_malware, 
                    :is_scam, :risk_level, :risk_factors, :ssl_valid)
            RETURNING id
        """)
        
        check_id = db.execute(save_query, {
            "user_id": current_user["id"],
            "url": url,
            "domain": domain,
            "trust_score": trust_score,
            "is_phishing": is_phishing,
            "is_malware": is_malware,
            "is_scam": is_scam,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "ssl_valid": ssl_valid
        }).fetchone()[0]
        
        # Update statistics
        stats_query = text("""
            INSERT INTO url_check_statistics (user_id, urls_checked, phishing_detected, last_check_at)
            VALUES (:user_id, 1, :phishing, :now)
            ON CONFLICT (user_id) DO UPDATE
            SET urls_checked = url_check_statistics.urls_checked + 1,
                phishing_detected = url_check_statistics.phishing_detected + :phishing,
                last_check_at = :now,
                updated_at = :now
        """)
        
        db.execute(stats_query, {
            "user_id": current_user["id"],
            "phishing": 1 if is_phishing else 0,
            "now": datetime.utcnow()
        })
        
        db.commit()
        
        # Recommendation
        if trust_score >= 80:
            recommendation = "This website appears safe to visit"
        elif trust_score >= 60:
            recommendation = "Be cautious when visiting this website"
        elif trust_score >= 40:
            recommendation = "This website may be risky - proceed with caution"
        else:
            recommendation = "Do not visit this website - high risk of phishing/scam"
        
        return {
            "ok": True,
            "checkId": check_id,
            "url": url,
            "domain": domain,
            "trustScore": trust_score,
            "riskLevel": risk_level,
            "isPhishing": is_phishing,
            "isMalware": is_malware,
            "isScam": is_scam,
            "sslValid": ssl_valid,
            "riskFactors": risk_factors,
            "recommendation": recommendation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"URL check failed: {str(e)}")


@router.post("/check-email")
async def check_email(
    request: EmailCheckRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Verify if an email address is valid and not disposable
    """
    try:
        email = request.email.lower()
        domain = email.split('@')[1]
        
        # Check if disposable
        disposable_query = text("""
            SELECT is_disposable_email(:email)
        """)
        
        is_disposable = db.execute(disposable_query, {"email": email}).fetchone()[0]
        
        # Check if role-based (common role emails)
        role_based_keywords = ['admin', 'info', 'support', 'contact', 'sales', 'noreply', 'no-reply']
        is_role_based = any(keyword in email.split('@')[0] for keyword in role_based_keywords)
        
        # Calculate risk score
        risk_score = 0
        if is_disposable:
            risk_score += 50
        if is_role_based:
            risk_score += 20
        if len(email.split('@')[0]) < 3:
            risk_score += 10
        
        risk_score = min(risk_score, 100)
        
        # Save check result
        save_query = text("""
            INSERT INTO email_check_results 
            (user_id, email, domain, is_valid, is_disposable, is_role_based, risk_score)
            VALUES (:user_id, :email, :domain, :is_valid, :is_disposable, :is_role_based, :risk_score)
            RETURNING id
        """)
        
        check_id = db.execute(save_query, {
            "user_id": current_user["id"],
            "email": email,
            "domain": domain,
            "is_valid": True,  # Basic validation passed (pydantic EmailStr)
            "is_disposable": is_disposable,
            "is_role_based": is_role_based,
            "risk_score": risk_score
        }).fetchone()[0]
        
        # Update statistics
        stats_query = text("""
            UPDATE url_check_statistics
            SET emails_verified = emails_verified + 1,
                disposable_emails_found = disposable_emails_found + :disposable,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
        """)
        
        db.execute(stats_query, {
            "user_id": current_user["id"],
            "disposable": 1 if is_disposable else 0
        })
        
        db.commit()
        
        # Recommendation
        if risk_score < 30:
            recommendation = "Email appears legitimate"
        elif risk_score < 60:
            recommendation = "Email may be suspicious"
        else:
            recommendation = "High risk email - likely disposable or fake"
        
        return {
            "ok": True,
            "checkId": check_id,
            "email": email,
            "domain": domain,
            "isValid": True,
            "isDisposable": is_disposable,
            "isRoleBased": is_role_based,
            "riskScore": risk_score,
            "recommendation": recommendation
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Email check failed: {str(e)}")


@router.post("/report-phishing")
async def report_phishing(
    request: ReportPhishingRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Report a phishing website
    """
    try:
        url = request.url.strip()
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        
        # Insert or update phishing domain
        query = text("""
            INSERT INTO phishing_domains 
            (domain, reported_by, phishing_type, target_brand, report_count)
            VALUES (:domain, :user_id, :phishing_type, :target_brand, 1)
            ON CONFLICT (domain) DO UPDATE
            SET report_count = phishing_domains.report_count + 1,
                last_reported_at = CURRENT_TIMESTAMP
            RETURNING id
        """)
        
        result = db.execute(query, {
            "domain": domain,
            "user_id": current_user["id"],
            "phishing_type": request.phishingType,
            "target_brand": request.targetBrand
        })
        
        phishing_id = result.fetchone()[0]
        db.commit()
        
        return {
            "ok": True,
            "phishingId": phishing_id,
            "message": "Thank you for reporting. This helps protect the community."
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-checks")
async def get_recent_checks(
    limit: int = 20,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user's recent URL checks
    """
    try:
        query = text("""
            SELECT 
                url,
                domain,
                trust_score,
                risk_level,
                is_phishing,
                checked_at
            FROM url_check_results
            WHERE user_id = :user_id
            ORDER BY checked_at DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {
            "user_id": current_user["id"],
            "limit": limit
        }).fetchall()
        
        checks = []
        for row in results:
            checks.append({
                "url": row[0],
                "domain": row[1],
                "trustScore": row[2],
                "riskLevel": row[3],
                "isPhishing": row[4],
                "checkedAt": row[5].isoformat() if row[5] else None
            })
        
        return {"ok": True, "recentChecks": checks}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get URL/email check statistics
    """
    try:
        query = text("""
            SELECT 
                urls_checked,
                phishing_detected,
                emails_verified,
                disposable_emails_found,
                last_check_at
            FROM url_check_statistics
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": current_user["id"]}).fetchone()
        
        if result:
            return {
                "ok": True,
                "statistics": {
                    "urlsChecked": result[0] or 0,
                    "phishingDetected": result[1] or 0,
                    "emailsVerified": result[2] or 0,
                    "disposableEmailsFound": result[3] or 0,
                    "lastCheckAt": result[4].isoformat() if result[4] else None
                }
            }
        else:
            return {
                "ok": True,
                "statistics": {
                    "urlsChecked": 0,
                    "phishingDetected": 0,
                    "emailsVerified": 0,
                    "disposableEmailsFound": 0,
                    "lastCheckAt": None
                }
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/known-phishing")
async def get_known_phishing(
    limit: int = 50,
    db=Depends(get_db)
):
    """
    Get list of known phishing domains (public endpoint)
    """
    try:
        query = text("""
            SELECT 
                domain,
                phishing_type,
                target_brand,
                report_count,
                last_reported_at
            FROM phishing_domains
            WHERE status = 'active'
            ORDER BY report_count DESC, last_reported_at DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {"limit": limit}).fetchall()
        
        domains = []
        for row in results:
            domains.append({
                "domain": row[0],
                "phishingType": row[1],
                "targetBrand": row[2],
                "reportCount": row[3],
                "lastReported": row[4].isoformat() if row[4] else None
            })
        
        return {"ok": True, "phishingDomains": domains}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
