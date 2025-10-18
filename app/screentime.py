# app/screentime.py
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy import text
from datetime import datetime, timedelta
from .utils import get_current_user

router = APIRouter(prefix="/screentime", tags=["screentime"])

@router.post("/log")
async def log_usage(
    payload: dict,
    request: Request,
    user = Depends(get_current_user)
):
    """
    Log app usage
    Payload: {
        "app_name": "Instagram",
        "category": "social_media",
        "duration_seconds": 1800,
        "date": "2025-10-18"
    }
    """
    app_name = payload.get("app_name")
    category = payload.get("category", "other")
    duration = payload.get("duration_seconds", 0)
    date = payload.get("date", datetime.now().date())
    
    if not app_name or duration <= 0:
        raise HTTPException(400, "Invalid app_name or duration")
    
    db = request.app.state.db
    await db.execute(text("""
        INSERT INTO screen_time_logs(user_id, app_name, category, duration_seconds, usage_date)
        VALUES (:uid, :app, :cat, :dur, :dt)
        ON CONFLICT (user_id, app_name, usage_date)
        DO UPDATE SET duration_seconds = screen_time_logs.duration_seconds + :dur
    """), {"uid": user["user_id"], "app": app_name, "cat": category, "dur": duration, "dt": date})
    
    return {"ok": True, "message": "Usage logged"}


@router.get("/daily")
async def daily_report(
    request: Request,
    user = Depends(get_current_user),
    date: str = None
):
    """Get daily screen time report"""
    target_date = date or datetime.now().date()
    
    db = request.app.state.db
    rows = (await db.execute(text("""
        SELECT app_name, category, duration_seconds, usage_date
        FROM screen_time_logs
        WHERE user_id = :uid AND usage_date = :dt
        ORDER BY duration_seconds DESC
    """), {"uid": user["user_id"], "dt": target_date})).fetchall()
    
    total_seconds = sum(r.duration_seconds for r in rows)
    total_hours = round(total_seconds / 3600, 1)
    
    return {
        "date": str(target_date),
        "total_hours": total_hours,
        "total_seconds": total_seconds,
        "apps": [dict(r._mapping) for r in rows]
    }


@router.get("/weekly")
async def weekly_report(
    request: Request,
    user = Depends(get_current_user)
):
    """Get weekly screen time trend"""
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    db = request.app.state.db
    rows = (await db.execute(text("""
        SELECT usage_date, SUM(duration_seconds) as total_seconds
        FROM screen_time_logs
        WHERE user_id = :uid AND usage_date >= :start
        GROUP BY usage_date
        ORDER BY usage_date ASC
    """), {"uid": user["user_id"], "start": week_ago})).fetchall()
    
    return {
        "period": f"{week_ago} to {today}",
        "daily_totals": [
            {
                "date": str(r.usage_date),
                "hours": round(r.total_seconds / 3600, 1)
            }
            for r in rows
        ]
    }


@router.get("/addiction-risk")
async def addiction_risk(
    request: Request,
    user = Depends(get_current_user)
):
    """Calculate addiction risk score (0-10)"""
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    db = request.app.state.db
    rows = (await db.execute(text("""
        SELECT SUM(duration_seconds) as total_seconds
        FROM screen_time_logs
        WHERE user_id = :uid AND usage_date >= :start
    """), {"uid": user["user_id"], "start": week_ago})).fetchone()
    
    total_hours = (rows.total_seconds or 0) / 3600
    avg_daily = total_hours / 7
    
    # Risk scoring
    if avg_daily > 6:
        risk = 10
        level = "CRITICAL"
    elif avg_daily > 4:
        risk = 7
        level = "HIGH"
    elif avg_daily > 2:
        risk = 4
        level = "MODERATE"
    else:
        risk = 1
        level = "LOW"
    
    return {
        "risk_score": risk,
        "risk_level": level,
        "avg_daily_hours": round(avg_daily, 1),
        "recommendation": "Consider setting daily limit to 2 hours" if risk >= 7 else "Healthy usage"
    }
