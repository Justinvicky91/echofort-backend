"""
Threat Intelligence API Endpoints - Block 15 v2
Admin routes for managing threat intelligence system
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import os

from app.threat_intelligence_scanner import ThreatIntelligenceScanner, run_threat_intelligence_scan

router = APIRouter(prefix="/admin/threat-intel", tags=["Threat Intelligence"])
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection using DATABASE_URL environment variable"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))


@router.get("/scans")
async def list_scans(
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None)
):
    """
    List threat intelligence scans
    
    Query Parameters:
    - limit: Maximum number of scans to return (default: 20, max: 100)
    - status: Filter by scan status (in_progress, completed, failed)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT id, scan_status, scan_timestamp, completed_at, 
                   items_collected, new_patterns_detected
            FROM threat_intelligence_scans
        """
        
        if status:
            query += " WHERE scan_status = %s"
            cur.execute(query + " ORDER BY scan_timestamp DESC LIMIT %s", (status, limit))
        else:
            cur.execute(query + " ORDER BY scan_timestamp DESC LIMIT %s", (limit,))
        
        scans = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {"scans": scans, "count": len(scans)}
        
    except Exception as e:
        logger.error(f"Error listing scans: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scans/trigger")
async def trigger_scan():
    """Manually trigger a threat intelligence scan"""
    try:
        result = run_threat_intelligence_scan()
        return {"message": "Scan triggered successfully", "result": result}
    except Exception as e:
        logger.error(f"Error triggering scan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items")
async def list_threat_items(
    limit: int = Query(50, ge=1, le=200),
    scam_type: Optional[str] = Query(None),
    min_severity: Optional[int] = Query(None, ge=1, le=10)
):
    """
    List threat intelligence items
    
    Query Parameters:
    - limit: Maximum number of items to return (default: 50, max: 200)
    - scam_type: Filter by scam type
    - min_severity: Filter by minimum severity_score (1-10)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        conditions = []
        params = []
        
        if scam_type:
            conditions.append("scam_type = %s")
            params.append(scam_type)
        
        if min_severity:
            conditions.append("severity_score >= %s")
            params.append(min_severity)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT id, scan_id, source_id, scam_type, severity_score, 
                   confidence_score, phone_numbers, urls, keywords, created_at
            FROM threat_intelligence_items
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        params.append(limit)
        cur.execute(query, tuple(params))
        
        items = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {"items": items, "count": len(items)}
        
    except Exception as e:
        logger.error(f"Error listing items: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns")
