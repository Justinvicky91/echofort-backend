# app/live_alerts.py - Live Scam Alerts WebSocket
"""
Live Alerts - Real-time Scam Alert Broadcasting
WebSocket-based live updates for emerging scam threats
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional, List, Literal
from pydantic import BaseModel
import json
import asyncio

router = APIRouter(prefix="/api/live-alerts", tags=["Live Alerts"])

# Active WebSocket connections
active_connections: List[WebSocket] = []


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)


manager = ConnectionManager()


class ScamAlert(BaseModel):
    title: str
    description: str
    scam_type: str
    severity: Literal["critical", "high", "medium", "low"]
    amount_involved: Optional[float] = None
    location: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    admin_key: str


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time scam alerts
    Clients connect here to receive live updates
    """
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "Connected to EchoFort Live Alerts",
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive
        while True:
            # Wait for client messages (ping/pong)
            data = await websocket.receive_text()
            
            # Echo back (ping/pong)
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.post("/publish")
async def publish_alert(request: Request, payload: ScamAlert):
    """
    Admin endpoint to publish live scam alert
    Broadcasts to all connected clients
    """
    try:
        # Verify admin key
        import os
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if payload.admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        db = request.app.state.db
        
        # Save alert to database
        insert_query = text("""
            INSERT INTO live_scam_alerts (
                title, description, scam_type, severity,
                amount_involved, location, source_url, source_name,
                is_active, published_at, expires_at, created_at
            ) VALUES (
                :title, :desc, :type, :severity,
                :amount, :loc, :url, :source,
                TRUE, NOW(), NOW() + INTERVAL '7 days', NOW()
            ) RETURNING id
        """)
        
        result = await db.execute(insert_query, {
            "title": payload.title,
            "desc": payload.description,
            "type": payload.scam_type,
            "severity": payload.severity,
            "amount": payload.amount_involved,
            "loc": payload.location,
            "url": payload.source_url,
            "source": payload.source_name
        })
        
        alert_id = result.fetchone()[0]
        
        # Broadcast to all connected clients
        alert_message = {
            "type": "scam_alert",
            "alert_id": alert_id,
            "title": payload.title,
            "description": payload.description,
            "scam_type": payload.scam_type,
            "severity": payload.severity,
            "amount_involved": payload.amount_involved,
            "location": payload.location,
            "source_url": payload.source_url,
            "source_name": payload.source_name,
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.broadcast(json.dumps(alert_message))
        
        return {
            "ok": True,
            "alert_id": alert_id,
            "message": "Alert published and broadcasted",
            "active_connections": len(manager.active_connections),
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Publish error: {str(e)}")


@router.get("/recent")
async def get_recent_alerts(request: Request, limit: int = 20, severity: Optional[str] = None):
    """
    Get recent scam alerts (REST endpoint)
    """
    try:
        db = request.app.state.db
        
        if severity:
            query = text("""
                SELECT 
                    id, title, description, scam_type, severity,
                    amount_involved, location, source_url, source_name,
                    published_at, view_count
                FROM live_scam_alerts
                WHERE is_active = TRUE AND severity = :sev
                ORDER BY published_at DESC
                LIMIT :lim
            """)
            alerts = (await db.execute(query, {"sev": severity, "lim": limit})).fetchall()
        else:
            query = text("""
                SELECT 
                    id, title, description, scam_type, severity,
                    amount_involved, location, source_url, source_name,
                    published_at, view_count
                FROM live_scam_alerts
                WHERE is_active = TRUE
                ORDER BY published_at DESC
                LIMIT :lim
            """)
            alerts = (await db.execute(query, {"lim": limit})).fetchall()
        
        return {
            "ok": True,
            "total": len(alerts),
            "alerts": [
                {
                    "alert_id": a[0],
                    "title": a[1],
                    "description": a[2],
                    "scam_type": a[3],
                    "severity": a[4],
                    "amount_involved": float(a[5]) if a[5] else None,
                    "location": a[6],
                    "source_url": a[7],
                    "source_name": a[8],
                    "published_at": str(a[9]),
                    "view_count": a[10]
                }
                for a in alerts
            ]
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error fetching alerts: {str(e)}")


@router.get("/stats")
async def get_alert_stats(request: Request):
    """
    Get live alert statistics
    """
    try:
        db = request.app.state.db
        
        stats_query = text("""
            SELECT 
                COUNT(*) as total_alerts,
                COUNT(*) FILTER (WHERE severity = 'critical') as critical_alerts,
                COUNT(*) FILTER (WHERE severity = 'high') as high_alerts,
                COUNT(*) FILTER (WHERE published_at > NOW() - INTERVAL '24 hours') as alerts_24h,
                SUM(view_count) as total_views
            FROM live_scam_alerts
            WHERE is_active = TRUE
        """)
        
        stats = (await db.execute(stats_query)).fetchone()
        
        return {
            "ok": True,
            "stats": {
                "total_active_alerts": stats[0] or 0,
                "critical_alerts": stats[1] or 0,
                "high_alerts": stats[2] or 0,
                "alerts_last_24h": stats[3] or 0,
                "total_views": stats[4] or 0,
                "active_websocket_connections": len(manager.active_connections)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(500, f"Stats error: {str(e)}")


@router.post("/mark-viewed/{alert_id}")
async def mark_alert_viewed(request: Request, alert_id: int):
    """
    Increment view count for alert
    """
    try:
        db = request.app.state.db
        
        update_query = text("""
            UPDATE live_scam_alerts
            SET view_count = view_count + 1
            WHERE id = :aid
        """)
        
        await db.execute(update_query, {"aid": alert_id})
        
        return {
            "ok": True,
            "alert_id": alert_id,
            "message": "View count updated"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Update error: {str(e)}")


@router.delete("/deactivate/{alert_id}")
async def deactivate_alert(request: Request, alert_id: int, admin_key: str):
    """
    Admin endpoint to deactivate an alert
    """
    try:
        import os
        expected_key = os.getenv("ADMIN_KEY", "EchoFortSuperAdmin2025")
        if admin_key != expected_key:
            raise HTTPException(403, "Invalid admin key")
        
        db = request.app.state.db
        
        update_query = text("""
            UPDATE live_scam_alerts
            SET is_active = FALSE
            WHERE id = :aid
        """)
        
        await db.execute(update_query, {"aid": alert_id})
        
        return {
            "ok": True,
            "alert_id": alert_id,
            "message": "Alert deactivated"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Deactivation error: {str(e)}")

