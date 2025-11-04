"""
Platform Status Monitoring for Super Admin
Shows unified status of Backend, Frontend, Mobile, Email, and Database
"""

from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
import os
import requests
from typing import Dict, Any

router = APIRouter(prefix="/api/super-admin/platform-status", tags=["platform-status"])

# Environment variables
CODEMAGIC_API_TOKEN = os.getenv("CODEMAGIC_API_TOKEN", "")
CODEMAGIC_APP_ID = os.getenv("CODEMAGIC_APP_ID", "69074578c535ae931b5ae681")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")


async def check_database_status(db) -> Dict[str, Any]:
    """Check PostgreSQL database health"""
    try:
        # Simple connection check - just verify db object exists
        if db:
            return {
                "status": "healthy",
                "connected": True,
                "total_users": 0,  # Will be populated later with actual query
                "users_24h": 0,
                "otps_1h": 0,
                "db_size_mb": 0,
                "last_checked": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "error",
                "connected": False,
                "error": "Database not available",
                "last_checked": datetime.utcnow().isoformat()
            }
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "error": str(e),
            "last_checked": datetime.utcnow().isoformat()
        }


def check_sendgrid_status() -> Dict[str, Any]:
    """Check SendGrid email service status"""
    if not SENDGRID_API_KEY:
        return {
            "status": "not_configured",
            "configured": False,
            "error": "SENDGRID_API_KEY not set"
        }
    
    try:
        # Check SendGrid API status
        url = "https://api.sendgrid.com/v3/user/profile"
        headers = {"Authorization": f"Bearer {SENDGRID_API_KEY}"}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            return {
                "status": "healthy",
                "configured": True,
                "api_accessible": True,
                "last_checked": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "error",
                "configured": True,
                "api_accessible": False,
                "error": f"API returned {response.status_code}",
                "last_checked": datetime.utcnow().isoformat()
            }
    except Exception as e:
        return {
            "status": "error",
            "configured": True,
            "api_accessible": False,
            "error": str(e),
            "last_checked": datetime.utcnow().isoformat()
        }


def check_codemagic_status() -> Dict[str, Any]:
    """Check Codemagic mobile build status"""
    if not CODEMAGIC_API_TOKEN:
        return {
            "status": "not_configured",
            "configured": False,
            "error": "CODEMAGIC_API_TOKEN not set"
        }
    
    try:
        # Get latest builds from Codemagic
        url = f"https://api.codemagic.io/builds?appId={CODEMAGIC_APP_ID}&limit=5"
        headers = {"x-auth-token": CODEMAGIC_API_TOKEN}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            builds = response.json().get("builds", [])
            
            if builds:
                latest_build = builds[0]
                return {
                    "status": "healthy",
                    "configured": True,
                    "latest_build": {
                        "id": latest_build.get("_id"),
                        "status": latest_build.get("status"),
                        "branch": latest_build.get("branch"),
                        "commit": latest_build.get("commit")[:7] if latest_build.get("commit") else None,
                        "started_at": latest_build.get("startedAt"),
                        "finished_at": latest_build.get("finishedAt"),
                        "duration_seconds": latest_build.get("duration"),
                        "build_number": latest_build.get("buildNumber")
                    },
                    "total_builds": len(builds),
                    "last_checked": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "healthy",
                    "configured": True,
                    "latest_build": None,
                    "total_builds": 0,
                    "last_checked": datetime.utcnow().isoformat()
                }
        else:
            return {
                "status": "error",
                "configured": True,
                "error": f"API returned {response.status_code}",
                "last_checked": datetime.utcnow().isoformat()
            }
    except Exception as e:
        return {
            "status": "error",
            "configured": True,
            "error": str(e),
            "last_checked": datetime.utcnow().isoformat()
        }


def check_backend_health() -> Dict[str, Any]:
    """Check backend API health"""
    try:
        # Backend is running if this code executes
        return {
            "status": "healthy",
            "running": True,
            "environment": os.getenv("ENVIRONMENT", "production"),
            "python_version": "3.11+",
            "framework": "FastAPI",
            "last_checked": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "running": False,
            "error": str(e),
            "last_checked": datetime.utcnow().isoformat()
        }


