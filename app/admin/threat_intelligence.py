"""
Threat Intelligence API Endpoints - Block 15
Admin routes for managing threat intelligence system
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import json
import asyncio

from app.database import get_db
from app.threat_intelligence_scanner import ThreatIntelligenceScanner, run_scheduled_scan

router = APIRouter(prefix="/admin/threat-intel", tags=["Threat Intelligence"])


@router.get("/scans")
async def list_scans(
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List threat intelligence scans
    
    Query Parameters:
    - limit: Maximum number of scans to return (default: 20, max: 100)
    - status: Filter by scan status (running, completed, failed)
    - source: Filter by scan source
    """
    try:
        conditions = []
        params = {"limit": limit}
        
        if status:
            conditions.append("scan_status = :status")
            params["status"] = status
        
        if source:
            conditions.append("scan_source LIKE :source")
            params["source"] = f"%{source}%"
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = text(f"""
            SELECT 
                id, scan_timestamp, scan_source, scan_status,
                items_collected, new_patterns_detected, scan_duration_seconds,
                error_message, created_at, completed_at
            FROM threat_intelligence_scans
            WHERE {where_clause}
            ORDER BY scan_timestamp DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, params)
        scans = [dict(row._mapping) for row in result]
        
        return {
            "success": True,
            "scans": scans,
            "count": len(scans)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch scans: {str(e)}")


@router.post("/scans/trigger")
async def trigger_manual_scan(
    source_type: Optional[str] = Query(None, description="Specific source type to scan"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a threat intelligence scan
    
    Query Parameters:
    - source_type: Optional specific source type to scan (twitter, news, government, reddit)
    """
    try:
        # Run scan in background
        result = await run_scheduled_scan()
        
        return {
            "success": True,
            "message": "Scan triggered successfully",
            "result": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger scan: {str(e)}")


@router.get("/items")
async def list_threat_items(
    limit: int = Query(50, ge=1, le=200),
    scam_type: Optional[str] = Query(None),
    min_severity: Optional[int] = Query(None, ge=1, le=10),
    verified_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    List collected threat intelligence items
    
    Query Parameters:
    - limit: Maximum number of items to return (default: 50, max: 200)
    - scam_type: Filter by scam type
    - min_severity: Minimum severity score (1-10)
    - verified_only: Only show verified items
    """
    try:
        conditions = []
        params = {"limit": limit}
        
        if scam_type:
            conditions.append("scam_type = :scam_type")
            params["scam_type"] = scam_type
        
        if min_severity:
            conditions.append("severity_score >= :min_severity")
            params["min_severity"] = min_severity
        
        if verified_only:
            conditions.append("is_verified = TRUE")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = text(f"""
            SELECT 
                id, scan_id, source_url, source_type, content_text,
                content_summary, extracted_phone_numbers, extracted_urls,
                extracted_keywords, scam_type, severity_score, confidence_score,
                geographic_context, is_verified, is_false_positive, created_at
            FROM threat_intelligence_items
            WHERE {where_clause}
            ORDER BY created_at DESC, severity_score DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, params)
        items = []
        
        for row in result:
            item = dict(row._mapping)
            # Parse JSONB fields
            item['extracted_phone_numbers'] = json.loads(item['extracted_phone_numbers'] or '[]')
            item['extracted_urls'] = json.loads(item['extracted_urls'] or '[]')
            item['extracted_keywords'] = json.loads(item['extracted_keywords'] or '[]')
            items.append(item)
        
        return {
            "success": True,
            "items": items,
            "count": len(items)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch items: {str(e)}")


@router.post("/items/{item_id}/verify")
async def verify_threat_item(
    item_id: int,
    is_valid: bool = Query(..., description="Is this a valid threat?"),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Verify or mark a threat intelligence item as false positive
    
    Path Parameters:
    - item_id: ID of the threat item
    
    Query Parameters:
    - is_valid: True if valid threat, False if false positive
    - notes: Optional verification notes
    """
    try:
        query = text("""
            UPDATE threat_intelligence_items
            SET 
                is_verified = TRUE,
                is_false_positive = :is_false_positive,
                verified_at = CURRENT_TIMESTAMP
            WHERE id = :item_id
            RETURNING id
        """)
        
        result = db.execute(query, {
            "item_id": item_id,
            "is_false_positive": not is_valid
        })
        
        if not result.first():
            raise HTTPException(status_code=404, detail="Threat item not found")
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Item marked as {'valid threat' if is_valid else 'false positive'}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to verify item: {str(e)}")


@router.get("/patterns")
async def list_threat_patterns(
    limit: int = Query(50, ge=1, le=100),
    pattern_type: Optional[str] = Query(None),
    scam_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    List detected threat patterns
    
    Query Parameters:
    - limit: Maximum number of patterns to return (default: 50, max: 100)
    - pattern_type: Filter by pattern type
    - scam_type: Filter by scam type
    - active_only: Only show active patterns (default: true)
    """
    try:
        conditions = []
        params = {"limit": limit}
        
        if pattern_type:
            conditions.append("pattern_type = :pattern_type")
            params["pattern_type"] = pattern_type
        
        if scam_type:
            conditions.append("scam_type = :scam_type")
            params["scam_type"] = scam_type
        
        if active_only:
            conditions.append("is_active = TRUE")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = text(f"""
            SELECT 
                id, pattern_type, pattern_name, pattern_description, pattern_data,
                scam_type, severity_level, confidence_score, first_seen, last_seen,
                occurrence_count, affected_users_count, is_active, is_auto_block,
                created_at, updated_at
            FROM threat_patterns
            WHERE {where_clause}
            ORDER BY last_seen DESC, occurrence_count DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, params)
        patterns = []
        
        for row in result:
            pattern = dict(row._mapping)
            # Parse JSONB field
            pattern['pattern_data'] = json.loads(pattern['pattern_data'] or '{}')
            patterns.append(pattern)
        
        return {
            "success": True,
            "patterns": patterns,
            "count": len(patterns)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch patterns: {str(e)}")


@router.post("/patterns/{pattern_id}/toggle")
async def toggle_pattern_status(
    pattern_id: int,
    is_active: bool = Query(..., description="Activate or deactivate pattern"),
    db: Session = Depends(get_db)
):
    """
    Activate or deactivate a threat pattern
    
    Path Parameters:
    - pattern_id: ID of the pattern
    
    Query Parameters:
    - is_active: True to activate, False to deactivate
    """
    try:
        query = text("""
            UPDATE threat_patterns
            SET 
                is_active = :is_active,
                updated_at = CURRENT_TIMESTAMP,
                deactivated_at = CASE WHEN :is_active = FALSE THEN CURRENT_TIMESTAMP ELSE NULL END
            WHERE id = :pattern_id
            RETURNING id
        """)
        
        result = db.execute(query, {
            "pattern_id": pattern_id,
            "is_active": is_active
        })
        
        if not result.first():
            raise HTTPException(status_code=404, detail="Pattern not found")
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Pattern {'activated' if is_active else 'deactivated'} successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to toggle pattern: {str(e)}")


@router.get("/alerts")
async def list_threat_alerts(
    limit: int = Query(20, ge=1, le=100),
    alert_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    unacknowledged_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    List threat alerts
    
    Query Parameters:
    - limit: Maximum number of alerts to return (default: 20, max: 100)
    - alert_type: Filter by alert type
    - severity: Filter by severity (low, medium, high, critical)
    - unacknowledged_only: Only show unacknowledged alerts
    """
    try:
        conditions = []
        params = {"limit": limit}
        
        if alert_type:
            conditions.append("alert_type = :alert_type")
            params["alert_type"] = alert_type
        
        if severity:
            conditions.append("alert_severity = :severity")
            params["severity"] = severity
        
        if unacknowledged_only:
            conditions.append("is_acknowledged = FALSE")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = text(f"""
            SELECT 
                a.id, a.pattern_id, a.alert_type, a.alert_title, a.alert_message,
                a.alert_severity, a.affected_users_count, a.recommended_actions,
                a.alert_metadata, a.is_acknowledged, a.is_resolved,
                a.created_at, a.acknowledged_at, a.resolved_at,
                p.pattern_name, p.scam_type
            FROM threat_alerts a
            LEFT JOIN threat_patterns p ON a.pattern_id = p.id
            WHERE {where_clause}
            ORDER BY a.created_at DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, params)
        alerts = []
        
        for row in result:
            alert = dict(row._mapping)
            # Parse JSONB fields
            alert['recommended_actions'] = json.loads(alert['recommended_actions'] or '[]')
            alert['alert_metadata'] = json.loads(alert['alert_metadata'] or '{}')
            alerts.append(alert)
        
        return {
            "success": True,
            "alerts": alerts,
            "count": len(alerts)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch alerts: {str(e)}")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Acknowledge a threat alert
    
    Path Parameters:
    - alert_id: ID of the alert
    
    Query Parameters:
    - notes: Optional acknowledgment notes
    """
    try:
        query = text("""
            UPDATE threat_alerts
            SET 
                is_acknowledged = TRUE,
                acknowledged_at = CURRENT_TIMESTAMP
            WHERE id = :alert_id
            RETURNING id
        """)
        
        result = db.execute(query, {"alert_id": alert_id})
        
        if not result.first():
            raise HTTPException(status_code=404, detail="Alert not found")
        
        db.commit()
        
        return {
            "success": True,
            "message": "Alert acknowledged successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    resolution_notes: str = Query(..., description="Resolution notes"),
    db: Session = Depends(get_db)
):
    """
    Resolve a threat alert
    
    Path Parameters:
    - alert_id: ID of the alert
    
    Query Parameters:
    - resolution_notes: Notes describing how the alert was resolved
    """
    try:
        query = text("""
            UPDATE threat_alerts
            SET 
                is_resolved = TRUE,
                resolved_at = CURRENT_TIMESTAMP,
                resolution_notes = :notes
            WHERE id = :alert_id
            RETURNING id
        """)
        
        result = db.execute(query, {
            "alert_id": alert_id,
            "notes": resolution_notes
        })
        
        if not result.first():
            raise HTTPException(status_code=404, detail="Alert not found")
        
        db.commit()
        
        return {
            "success": True,
            "message": "Alert resolved successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}")


@router.get("/sources")
async def list_threat_sources(
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    List configured threat intelligence sources
    
    Query Parameters:
    - enabled_only: Only show enabled sources
    """
    try:
        condition = "WHERE is_enabled = TRUE" if enabled_only else ""
        
        query = text(f"""
            SELECT 
                id, source_name, source_type, source_url, is_enabled,
                scan_frequency_hours, last_scan_at, last_scan_status,
                success_rate, total_scans, total_items_collected,
                created_at, updated_at
            FROM threat_intel_sources
            {condition}
            ORDER BY source_name
        """)
        
        result = db.execute(query)
        sources = [dict(row._mapping) for row in result]
        
        return {
            "success": True,
            "sources": sources,
            "count": len(sources)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sources: {str(e)}")


@router.post("/sources/{source_id}/toggle")
async def toggle_source_status(
    source_id: int,
    is_enabled: bool = Query(..., description="Enable or disable source"),
    db: Session = Depends(get_db)
):
    """
    Enable or disable a threat intelligence source
    
    Path Parameters:
    - source_id: ID of the source
    
    Query Parameters:
    - is_enabled: True to enable, False to disable
    """
    try:
        query = text("""
            UPDATE threat_intel_sources
            SET 
                is_enabled = :is_enabled,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :source_id
            RETURNING id
        """)
        
        result = db.execute(query, {
            "source_id": source_id,
            "is_enabled": is_enabled
        })
        
        if not result.first():
            raise HTTPException(status_code=404, detail="Source not found")
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Source {'enabled' if is_enabled else 'disabled'} successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to toggle source: {str(e)}")


@router.get("/stats")
async def get_threat_intel_stats(
    days: int = Query(30, ge=1, le=90, description="Number of days to include in stats"),
    db: Session = Depends(get_db)
):
    """
    Get threat intelligence statistics
    
    Query Parameters:
    - days: Number of days to include (default: 30, max: 90)
    """
    try:
        # Overall stats
        overall_query = text("""
            SELECT 
                COUNT(*) as total_scans,
                SUM(items_collected) as total_items,
                (SELECT COUNT(*) FROM threat_patterns WHERE is_active = TRUE) as active_patterns,
                (SELECT COUNT(*) FROM threat_alerts WHERE is_acknowledged = FALSE) as pending_alerts
            FROM threat_intelligence_scans
            WHERE scan_timestamp > CURRENT_TIMESTAMP - INTERVAL ':days days'
        """)
        
        overall_result = db.execute(overall_query, {"days": days}).first()
        
        # Daily stats
        daily_query = text("""
            SELECT 
                stat_date, total_scans, successful_scans, failed_scans,
                total_items_collected, new_patterns_detected, alerts_generated,
                top_scam_types, top_sources
            FROM threat_intel_statistics
            WHERE stat_date > CURRENT_DATE - INTERVAL ':days days'
            ORDER BY stat_date DESC
        """)
        
        daily_result = db.execute(daily_query, {"days": days})
        daily_stats = []
        
        for row in daily_result:
            stat = dict(row._mapping)
            stat['top_scam_types'] = json.loads(stat['top_scam_types'] or '[]')
            stat['top_sources'] = json.loads(stat['top_sources'] or '[]')
            daily_stats.append(stat)
        
        # Scam type distribution
        scam_type_query = text("""
            SELECT scam_type, COUNT(*) as count
            FROM threat_intelligence_items
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL ':days days'
            AND scam_type IS NOT NULL
            GROUP BY scam_type
            ORDER BY count DESC
        """)
        
        scam_type_result = db.execute(scam_type_query, {"days": days})
        scam_types = [dict(row._mapping) for row in scam_type_result]
        
        return {
            "success": True,
            "stats": {
                "overall": dict(overall_result._mapping) if overall_result else {},
                "daily": daily_stats,
                "scam_type_distribution": scam_types
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@router.get("/stats/dashboard")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get high-level dashboard statistics for threat intelligence"""
    try:
        query = text("""
            SELECT 
                (SELECT COUNT(*) FROM threat_intelligence_scans WHERE scan_status = 'completed' AND scan_timestamp > CURRENT_TIMESTAMP - INTERVAL '7 days') as scans_last_7_days,
                (SELECT COUNT(*) FROM threat_intelligence_items WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days') as items_last_7_days,
                (SELECT COUNT(*) FROM threat_patterns WHERE is_active = TRUE) as active_patterns,
                (SELECT COUNT(*) FROM threat_alerts WHERE is_acknowledged = FALSE) as pending_alerts,
                (SELECT COUNT(*) FROM threat_alerts WHERE is_resolved = FALSE) as unresolved_alerts,
                (SELECT scam_type FROM threat_intelligence_items WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days' AND scam_type IS NOT NULL GROUP BY scam_type ORDER BY COUNT(*) DESC LIMIT 1) as top_scam_type_7_days,
                (SELECT AVG(severity_score) FROM threat_intelligence_items WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days') as avg_severity_7_days
        """)
        
        result = db.execute(query).first()
        
        return {
            "success": True,
            "dashboard": dict(result._mapping) if result else {}
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard stats: {str(e)}")
