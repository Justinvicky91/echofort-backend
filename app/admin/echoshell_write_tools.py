"""
EchoShell WRITE Tools - Commands that require human approval

These tools allow EchoFort AI to propose impactful changes, but all changes
go through the AI Pending Actions queue for human approval. No automatic execution.
"""

import psycopg
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import os

# Database connection
def get_db_connection():
    """Get database connection from environment"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not configured")
    return psycopg.connect(database_url)


def create_ai_pending_action(
    action_type: str,
    payload: Dict[str, Any],
    summary: str,
    reason: str,
    created_by_user_id: int = 1,
    risk_level: str = "medium"
) -> Dict[str, Any]:
    """
    Create a pending action in the AI action queue
    
    Args:
        action_type: Type of action (e.g., UPDATE_USER, CREATE_SCAM_PATTERN)
        payload: Action payload as JSON
        summary: Human-readable summary
        reason: Detailed reason for the action
        created_by_user_id: User ID creating the action
        risk_level: Risk level (low, medium, high, critical)
    
    Returns:
        dict: Created action details
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ai_action_queue 
            (action_type, payload, status, created_by_user_id, source, summary, reason, risk_level)
            VALUES (%s, %s, 'PENDING', %s, 'EchoFort AI', %s, %s, %s)
            RETURNING id, action_type, status, created_at
        """, (action_type, json.dumps(payload), created_by_user_id, summary, reason, risk_level))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if result:
            return {
                "action_id": result[0],
                "action_type": result[1],
                "status": result[2],
                "created_at": result[3].isoformat() if result[3] else None,
                "message": f"Action #{result[0]} created and awaiting approval"
            }
        else:
            return {"error": "Failed to create action"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# USER MANAGEMENT WRITE TOOLS
# ============================================================================

def propose_user_refund(
    user_id: int,
    amount: float,
    reason: str,
    created_by_user_id: int = 1
) -> Dict[str, Any]:
    """
    Propose a refund for a user
    
    Args:
        user_id: User ID to refund
        amount: Refund amount
        reason: Reason for refund
        created_by_user_id: User ID proposing the action
    
    Returns:
        dict: Pending action details
    """
    return create_ai_pending_action(
        action_type="USER_REFUND",
        payload={
            "user_id": user_id,
            "amount": amount,
            "reason": reason
        },
        summary=f"Refund ₹{amount} to user #{user_id}",
        reason=reason,
        created_by_user_id=created_by_user_id,
        risk_level="high"
    )


def propose_user_plan_change(
    user_id: int,
    new_plan: str,
    reason: str,
    created_by_user_id: int = 1
) -> Dict[str, Any]:
    """
    Propose a plan change for a user
    
    Args:
        user_id: User ID
        new_plan: New plan type (free, basic, premium, family)
        reason: Reason for plan change
        created_by_user_id: User ID proposing the action
    
    Returns:
        dict: Pending action details
    """
    return create_ai_pending_action(
        action_type="USER_PLAN_CHANGE",
        payload={
            "user_id": user_id,
            "new_plan": new_plan,
            "reason": reason
        },
        summary=f"Change user #{user_id} plan to {new_plan}",
        reason=reason,
        created_by_user_id=created_by_user_id,
        risk_level="medium"
    )


def propose_user_ban(
    user_id: int,
    reason: str,
    duration_days: Optional[int] = None,
    created_by_user_id: int = 1
) -> Dict[str, Any]:
    """
    Propose banning a user
    
    Args:
        user_id: User ID to ban
        reason: Reason for ban
        duration_days: Ban duration in days (None = permanent)
        created_by_user_id: User ID proposing the action
    
    Returns:
        dict: Pending action details
    """
    return create_ai_pending_action(
        action_type="USER_BAN",
        payload={
            "user_id": user_id,
            "reason": reason,
            "duration_days": duration_days
        },
        summary=f"Ban user #{user_id} ({'permanent' if not duration_days else f'{duration_days} days'})",
        reason=reason,
        created_by_user_id=created_by_user_id,
        risk_level="critical"
    )


# ============================================================================
# THREAT INTELLIGENCE WRITE TOOLS
# ============================================================================

def propose_scam_pattern_create(
    name: str,
    description: str,
    risk_level: str,
    example_phrases: List[str],
    source_url: Optional[str] = None,
    created_by_user_id: int = 1
) -> Dict[str, Any]:
    """
    Propose creating a new scam pattern
    
    Args:
        name: Pattern name
        description: Pattern description
        risk_level: Risk level (low, medium, high, critical)
        example_phrases: Example phrases for detection
        source_url: Source URL for verification
        created_by_user_id: User ID proposing the action
    
    Returns:
        dict: Pending action details
    """
    return create_ai_pending_action(
        action_type="SCAM_PATTERN_CREATE",
        payload={
            "name": name,
            "description": description,
            "risk_level": risk_level,
            "example_phrases": example_phrases,
            "source_url": source_url
        },
        summary=f"Create scam pattern: {name}",
        reason=f"New {risk_level}-risk scam pattern detected from {source_url or 'AI analysis'}",
        created_by_user_id=created_by_user_id,
        risk_level="medium"
    )


def propose_scam_alert_create(
    title: str,
    description: str,
    severity: str,
    location: Optional[str] = None,
    created_by_user_id: int = 1
) -> Dict[str, Any]:
    """
    Propose creating a live scam alert
    
    Args:
        title: Alert title
        description: Alert description
        severity: Severity (low, medium, high, critical)
        location: Location (optional)
        created_by_user_id: User ID proposing the action
    
    Returns:
        dict: Pending action details
    """
    return create_ai_pending_action(
        action_type="SCAM_ALERT_CREATE",
        payload={
            "title": title,
            "description": description,
            "severity": severity,
            "location": location
        },
        summary=f"Create scam alert: {title}",
        reason=f"New {severity}-severity scam alert detected" + (f" in {location}" if location else ""),
        created_by_user_id=created_by_user_id,
        risk_level="high"
    )


# ============================================================================
# CONFIG & FEATURE FLAG WRITE TOOLS
# ============================================================================

def propose_feature_flag_toggle(
    flag_key: str,
    new_value: bool,
    reason: str,
    created_by_user_id: int = 1
) -> Dict[str, Any]:
    """
    Propose toggling a feature flag
    
    Args:
        flag_key: Feature flag key
        new_value: New value (true/false)
        reason: Reason for change
        created_by_user_id: User ID proposing the action
    
    Returns:
        dict: Pending action details
    """
    return create_ai_pending_action(
        action_type="FEATURE_FLAG_UPDATE",
        payload={
            "flag_key": flag_key,
            "new_value": new_value,
            "reason": reason
        },
        summary=f"Set feature flag '{flag_key}' to {new_value}",
        reason=reason,
        created_by_user_id=created_by_user_id,
        risk_level="medium"
    )


def propose_config_update(
    config_key: str,
    new_value: Any,
    reason: str,
    created_by_user_id: int = 1
) -> Dict[str, Any]:
    """
    Propose updating app configuration
    
    Args:
        config_key: Config key
        new_value: New value
        reason: Reason for change
        created_by_user_id: User ID proposing the action
    
    Returns:
        dict: Pending action details
    """
    return create_ai_pending_action(
        action_type="CONFIG_UPDATE",
        payload={
            "config_key": config_key,
            "new_value": new_value,
            "reason": reason
        },
        summary=f"Update config '{config_key}'",
        reason=reason,
        created_by_user_id=created_by_user_id,
        risk_level="high"
    )


# ============================================================================
# DATABASE OPERATIONS WRITE TOOLS
# ============================================================================

def propose_database_migration(
    migration_name: str,
    sql_script: str,
    reason: str,
    created_by_user_id: int = 1
) -> Dict[str, Any]:
    """
    Propose running a database migration
    
    Args:
        migration_name: Migration name
        sql_script: SQL script to execute
        reason: Reason for migration
        created_by_user_id: User ID proposing the action
    
    Returns:
        dict: Pending action details
    """
    return create_ai_pending_action(
        action_type="DATABASE_MIGRATION",
        payload={
            "migration_name": migration_name,
            "sql_script": sql_script,
            "reason": reason
        },
        summary=f"Run database migration: {migration_name}",
        reason=reason,
        created_by_user_id=created_by_user_id,
        risk_level="critical"
    )


def propose_data_cleanup(
    table_name: str,
    condition: str,
    reason: str,
    created_by_user_id: int = 1
) -> Dict[str, Any]:
    """
    Propose cleaning up data from a table
    
    Args:
        table_name: Table name
        condition: SQL WHERE condition
        reason: Reason for cleanup
        created_by_user_id: User ID proposing the action
    
    Returns:
        dict: Pending action details
    """
    return create_ai_pending_action(
        action_type="DATA_CLEANUP",
        payload={
            "table_name": table_name,
            "condition": condition,
            "reason": reason
        },
        summary=f"Clean up data from {table_name}",
        reason=reason,
        created_by_user_id=created_by_user_id,
        risk_level="high"
    )


# ============================================================================
# SYSTEM OPERATIONS WRITE TOOLS
# ============================================================================

def propose_service_restart(
    service_name: str,
    reason: str,
    created_by_user_id: int = 1
) -> Dict[str, Any]:
    """
    Propose restarting a service
    
    Args:
        service_name: Service name (web, frontend, postgres)
        reason: Reason for restart
        created_by_user_id: User ID proposing the action
    
    Returns:
        dict: Pending action details
    """
    return create_ai_pending_action(
        action_type="SERVICE_RESTART",
        payload={
            "service_name": service_name,
            "reason": reason
        },
        summary=f"Restart service: {service_name}",
        reason=reason,
        created_by_user_id=created_by_user_id,
        risk_level="high"
    )


def propose_deployment_rollback(
    service_name: str,
    target_version: str,
    reason: str,
    created_by_user_id: int = 1
) -> Dict[str, Any]:
    """
    Propose rolling back a deployment
    
    Args:
        service_name: Service name
        target_version: Target version to roll back to
        reason: Reason for rollback
        created_by_user_id: User ID proposing the action
    
    Returns:
        dict: Pending action details
    """
    return create_ai_pending_action(
        action_type="DEPLOYMENT_ROLLBACK",
        payload={
            "service_name": service_name,
            "target_version": target_version,
            "reason": reason
        },
        summary=f"Roll back {service_name} to {target_version}",
        reason=reason,
        created_by_user_id=created_by_user_id,
        risk_level="critical"
    )


# ============================================================================
# TOOL REGISTRY
# ============================================================================

ECHOSHELL_WRITE_TOOLS = {
    # User Management
    "propose_user_refund": {
        "function": propose_user_refund,
        "description": "Propose a refund for a user (requires approval)",
        "parameters": {
            "user_id": {"type": "integer", "description": "User ID to refund"},
            "amount": {"type": "number", "description": "Refund amount"},
            "reason": {"type": "string", "description": "Reason for refund"},
            "created_by_user_id": {"type": "integer", "description": "User ID proposing the action", "default": 1}
        }
    },
    "propose_user_plan_change": {
        "function": propose_user_plan_change,
        "description": "Propose a plan change for a user (requires approval)",
        "parameters": {
            "user_id": {"type": "integer", "description": "User ID"},
            "new_plan": {"type": "string", "description": "New plan type (free, basic, premium, family)"},
            "reason": {"type": "string", "description": "Reason for plan change"},
            "created_by_user_id": {"type": "integer", "description": "User ID proposing the action", "default": 1}
        }
    },
    "propose_user_ban": {
        "function": propose_user_ban,
        "description": "Propose banning a user (requires approval)",
        "parameters": {
            "user_id": {"type": "integer", "description": "User ID to ban"},
            "reason": {"type": "string", "description": "Reason for ban"},
            "duration_days": {"type": "integer", "description": "Ban duration in days (None = permanent)"},
            "created_by_user_id": {"type": "integer", "description": "User ID proposing the action", "default": 1}
        }
    },
    
    # Threat Intelligence
    "propose_scam_pattern_create": {
        "function": propose_scam_pattern_create,
        "description": "Propose creating a new scam pattern (requires approval)",
        "parameters": {
            "name": {"type": "string", "description": "Pattern name"},
            "description": {"type": "string", "description": "Pattern description"},
            "risk_level": {"type": "string", "description": "Risk level (low, medium, high, critical)"},
            "example_phrases": {"type": "array", "items": {"type": "string"}, "description": "Example phrases for detection"},
            "source_url": {"type": "string", "description": "Source URL for verification"},
            "created_by_user_id": {"type": "integer", "description": "User ID proposing the action", "default": 1}
        }
    },
    "propose_scam_alert_create": {
        "function": propose_scam_alert_create,
        "description": "Propose creating a live scam alert (requires approval)",
        "parameters": {
            "title": {"type": "string", "description": "Alert title"},
            "description": {"type": "string", "description": "Alert description"},
            "severity": {"type": "string", "description": "Severity (low, medium, high, critical)"},
            "location": {"type": "string", "description": "Location (optional)"},
            "created_by_user_id": {"type": "integer", "description": "User ID proposing the action", "default": 1}
        }
    },
    
    # Config & Feature Flags
    "propose_feature_flag_toggle": {
        "function": propose_feature_flag_toggle,
        "description": "Propose toggling a feature flag (requires approval)",
        "parameters": {
            "flag_key": {"type": "string", "description": "Feature flag key"},
            "new_value": {"type": "boolean", "description": "New value (true/false)"},
            "reason": {"type": "string", "description": "Reason for change"},
            "created_by_user_id": {"type": "integer", "description": "User ID proposing the action", "default": 1}
        }
    },
    "propose_config_update": {
        "function": propose_config_update,
        "description": "Propose updating app configuration (requires approval)",
        "parameters": {
            "config_key": {"type": "string", "description": "Config key"},
            "new_value": {"type": "object", "description": "New value"},
            "reason": {"type": "string", "description": "Reason for change"},
            "created_by_user_id": {"type": "integer", "description": "User ID proposing the action", "default": 1}
        }
    },
    
    # Database Operations
    "propose_database_migration": {
        "function": propose_database_migration,
        "description": "Propose running a database migration (requires approval)",
        "parameters": {
            "migration_name": {"type": "string", "description": "Migration name"},
            "sql_script": {"type": "string", "description": "SQL script to execute"},
            "reason": {"type": "string", "description": "Reason for migration"},
            "created_by_user_id": {"type": "integer", "description": "User ID proposing the action", "default": 1}
        }
    },
    "propose_data_cleanup": {
        "function": propose_data_cleanup,
        "description": "Propose cleaning up data from a table (requires approval)",
        "parameters": {
            "table_name": {"type": "string", "description": "Table name"},
            "condition": {"type": "string", "description": "SQL WHERE condition"},
            "reason": {"type": "string", "description": "Reason for cleanup"},
            "created_by_user_id": {"type": "integer", "description": "User ID proposing the action", "default": 1}
        }
    },
    
    # System Operations
    "propose_service_restart": {
        "function": propose_service_restart,
        "description": "Propose restarting a service (requires approval)",
        "parameters": {
            "service_name": {"type": "string", "description": "Service name (web, frontend, postgres)"},
            "reason": {"type": "string", "description": "Reason for restart"},
            "created_by_user_id": {"type": "integer", "description": "User ID proposing the action", "default": 1}
        }
    },
    "propose_deployment_rollback": {
        "function": propose_deployment_rollback,
        "description": "Propose rolling back a deployment (requires approval)",
        "parameters": {
            "service_name": {"type": "string", "description": "Service name"},
            "target_version": {"type": "string", "description": "Target version to roll back to"},
            "reason": {"type": "string", "description": "Reason for rollback"},
            "created_by_user_id": {"type": "integer", "description": "User ID proposing the action", "default": 1}
        }
    }
}
