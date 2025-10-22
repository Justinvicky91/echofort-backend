from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import psycopg
import os
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/api/public", tags=["Public Content"])

def get_db_connection():
    """Get database connection"""
    return psycopg.connect(os.getenv("DATABASE_URL"))

class YouTubeVideo(BaseModel):
    id: int
    title: str
    description: Optional[str]
    video_id: str
    thumbnail_url: Optional[str]
    duration: Optional[str]
    category: str
    view_count: int

class ScamAlert(BaseModel):
    id: int
    title: str
    description: str
    amount: Optional[str]
    severity: str
    source: Optional[str]
    link: Optional[str]
    location: Optional[str]
    reported_at: datetime

@router.get("/youtube/current")
async def get_current_video():
    """
    Get current YouTube video for homepage
    Rotates every 30 minutes based on server time
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all active videos
        cursor.execute("""
            SELECT id, title, description, video_id, thumbnail_url, 
                   duration, category, view_count
            FROM youtube_videos
            WHERE active = true
            ORDER BY rotation_priority ASC
        """)
        
        videos = cursor.fetchall()
        
        if not videos:
            return {
                "success": False,
                "message": "No videos available"
            }
        
        # Calculate which video to show based on 30-minute rotation
        current_time = datetime.now()
        minutes_since_midnight = current_time.hour * 60 + current_time.minute
        rotation_index = (minutes_since_midnight // 30) % len(videos)
        
        current_video = videos[rotation_index]
        
        # Increment view count
        cursor.execute("""
            UPDATE youtube_videos 
            SET view_count = view_count + 1,
                updated_at = NOW()
            WHERE id = %s
        """, (current_video[0],))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "video": {
                "id": current_video[0],
                "title": current_video[1],
                "description": current_video[2],
                "video_id": current_video[3],
                "thumbnail_url": current_video[4],
                "duration": current_video[5],
                "category": current_video[6],
                "view_count": current_video[7] + 1,
                "embed_url": f"https://www.youtube.com/embed/{current_video[3]}",
                "watch_url": f"https://www.youtube.com/watch?v={current_video[3]}"
            },
            "rotation_info": {
                "current_index": rotation_index + 1,
                "total_videos": len(videos),
                "next_rotation_in_minutes": 30 - (minutes_since_midnight % 30),
                "rotation_interval": "30 minutes"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching video: {str(e)}")

@router.get("/youtube/all")
async def get_all_videos():
    """Get all active YouTube videos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, description, video_id, thumbnail_url, 
                   duration, category, view_count
            FROM youtube_videos
            WHERE active = true
            ORDER BY rotation_priority ASC
        """)
        
        videos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "videos": [
                {
                    "id": v[0],
                    "title": v[1],
                    "description": v[2],
                    "video_id": v[3],
                    "thumbnail_url": v[4],
                    "duration": v[5],
                    "category": v[6],
                    "view_count": v[7],
                    "embed_url": f"https://www.youtube.com/embed/{v[3]}"
                }
                for v in videos
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching videos: {str(e)}")

@router.get("/scam-alerts/live")
async def get_live_scam_alerts():
    """
    Get live scam alerts for homepage sidebar
    Updates every 12 hours from database
    Returns latest 10 alerts
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, description, amount, severity, source, 
                   link, location, reported_at, view_count
            FROM scam_alerts
            WHERE active = true
            ORDER BY reported_at DESC
            LIMIT 10
        """)
        
        alerts = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Calculate time since last update
        if alerts:
            latest_alert_time = alerts[0][8]
            hours_since_update = (datetime.now() - latest_alert_time).total_seconds() / 3600
            next_update_hours = max(0, 12 - hours_since_update)
        else:
            next_update_hours = 0
        
        return {
            "success": True,
            "alerts": [
                {
                    "id": a[0],
                    "title": a[1],
                    "description": a[2],
                    "amount": a[3],
                    "severity": a[4],
                    "source": a[5],
                    "link": a[6],
                    "location": a[7],
                    "time": calculate_time_ago(a[8]),
                    "reported_at": a[8].isoformat() if a[8] else None
                }
                for a in alerts
            ],
            "update_info": {
                "total_alerts": len(alerts),
                "next_update_in_hours": round(next_update_hours, 1),
                "update_interval": "12 hours",
                "last_updated": alerts[0][8].isoformat() if alerts else None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching scam alerts: {str(e)}")

@router.post("/scam-alerts/add")
async def add_scam_alert(
    title: str,
    description: str,
    amount: Optional[str] = None,
    severity: str = "medium",
    source: Optional[str] = None,
    link: Optional[str] = None,
    location: Optional[str] = None
):
    """Add a new scam alert (admin only in production)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scam_alerts 
            (title, description, amount, severity, source, link, location, reported_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (title, description, amount, severity, source, link, location))
        
        alert_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Scam alert added successfully",
            "alert_id": alert_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding scam alert: {str(e)}")

@router.post("/youtube/add")
async def add_youtube_video(
    title: str,
    video_id: str,
    description: Optional[str] = None,
    category: str = "demo",
    rotation_priority: int = 1
):
    """Add a new YouTube video (admin only in production)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate thumbnail URL
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        cursor.execute("""
            INSERT INTO youtube_videos 
            (title, description, video_id, thumbnail_url, category, rotation_priority)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (title, description, video_id, thumbnail_url, category, rotation_priority))
        
        video_id_db = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": "YouTube video added successfully",
            "video_id": video_id_db
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding video: {str(e)}")

def calculate_time_ago(reported_at: datetime) -> str:
    """Calculate human-readable time ago"""
    if not reported_at:
        return "Unknown"
    
    now = datetime.now()
    diff = now - reported_at
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

@router.get("/stats")
async def get_public_stats():
    """Get public statistics for homepage"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total video views
        cursor.execute("SELECT COALESCE(SUM(view_count), 0) FROM youtube_videos")
        total_video_views = cursor.fetchone()[0]
        
        # Get total scam alerts
        cursor.execute("SELECT COUNT(*) FROM scam_alerts WHERE active = true")
        total_alerts = cursor.fetchone()[0]
        
        # Get total users (mock for now)
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "stats": {
                "users_protected": max(50000, total_users),
                "scams_blocked": max(125000, total_alerts * 100),
                "money_saved": "₹150Cr+",
                "video_views": total_video_views,
                "active_alerts": total_alerts
            }
        }
        
    except Exception as e:
        return {
            "success": True,
            "stats": {
                "users_protected": 50000,
                "scams_blocked": 125000,
                "money_saved": "₹150Cr+",
                "video_views": 0,
                "active_alerts": 0
            }
        }