async def list_patterns(
    limit: int = Query(50, ge=1, le=200),
    pattern_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    """
    List detected threat patterns
    
    Query Parameters:
    - limit: Maximum number of patterns to return (default: 50, max: 200)
    - pattern_type: Filter by pattern type (phone_number, url, keyword)
    - is_active: Filter by active status
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        conditions = []
        params = []
        
        if pattern_type:
            conditions.append("pattern_type = %s")
            params.append(pattern_type)
        
        if is_active is not None:
            conditions.append("is_active = %s")
            params.append(is_active)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT id, pattern_type, pattern_name, occurrence_count, 
                   scam_types, first_seen, last_seen, is_active
            FROM threat_patterns
            {where_clause}
            ORDER BY occurrence_count DESC, last_seen DESC
            LIMIT %s
        """
        
        params.append(limit)
        cur.execute(query, tuple(params))
        
        patterns = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {"patterns": patterns, "count": len(patterns)}
        
    except Exception as e:
        logger.error(f"Error listing patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patterns/{pattern_id}/toggle")
async def toggle_pattern(pattern_id: int):
    """Toggle pattern active status"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            UPDATE threat_patterns
            SET is_active = NOT is_active
            WHERE id = %s
            RETURNING id, is_active
        """, (pattern_id,))
        
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Pattern not found")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"message": "Pattern status toggled", "pattern": result}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling pattern: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    min_severity: Optional[int] = Query(None, ge=1, le=10)
):
    """
    List threat alerts
    
    Query Parameters:
    - limit: Maximum number of alerts to return (default: 50, max: 200)
    - status: Filter by status (new, acknowledged, resolved)
    - min_severity: Filter by minimum severity_score (1-10)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        conditions = []
        params = []
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        
        if min_severity:
            conditions.append("severity_score >= %s")
            params.append(min_severity)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT id, alert_type, alert_severity, alert_title, alert_message, 
                   alert_metadata, created_at, acknowledged_at, resolved_at
            FROM threat_alerts
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        params.append(limit)
        cur.execute(query, tuple(params))
        
        alerts = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {"alerts": alerts, "count": len(alerts)}
        
    except Exception as e:
        logger.error(f"Error listing alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    """Acknowledge a threat alert"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            UPDATE threat_alerts
            SET is_acknowledged = true,
                acknowledged_at = CURRENT_TIMESTAMP
            WHERE id = %s AND is_acknowledged = false
            RETURNING id, is_acknowledged
        """, (alert_id,))
        
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"message": "Alert acknowledged", "alert": result}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """Resolve a threat alert"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            UPDATE threat_alerts
            SET is_resolved = true,
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = %s AND is_resolved = false
            RETURNING id, is_acknowledged
        """, (alert_id,))
        
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Alert not found or already resolved")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"message": "Alert resolved", "alert": result}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def list_sources():
    """List all threat intelligence sources"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, name, source_type, url, keywords, is_active, priority
            FROM threat_intel_sources
            ORDER BY priority DESC, name ASC
        """)
        
        sources = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {"sources": sources, "count": len(sources)}
        
    except Exception as e:
        logger.error(f"Error listing sources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/{source_id}/toggle")
async def toggle_source(source_id: int):
    """Toggle source active status"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            UPDATE threat_intel_sources
            SET is_active = NOT is_active
            WHERE id = %s
            RETURNING id, name, is_active
        """, (source_id,))
        
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Source not found")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"message": "Source status toggled", "source": result}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_statistics():
    """Get threat intelligence statistics"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get latest statistics
        cur.execute("""
            SELECT total_scans, total_items, total_patterns, total_alerts,
                   avg_severity_score, most_common_scam_type, stats_date
            FROM threat_intel_statistics
            ORDER BY stats_date DESC
            LIMIT 1
        """)
        
        latest_stats = cur.fetchone()
        
        # Get real-time counts
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE scan_status = 'in_progress') as active_scans,
                COUNT(*) FILTER (WHERE scan_status = 'completed') as completed_scans,
                COUNT(*) FILTER (WHERE scan_status = 'failed') as failed_scans
            FROM threat_intelligence_scans
        """)
        
        scan_stats = cur.fetchone()
        
        cur.execute("""
            SELECT COUNT(*) as active_patterns
            FROM threat_patterns
            WHERE is_active = true
        """)
        
        pattern_stats = cur.fetchone()
        
        cur.execute("""
            SELECT COUNT(*) as new_alerts
            FROM threat_alerts
            WHERE is_acknowledged = false AND is_resolved = false
        """)
        
        alert_stats = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return {
            "latest_statistics": latest_stats,
            "real_time": {
                "active_scans": scan_stats['active_scans'],
                "completed_scans": scan_stats['completed_scans'],
                "failed_scans": scan_stats['failed_scans'],
                "active_patterns": pattern_stats['active_patterns'],
                "new_alerts": alert_stats['new_alerts']
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard():
    """Get threat intelligence dashboard summary"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Recent scans
        cur.execute("""
            SELECT id, scan_status, scan_timestamp, completed_at, items_collected
            FROM threat_intelligence_scans
            ORDER BY scan_timestamp DESC
            LIMIT 5
        """)
        recent_scans = cur.fetchall()
        
        # High severity_score items
        cur.execute("""
            SELECT id, scam_type, severity_score, created_at
            FROM threat_intelligence_items
            WHERE severity_score >= 8
            ORDER BY created_at DESC
            LIMIT 10
        """)
        high_severity_items = cur.fetchall()
        
        # Active patterns
        cur.execute("""
            SELECT id, pattern_type, pattern_name, occurrence_count
            FROM threat_patterns
            WHERE is_active = true
            ORDER BY occurrence_count DESC
            LIMIT 10
        """)
        active_patterns = cur.fetchall()
        
        # New alerts
        cur.execute("""
            SELECT id, alert_type, alert_severity, alert_title, created_at
            FROM threat_alerts
            WHERE is_acknowledged = false AND is_resolved = false
            ORDER BY created_at DESC
            LIMIT 10
        """)
        new_alerts = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            "recent_scans": recent_scans,
            "high_severity_items": high_severity_items,
            "active_patterns": active_patterns,
            "new_alerts": new_alerts
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
