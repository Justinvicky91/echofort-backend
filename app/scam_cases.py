"""
Scam Cases API
Manages scam case database, user reporting, and live scam alerts.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import psycopg
from app.deps import get_current_user, get_db

router = APIRouter()


class ScamCase(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    amount_lost: Optional[float] = None
    scam_type: str  # "digital_arrest", "investment", "loan", "romance", etc.
    severity: str  # "critical", "high", "medium", "low"
    location: Optional[str] = None  # City, State
    reported_at: datetime
    source_url: Optional[str] = None  # News article URL
    source_name: Optional[str] = None  # "Times of India", "NDTV", etc.
    verified: bool = False


class UserScamReport(BaseModel):
    id: Optional[str] = None
    user_id: str
    phone_number: str
    scam_type: str
    amount_lost: Optional[float] = None
    description: str
    evidence_urls: Optional[List[str]] = None
    reported_at: datetime
    status: str  # "pending", "verified", "rejected"


@router.get("/cases", response_model=List[ScamCase])
async def get_scam_cases(
    scam_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db = Depends(get_db)
):
    """Get latest scam cases from database"""
    
    query = "SELECT * FROM scam_cases WHERE verified = TRUE"
    params = []
    
    if scam_type:
        query += " AND scam_type = %s"
        params.append(scam_type)
    
    if severity:
        query += " AND severity = %s"
        params.append(severity)
    
    query += " ORDER BY reported_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    cursor = db.cursor()
    cursor.execute(query, params)
    cases = cursor.fetchall()
    
    return [
        ScamCase(
            id=str(c[0]),
            title=c[1],
            description=c[2],
            amount_lost=c[3],
            scam_type=c[4],
            severity=c[5],
            location=c[6],
            reported_at=c[7],
            source_url=c[8],
            source_name=c[9],
            verified=c[10]
        )
        for c in cases
    ]


@router.get("/live-alerts", response_model=List[ScamCase])
async def get_live_scam_alerts(
    hours: int = 12,  # Get scams from last 12 hours
    db = Depends(get_db)
):
    """
    Get live scam alerts for sidebar.
    Auto-updates every 12 hours.
    """
    
    since = datetime.now() - timedelta(hours=hours)
    
    query = """
        SELECT * FROM scam_cases
        WHERE verified = TRUE
        AND reported_at >= %s
        ORDER BY reported_at DESC
        LIMIT 5
    """
    
    cursor = db.cursor()
    cursor.execute(query, (since,))
    cases = cursor.fetchall()
    
    return [
        ScamCase(
            id=str(c[0]),
            title=c[1],
            description=c[2],
            amount_lost=c[3],
            scam_type=c[4],
            severity=c[5],
            location=c[6],
            reported_at=c[7],
            source_url=c[8],
            source_name=c[9],
            verified=c[10]
        )
        for c in cases
    ]


@router.post("/report")
async def report_scam(
    report: UserScamReport,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """User reports a scam they encountered"""
    
    user_id = current_user["id"]
    
    query = """
        INSERT INTO user_scam_reports (
            user_id, phone_number, scam_type, amount_lost,
            description, evidence_urls, reported_at, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    cursor = db.cursor()
    cursor.execute(query, (
        user_id,
        report.phone_number,
        report.scam_type,
        report.amount_lost,
        report.description,
        report.evidence_urls,
        datetime.now(),
        "pending"
    ))
    report_id = cursor.fetchone()[0]
    db.commit()
    
    return {
        "success": True,
        "report_id": str(report_id),
        "message": "Scam reported successfully. Our team will verify and update the database."
    }


@router.get("/stats")
async def get_scam_stats(db = Depends(get_db)):
    """Get overall scam statistics"""
    
    query = """
        SELECT 
            COUNT(*) as total_cases,
            COUNT(*) FILTER (WHERE scam_type = 'digital_arrest') as digital_arrest,
            COUNT(*) FILTER (WHERE scam_type = 'investment') as investment,
            COUNT(*) FILTER (WHERE scam_type = 'loan') as loan,
            COUNT(*) FILTER (WHERE scam_type = 'romance') as romance,
            SUM(amount_lost) as total_amount_lost,
            COUNT(*) FILTER (WHERE severity = 'critical') as critical_cases
        FROM scam_cases
        WHERE verified = TRUE
    """
    
    cursor = db.cursor()
    cursor.execute(query)
    stats = cursor.fetchone()
    
    return {
        "total_cases": stats[0] or 0,
        "digital_arrest_cases": stats[1] or 0,
        "investment_scams": stats[2] or 0,
        "loan_scams": stats[3] or 0,
        "romance_scams": stats[4] or 0,
        "total_amount_lost": float(stats[5]) if stats[5] else 0.0,
        "critical_cases": stats[6] or 0
    }


@router.get("/admin/reports")
async def get_user_reports(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Admin: Get user-reported scams for verification"""
    
    role = current_user.get("role", "user")
    
    if role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only admins can access user reports"
        )
    
    query = "SELECT * FROM user_scam_reports"
    params = []
    
    if status:
        query += " WHERE status = %s"
        params.append(status)
    
    query += " ORDER BY reported_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    cursor = db.cursor()
    cursor.execute(query, params)
    reports = cursor.fetchall()
    
    return [
        UserScamReport(
            id=str(r[0]),
            user_id=str(r[1]),
            phone_number=r[2],
            scam_type=r[3],
            amount_lost=r[4],
            description=r[5],
            evidence_urls=r[6],
            reported_at=r[7],
            status=r[8]
        )
        for r in reports
    ]


@router.post("/admin/verify/{report_id}")
async def verify_scam_report(
    report_id: str,
    approved: bool,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Admin: Verify user-reported scam"""
    
    role = current_user.get("role", "user")
    
    if role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only admins can verify reports"
        )
    
    if approved:
        # Get report details
        cursor = db.cursor()
        cursor.execute("SELECT * FROM user_scam_reports WHERE id = %s", (report_id,))
        report = cursor.fetchone()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Create verified scam case
        query = """
            INSERT INTO scam_cases (
                title, description, amount_lost, scam_type,
                severity, reported_at, verified
            ) VALUES (%s, %s, %s, %s, %s, %s, TRUE)
        """
        
        title = f"{report[3].replace('_', ' ').title()} Scam - ₹{report[4] or 0}"
        
        cursor.execute(query, (
            title,
            report[5],  # description
            report[4],  # amount_lost
            report[3],  # scam_type
            "high",  # severity
            report[7]  # reported_at
        ))
        
        # Update report status
        cursor.execute(
            "UPDATE user_scam_reports SET status = 'verified' WHERE id = %s",
            (report_id,)
        )
        db.commit()
        
        return {"success": True, "message": "Report verified and added to scam database"}
    
    else:
        # Reject report
        cursor = db.cursor()
        cursor.execute(
            "UPDATE user_scam_reports SET status = 'rejected' WHERE id = %s",
            (report_id,)
        )
        db.commit()
        
        return {"success": True, "message": "Report rejected"}

