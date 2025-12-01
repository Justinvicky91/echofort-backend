"""
EchoShell READ Tools - Safe commands that don't require human approval

These tools provide EchoFort AI with deep visibility into the platform
without the ability to make changes. All tools are read-only and safe to execute.
"""

import psycopg
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os

# Database connection
def get_db_connection():
    """Get database connection from environment"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not configured")
    return psycopg.connect(database_url)


# ============================================================================
# METRICS & HEALTH TOOLS
# ============================================================================

def get_system_health() -> Dict[str, Any]:
    """
    Get comprehensive system health status
    
    Returns:
        dict: System health metrics including database, API, and service status
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check database connectivity
        cursor.execute("SELECT 1")
        db_status = "connected"
        
        # Get recent error count
        cursor.execute("""
            SELECT COUNT(*) FROM error_logs 
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """)
        recent_errors = cursor.fetchone()[0]
        
        # Get active sessions
        cursor.execute("""
            SELECT COUNT(*) FROM pg_stat_activity 
            WHERE state = 'active'
        """)
        active_connections = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "status": "healthy" if recent_errors < 10 else "degraded",
            "database": db_status,
            "api": "operational",
            "recent_errors_1h": recent_errors,
            "active_db_connections": active_connections,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def get_error_logs(limit: int = 50, severity: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get recent error logs
    
    Args:
        limit: Maximum number of logs to return (default: 50)
        severity: Filter by severity (critical, error, warning)
    
    Returns:
        list: Recent error logs
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, severity, message, context, created_at
            FROM error_logs
            WHERE 1=1
        """
        params = []
        
        if severity:
            query += " AND severity = %s"
            params.append(severity)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "severity": row[1],
                "message": row[2],
                "context": row[3],
                "created_at": row[4].isoformat() if row[4] else None
            })
        
        cursor.close()
        conn.close()
        
        return logs
    except Exception as e:
        return [{"error": str(e)}]


def get_api_metrics(hours: int = 24) -> Dict[str, Any]:
    """
    Get API usage metrics
    
    Args:
        hours: Number of hours to look back (default: 24)
    
    Returns:
        dict: API metrics including request count, error rate, response times
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total requests
        cursor.execute("""
            SELECT COUNT(*) FROM error_logs
            WHERE created_at > NOW() - INTERVAL '%s hours'
        """, (hours,))
        total_errors = cursor.fetchone()[0]
        
        # Get errors by severity
        cursor.execute("""
            SELECT severity, COUNT(*) 
            FROM error_logs
            WHERE created_at > NOW() - INTERVAL '%s hours'
            GROUP BY severity
        """, (hours,))
        errors_by_severity = dict(cursor.fetchall())
        
        cursor.close()
        conn.close()
        
        return {
            "time_window_hours": hours,
            "total_errors": total_errors,
            "errors_by_severity": errors_by_severity,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# BUSINESS METRICS TOOLS
# ============================================================================

def get_user_stats() -> Dict[str, Any]:
    """
    Get user statistics
    
    Returns:
        dict: User metrics including total, active, by plan type
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # Active users (logged in last 30 days)
        cursor.execute("""
            SELECT COUNT(*) FROM users
            WHERE last_login > NOW() - INTERVAL '30 days'
        """)
        active_users = cursor.fetchone()[0]
        
        # Users by plan
        cursor.execute("""
            SELECT plan_type, COUNT(*)
            FROM subscriptions
            WHERE status = 'active'
            GROUP BY plan_type
        """)
        users_by_plan = dict(cursor.fetchall())
        
        cursor.close()
        conn.close()
        
        return {
            "total_users": total_users,
            "active_users_30d": active_users,
            "users_by_plan": users_by_plan,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


def get_subscription_stats() -> Dict[str, Any]:
    """
    Get subscription statistics
    
    Returns:
        dict: Subscription metrics including active, churned, revenue
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Active subscriptions
        cursor.execute("""
            SELECT COUNT(*) FROM subscriptions
            WHERE status = 'active'
        """)
        active_subs = cursor.fetchone()[0]
        
        # Subscriptions by plan
        cursor.execute("""
            SELECT plan_type, COUNT(*)
            FROM subscriptions
            WHERE status = 'active'
            GROUP BY plan_type
        """)
        subs_by_plan = dict(cursor.fetchall())
        
        # Monthly recurring revenue (MRR)
        cursor.execute("""
            SELECT SUM(amount) FROM subscriptions
            WHERE status = 'active'
        """)
        mrr = cursor.fetchone()[0] or 0
        
        cursor.close()
        conn.close()
        
        return {
            "active_subscriptions": active_subs,
            "subscriptions_by_plan": subs_by_plan,
            "mrr": float(mrr),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


def get_revenue_metrics(days: int = 30) -> Dict[str, Any]:
    """
    Get revenue metrics
    
    Args:
        days: Number of days to look back (default: 30)
    
    Returns:
        dict: Revenue metrics including total, by plan, growth
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total revenue in period
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM invoices
            WHERE status = 'paid'
            AND created_at > NOW() - INTERVAL '%s days'
        """, (days,))
        total_revenue = cursor.fetchone()[0]
        
        # Revenue by plan
        cursor.execute("""
            SELECT s.plan_type, COALESCE(SUM(i.amount), 0)
            FROM invoices i
            JOIN subscriptions s ON i.subscription_id = s.id
            WHERE i.status = 'paid'
            AND i.created_at > NOW() - INTERVAL '%s days'
            GROUP BY s.plan_type
        """, (days,))
        revenue_by_plan = dict(cursor.fetchall())
        
        cursor.close()
        conn.close()
        
        return {
            "time_window_days": days,
            "total_revenue": float(total_revenue),
            "revenue_by_plan": {k: float(v) for k, v in revenue_by_plan.items()},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# THREAT INTELLIGENCE TOOLS
# ============================================================================

def get_scam_patterns(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent scam patterns
    
    Args:
        limit: Maximum number of patterns to return (default: 20)
    
    Returns:
        list: Recent scam patterns with details
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, risk_level, example_phrases, 
                   source_url, reported_at
            FROM threat_intelligence_patterns
            ORDER BY reported_at DESC
            LIMIT %s
        """, (limit,))
        
        rows = cursor.fetchall()
        patterns = []
        for row in rows:
            patterns.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "risk_level": row[3],
                "example_phrases": row[4],
                "source_url": row[5],
                "reported_at": row[6].isoformat() if row[6] else None
            })
        
        cursor.close()
        conn.close()
        
        return patterns
    except Exception as e:
        return [{"error": str(e)}]


def get_scam_alerts(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get live scam alerts
    
    Args:
        limit: Maximum number of alerts to return (default: 10)
    
    Returns:
        list: Recent scam alerts
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, description, severity, location, 
                   reported_count, created_at
            FROM live_scam_alerts
            WHERE is_active = true
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        
        rows = cursor.fetchall()
        alerts = []
        for row in rows:
            alerts.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "severity": row[3],
                "location": row[4],
                "reported_count": row[5],
                "created_at": row[6].isoformat() if row[6] else None
            })
        
        cursor.close()
        conn.close()
        
        return alerts
    except Exception as e:
        return [{"error": str(e)}]


def get_threat_stats() -> Dict[str, Any]:
    """
    Get threat intelligence statistics
    
    Returns:
        dict: Threat statistics including total patterns, alerts, cases
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total patterns
        cursor.execute("SELECT COUNT(*) FROM threat_intelligence_patterns")
        total_patterns = cursor.fetchone()[0]
        
        # Active alerts
        cursor.execute("""
            SELECT COUNT(*) FROM live_scam_alerts
            WHERE is_active = true
        """)
        active_alerts = cursor.fetchone()[0]
        
        # Scam cases by status
        cursor.execute("""
            SELECT COUNT(*) FROM scam_cases
        """)
        total_cases = cursor.fetchone()[0]
        
        # High-risk patterns
        cursor.execute("""
            SELECT COUNT(*) FROM threat_intelligence_patterns
            WHERE risk_level IN ('high', 'critical')
        """)
        high_risk_patterns = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "total_patterns": total_patterns,
            "active_alerts": active_alerts,
            "total_cases": total_cases,
            "high_risk_patterns": high_risk_patterns,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# CONFIG & SETTINGS TOOLS (READ-ONLY)
# ============================================================================

def get_feature_flags() -> List[Dict[str, Any]]:
    """
    Get all feature flags (read-only)
    
    Returns:
        list: All feature flags with their current state
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT flag_key, flag_value, description, updated_at
            FROM feature_flags
            ORDER BY flag_key
        """)
        
        rows = cursor.fetchall()
        flags = []
        for row in rows:
            flags.append({
                "flag_key": row[0],
                "flag_value": row[1],
                "description": row[2],
                "updated_at": row[3].isoformat() if row[3] else None
            })
        
        cursor.close()
        conn.close()
        
        return flags
    except Exception as e:
        return [{"error": str(e)}]


def get_app_config() -> List[Dict[str, Any]]:
    """
    Get all app configuration (read-only)
    
    Returns:
        list: All app config entries
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT config_key, config_value, description, updated_at
            FROM app_config
            ORDER BY config_key
        """)
        
        rows = cursor.fetchall()
        config = []
        for row in rows:
            config.append({
                "config_key": row[0],
                "config_value": row[1],
                "description": row[2],
                "updated_at": row[3].isoformat() if row[3] else None
            })
        
        cursor.close()
        conn.close()
        
        return config
    except Exception as e:
        return [{"error": str(e)}]


# ============================================================================
# TOOL REGISTRY
# ============================================================================

ECHOSHELL_READ_TOOLS = {
    # Metrics & Health
    "get_system_health": {
        "function": get_system_health,
        "description": "Get comprehensive system health status including database, API, and error metrics",
        "parameters": {}
    },
    "get_error_logs": {
        "function": get_error_logs,
        "description": "Get recent error logs with optional severity filter",
        "parameters": {
            "limit": {"type": "integer", "description": "Maximum number of logs to return (default: 50)"},
            "severity": {"type": "string", "description": "Filter by severity: critical, error, warning"}
        }
    },
    "get_api_metrics": {
        "function": get_api_metrics,
        "description": "Get API usage metrics including error rates and response times",
        "parameters": {
            "hours": {"type": "integer", "description": "Number of hours to look back (default: 24)"}
        }
    },
    
    # Business Metrics
    "get_user_stats": {
        "function": get_user_stats,
        "description": "Get user statistics including total, active, and by plan type",
        "parameters": {}
    },
    "get_subscription_stats": {
        "function": get_subscription_stats,
        "description": "Get subscription statistics including active, by plan, and MRR",
        "parameters": {}
    },
    "get_revenue_metrics": {
        "function": get_revenue_metrics,
        "description": "Get revenue metrics including total, by plan, and growth",
        "parameters": {
            "days": {"type": "integer", "description": "Number of days to look back (default: 30)"}
        }
    },
    
    # Threat Intelligence
    "get_scam_patterns": {
        "function": get_scam_patterns,
        "description": "Get recent scam patterns with details",
        "parameters": {
            "limit": {"type": "integer", "description": "Maximum number of patterns to return (default: 20)"}
        }
    },
    "get_scam_alerts": {
        "function": get_scam_alerts,
        "description": "Get live scam alerts",
        "parameters": {
            "limit": {"type": "integer", "description": "Maximum number of alerts to return (default: 10)"}
        }
    },
    "get_threat_stats": {
        "function": get_threat_stats,
        "description": "Get threat intelligence statistics",
        "parameters": {}
    },
    
    # Config & Settings (Read-Only)
    "get_feature_flags": {
        "function": get_feature_flags,
        "description": "Get all feature flags (read-only)",
        "parameters": {}
    },
    "get_app_config": {
        "function": get_app_config,
        "description": "Get all app configuration (read-only)",
        "parameters": {}
    }
}
