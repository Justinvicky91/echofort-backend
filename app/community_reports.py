# app/community_reports.py - Community Scam Reporting
"""
Community Scam Reporting - User-submitted Scam Reports
Crowdsourced scam database for community protection
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr
from .utils import get_current_user

router = APIRouter(prefix="/api/community", tags=["Community Reports"])


class ScamReport(BaseModel):
    scam_type: Literal["digital_arrest", "investment_fraud", "phishing", "lottery_scam", "tech_support", "romance_scam", "job_scam", "other"]
    title: str
    description: str
    scammer_phone: Optional[str] = None
    scammer_email: Optional[str] = None
    scammer_name: Optional[str] = None
    scammer_company: Optional[str] = None
    amount_lost: Optional[float] = None
    incident_date: str
    location: Optional[str] = None
    evidence_urls: Optional[list[str]] = None
    reported_to_police: bool = False


class ReportVote(BaseModel):
    report_id: int
    vote_type: Literal["helpful", "not_helpful", "fake"]


class ReportComment(BaseModel):
    report_id: int
    comment: str


@router.post("/report-scam")
async def submit_scam_report(
    request: Request,
    payload: ScamReport,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit a scam report to the community database
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Save report
        insert_query = text("""
            INSERT INTO community_reports (
                user_id, scam_type, title, description,
                scammer_phone, scammer_email, scammer_name, scammer_company,
                amount_lost, incident_date, location,
                evidence_urls, reported_to_police,
                status, view_count, helpful_count, created_at
            ) VALUES (
                :uid, :type, :title, :desc,
                :phone, :email, :name, :company,
                :amount, :date, :loc,
                :evidence::jsonb, :police,
                'pending', 0, 0, NOW()
            ) RETURNING id
        """)
        
        result = await db.execute(insert_query, {
            "uid": user_id,
            "type": payload.scam_type,
            "title": payload.title,
            "desc": payload.description,
            "phone": payload.scammer_phone,
            "email": payload.scammer_email,
            "name": payload.scammer_name,
            "company": payload.scammer_company,
            "amount": payload.amount_lost,
            "date": payload.incident_date,
            "loc": payload.location,
            "evidence": str(payload.evidence_urls) if payload.evidence_urls else "[]",
            "police": payload.reported_to_police
        })
        
        report_id = result.fetchone()[0]
        
        return {
            "ok": True,
            "report_id": report_id,
            "status": "pending",
            "message": "Scam report submitted successfully",
            "note": "Report will be reviewed and published within 24 hours"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Report submission error: {str(e)}")


@router.get("/recent-reports")
async def get_recent_reports(
    request: Request,
    scam_type: Optional[str] = None,
    limit: int = 50
):
    """
    Get recent community scam reports
    """
    try:
        db = request.app.state.db
        
        if scam_type:
            query = text("""
                SELECT 
                    r.id, r.scam_type, r.title, r.description,
                    r.scammer_phone, r.amount_lost, r.incident_date,
                    r.location, r.view_count, r.helpful_count,
                    r.created_at, u.name as reporter_name
                FROM community_reports r
                LEFT JOIN users u ON r.user_id = u.id
                WHERE r.status = 'approved' AND r.scam_type = :type
                ORDER BY r.created_at DESC
                LIMIT :lim
            """)
            reports = (await db.execute(query, {"type": scam_type, "lim": limit})).fetchall()
        else:
            query = text("""
                SELECT 
                    r.id, r.scam_type, r.title, r.description,
                    r.scammer_phone, r.amount_lost, r.incident_date,
                    r.location, r.view_count, r.helpful_count,
                    r.created_at, u.name as reporter_name
                FROM community_reports r
                LEFT JOIN users u ON r.user_id = u.id
                WHERE r.status = 'approved'
                ORDER BY r.created_at DESC
                LIMIT :lim
            """)
            reports = (await db.execute(query, {"lim": limit})).fetchall()
        
        return {
            "ok": True,
            "total": len(reports),
            "reports": [
                {
                    "report_id": r[0],
                    "scam_type": r[1],
                    "title": r[2],
                    "description": r[3][:200] + "..." if len(r[3]) > 200 else r[3],
                    "scammer_phone": r[4],
                    "amount_lost": float(r[5]) if r[5] else None,
                    "incident_date": r[6],
                    "location": r[7],
                    "view_count": r[8],
                    "helpful_count": r[9],
                    "reported_at": str(r[10]),
                    "reporter_name": r[11] or "Anonymous"
                }
                for r in reports
            ]
        }
    
    except Exception as e:
        raise HTTPException(500, f"Reports fetch error: {str(e)}")


@router.get("/report/{report_id}")
async def get_report_details(request: Request, report_id: int):
    """
    Get full details of a specific scam report
    """
    try:
        db = request.app.state.db
        
        # Increment view count
        await db.execute(text("""
            UPDATE community_reports
            SET view_count = view_count + 1
            WHERE id = :rid
        """), {"rid": report_id})
        
        # Get report details
        query = text("""
            SELECT 
                r.id, r.scam_type, r.title, r.description,
                r.scammer_phone, r.scammer_email, r.scammer_name, r.scammer_company,
                r.amount_lost, r.incident_date, r.location,
                r.evidence_urls, r.reported_to_police,
                r.view_count, r.helpful_count, r.created_at,
                u.name as reporter_name
            FROM community_reports r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.id = :rid
        """)
        
        report = (await db.execute(query, {"rid": report_id})).fetchone()
        
        if not report:
            raise HTTPException(404, "Report not found")
        
        return {
            "ok": True,
            "report": {
                "report_id": report[0],
                "scam_type": report[1],
                "title": report[2],
                "description": report[3],
                "scammer_phone": report[4],
                "scammer_email": report[5],
                "scammer_name": report[6],
                "scammer_company": report[7],
                "amount_lost": float(report[8]) if report[8] else None,
                "incident_date": report[9],
                "location": report[10],
                "evidence_urls": eval(report[11]) if report[11] else [],
                "reported_to_police": report[12],
                "view_count": report[13],
                "helpful_count": report[14],
                "reported_at": str(report[15]),
                "reporter_name": report[16] or "Anonymous"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Report fetch error: {str(e)}")


@router.post("/vote")
async def vote_on_report(
    request: Request,
    payload: ReportVote,
    current_user: dict = Depends(get_current_user)
):
    """
    Vote on a community report (helpful/not helpful/fake)
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Check if already voted
        existing_vote = (await db.execute(text("""
            SELECT vote_type FROM report_votes
            WHERE report_id = :rid AND user_id = :uid
        """), {"rid": payload.report_id, "uid": user_id})).fetchone()
        
        if existing_vote:
            # Update vote
            await db.execute(text("""
                UPDATE report_votes
                SET vote_type = :vtype, updated_at = NOW()
                WHERE report_id = :rid AND user_id = :uid
            """), {"vtype": payload.vote_type, "rid": payload.report_id, "uid": user_id})
        else:
            # Insert new vote
            await db.execute(text("""
                INSERT INTO report_votes (report_id, user_id, vote_type, created_at)
                VALUES (:rid, :uid, :vtype, NOW())
            """), {"rid": payload.report_id, "uid": user_id, "vtype": payload.vote_type})
        
        # Update helpful count
        if payload.vote_type == "helpful":
            await db.execute(text("""
                UPDATE community_reports
                SET helpful_count = helpful_count + 1
                WHERE id = :rid
            """), {"rid": payload.report_id})
        
        return {
            "ok": True,
            "message": "Vote recorded",
            "vote_type": payload.vote_type
        }
    
    except Exception as e:
        raise HTTPException(500, f"Voting error: {str(e)}")