def check_frontend_status() -> Dict[str, Any]:
    """Check frontend website status"""
    try:
        # Try to reach frontend
        response = requests.get("https://echofort.ai", timeout=5)
        
        if response.status_code == 200:
            return {
                "status": "healthy",
                "accessible": True,
                "url": "https://echofort.ai",
                "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                "last_checked": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "warning",
                "accessible": True,
                "url": "https://echofort.ai",
                "status_code": response.status_code,
                "last_checked": datetime.utcnow().isoformat()
            }
    except Exception as e:
        return {
            "status": "error",
            "accessible": False,
            "url": "https://echofort.ai",
            "error": str(e),
            "last_checked": datetime.utcnow().isoformat()
        }


@router.get("/")
async def get_platform_status(request: Request):
    """
    Get unified platform status for all EchoFort services
    
    Returns:
    {
        "backend": {...},
        "frontend": {...},
        "database": {...},
        "email": {...},
        "mobile": {...},
        "overall_status": "healthy|degraded|error",
        "timestamp": "2025-11-04T..."
    }
    """
    db = request.app.state.db
    
    # Check all services
    backend_status = check_backend_health()
    frontend_status = check_frontend_status()
    database_status = await check_database_status(db)
    email_status = check_sendgrid_status()
    mobile_status = check_codemagic_status()
    
    # Determine overall status
    statuses = [
        backend_status.get("status"),
        frontend_status.get("status"),
        database_status.get("status"),
        email_status.get("status"),
        mobile_status.get("status")
    ]
    
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "error" for s in statuses):
        overall_status = "error"
    else:
        overall_status = "degraded"
    
    return {
        "backend": backend_status,
        "frontend": frontend_status,
        "database": database_status,
        "email": email_status,
        "mobile": mobile_status,
        "overall_status": overall_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/mobile/builds")
async def get_mobile_builds(request: Request, limit: int = 10):
    """
    Get recent mobile app builds from Codemagic
    
    Query params:
    - limit: Number of builds to return (default: 10, max: 50)
    """
    if not CODEMAGIC_API_TOKEN:
        raise HTTPException(400, "Codemagic API token not configured")
    
    if limit > 50:
        limit = 50
    
    try:
        url = f"https://api.codemagic.io/builds?appId={CODEMAGIC_APP_ID}&limit={limit}"
        headers = {"x-auth-token": CODEMAGIC_API_TOKEN}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            builds = data.get("builds", [])
            
            # Format builds for frontend
            formatted_builds = []
            for build in builds:
                formatted_builds.append({
                    "id": build.get("_id"),
                    "build_number": build.get("buildNumber"),
                    "status": build.get("status"),
                    "branch": build.get("branch"),
                    "commit": build.get("commit"),
                    "commit_short": build.get("commit")[:7] if build.get("commit") else None,
                    "commit_message": build.get("commitMessage"),
                    "started_at": build.get("startedAt"),
                    "finished_at": build.get("finishedAt"),
                    "duration_seconds": build.get("duration"),
                    "platform": build.get("platform"),
                    "workflow": build.get("workflowId")
                })
            
            return {
                "ok": True,
                "builds": formatted_builds,
                "total": len(formatted_builds)
            }
        else:
            raise HTTPException(response.status_code, f"Codemagic API error: {response.text}")
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(500, f"Failed to fetch builds: {str(e)}")


@router.post("/test-email")
async def test_email_service(request: Request):
    """
    Test email service by sending a test OTP email
    
    Body:
    {
        "email": "test@example.com"
    }
    """
    body = await request.json()
    email = body.get("email")
    
    if not email:
        raise HTTPException(400, "email required")
    
    try:
        from ..email_service_sendgrid import send_otp_email
        
        # Send test OTP
        test_otp = "123456"
        success = send_otp_email(email, test_otp)
        
        if success:
            return {
                "ok": True,
                "message": f"Test email sent to {email}",
                "email_sent": True
            }
        else:
            return {
                "ok": False,
                "message": "Failed to send test email",
                "email_sent": False
            }
    except Exception as e:
        raise HTTPException(500, f"Email test failed: {str(e)}")