@router.post("/comment")
async def add_comment(
    request: Request,
    payload: ReportComment,
    current_user: dict = Depends(get_current_user)
):
    """
    Add a comment to a scam report
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        # Insert comment
        insert_query = text("""
            INSERT INTO report_comments (report_id, user_id, comment, created_at)
            VALUES (:rid, :uid, :comment, NOW())
            RETURNING id
        """)
        
        result = await db.execute(insert_query, {
            "rid": payload.report_id,
            "uid": user_id,
            "comment": payload.comment
        })
        
        comment_id = result.fetchone()[0]
        
        return {
            "ok": True,
            "comment_id": comment_id,
            "message": "Comment added"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Comment error: {str(e)}")


@router.get("/search")
async def search_reports(
    request: Request,
    query: str,
    scam_type: Optional[str] = None,
    limit: int = 30
):
    """
    Search community reports by phone number, email, or keywords
    """
    try:
        db = request.app.state.db
        
        search_pattern = f"%{query}%"
        
        if scam_type:
            search_query = text("""
                SELECT 
                    id, scam_type, title, scammer_phone, scammer_email,
                    amount_lost, incident_date, helpful_count
                FROM community_reports
                WHERE status = 'approved' 
                AND scam_type = :type
                AND (
                    scammer_phone LIKE :q 
                    OR scammer_email LIKE :q 
                    OR title LIKE :q 
                    OR description LIKE :q
                )
                ORDER BY helpful_count DESC, created_at DESC
                LIMIT :lim
            """)
            results = (await db.execute(search_query, {"type": scam_type, "q": search_pattern, "lim": limit})).fetchall()
        else:
            search_query = text("""
                SELECT 
                    id, scam_type, title, scammer_phone, scammer_email,
                    amount_lost, incident_date, helpful_count
                FROM community_reports
                WHERE status = 'approved'
                AND (
                    scammer_phone LIKE :q 
                    OR scammer_email LIKE :q 
                    OR title LIKE :q 
                    OR description LIKE :q
                )
                ORDER BY helpful_count DESC, created_at DESC
                LIMIT :lim
            """)
            results = (await db.execute(search_query, {"q": search_pattern, "lim": limit})).fetchall()
        
        return {
            "ok": True,
            "query": query,
            "total_results": len(results),
            "results": [
                {
                    "report_id": r[0],
                    "scam_type": r[1],
                    "title": r[2],
                    "scammer_phone": r[3],
                    "scammer_email": r[4],
                    "amount_lost": float(r[5]) if r[5] else None,
                    "incident_date": r[6],
                    "helpful_count": r[7]
                }
                for r in results
            ]
        }
    
    except Exception as e:
        raise HTTPException(500, f"Search error: {str(e)}")


@router.get("/stats")
async def get_community_stats(request: Request):
    """
    Get community reporting statistics
    """
    try:
        db = request.app.state.db
        
        stats_query = text("""
            SELECT 
                COUNT(*) as total_reports,
                COUNT(*) FILTER (WHERE status = 'approved') as approved_reports,
                COUNT(DISTINCT scammer_phone) as unique_scammers,
                SUM(amount_lost) as total_amount_lost,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as reports_last_week
            FROM community_reports
        """)
        
        stats = (await db.execute(stats_query)).fetchone()
        
        # Get top scam types
        top_types_query = text("""
            SELECT scam_type, COUNT(*) as count
            FROM community_reports
            WHERE status = 'approved'
            GROUP BY scam_type
            ORDER BY count DESC
            LIMIT 5
        """)
        
        top_types = (await db.execute(top_types_query)).fetchall()
        
        return {
            "ok": True,
            "stats": {
                "total_reports": stats[0] or 0,
                "approved_reports": stats[1] or 0,
                "unique_scammers": stats[2] or 0,
                "total_amount_lost": float(stats[3]) if stats[3] else 0.0,
                "reports_last_week": stats[4] or 0
            },
            "top_scam_types": [
                {
                    "scam_type": t[0],
                    "count": t[1]
                }
                for t in top_types
            ]
        }
    
    except Exception as e:
        raise HTTPException(500, f"Stats error: {str(e)}")


@router.get("/my-reports")
async def get_my_reports(
    request: Request,
    current_user: dict = Depends(get_current_user),
    limit: int = 20
):
    """
    Get user's submitted reports
    """
    try:
        user_id = current_user["id"]
        db = request.app.state.db
        
        reports_query = text("""
            SELECT 
                id, scam_type, title, status, view_count,
                helpful_count, created_at
            FROM community_reports
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT :lim
        """)
        
        reports = (await db.execute(reports_query, {"uid": user_id, "lim": limit})).fetchall()
        
        return {
            "ok": True,
            "total": len(reports),
            "reports": [
                {
                    "report_id": r[0],
                    "scam_type": r[1],
                    "title": r[2],
                    "status": r[3],
                    "view_count": r[4],
                    "helpful_count": r[5],
                    "submitted_at": str(r[6])
                }
                for r in reports
            ]
        }
    
    except Exception as e:
        raise HTTPException(500, f"Reports fetch error: {str(e)}")

