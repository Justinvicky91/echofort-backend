"""
AI Config Management Tools
Allows EchoFort AI to read and propose changes to platform configuration.
All changes go through AI Pending Actions for approval.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

def get_config(scope: str, key_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get configuration entries for a given scope.
    
    Args:
        scope: 'web', 'backend', or 'mobile'
        key_prefix: Optional prefix to filter keys (e.g., 'hero_' to get all hero-related config)
    
    Returns:
        List of config entries with key, value_json, description
    """
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                if key_prefix:
                    cur.execute("""
                        SELECT id, scope, key, value_json, description, updated_at
                        FROM app_config
                        WHERE scope = %s AND key LIKE %s
                        ORDER BY key
                    """, (scope, f"{key_prefix}%"))
                else:
                    cur.execute("""
                        SELECT id, scope, key, value_json, description, updated_at
                        FROM app_config
                        WHERE scope = %s
                        ORDER BY key
                    """, (scope,))
                
                results = cur.fetchall()
                return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return []

def get_feature_flags(scope: str, flag_name_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get feature flags for a given scope.
    
    Args:
        scope: 'web', 'backend', or 'mobile'
        flag_name_prefix: Optional prefix to filter flag names
    
    Returns:
        List of feature flags with name, is_enabled, rollout_percent, notes
    """
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                if flag_name_prefix:
                    cur.execute("""
                        SELECT id, scope, flag_name, is_enabled, rollout_percent, notes, updated_at
                        FROM feature_flags
                        WHERE scope = %s AND flag_name LIKE %s
                        ORDER BY flag_name
                    """, (scope, f"{flag_name_prefix}%"))
                else:
                    cur.execute("""
                        SELECT id, scope, flag_name, is_enabled, rollout_percent, notes, updated_at
                        FROM feature_flags
                        WHERE scope = %s
                        ORDER BY flag_name
                    """, (scope,))
                
                results = cur.fetchall()
                return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Failed to get feature flags: {e}")
        return []

def propose_config_change(
    scope: str,
    key: str,
    new_value: Dict[str, Any],
    reason: str,
    created_by_user_id: int
) -> Dict[str, Any]:
    """
    Propose a configuration change (does NOT execute immediately).
    Creates an AI action proposal that requires approval.
    
    Args:
        scope: 'web', 'backend', or 'mobile'
        key: Config key to update
        new_value: New value as dict/JSON
        reason: Human-readable reason for the change
        created_by_user_id: User ID proposing the change
    
    Returns:
        Action proposal details
    """
    try:
        # Get current value for comparison
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT value_json FROM app_config
                    WHERE scope = %s AND key = %s
                """, (scope, key))
                result = cur.fetchone()
                old_value = dict(result)["value_json"] if result else None
        
        # Create action proposal
        from app.admin.ai_actions import create_action
        
        action = create_action(
            action_type="CONFIG_UPDATE",
            payload={
                "scope": scope,
                "key": key,
                "old_value": old_value,
                "new_value": new_value,
                "reason": reason
            },
            created_by_user_id=created_by_user_id,
            summary=f"Update {scope} config '{key}'"
        )
        
        return {
            "success": True,
            "action_id": action["id"],
            "action_type": "CONFIG_UPDATE",
            "summary": f"Proposed config change for {scope}.{key}",
            "message": "Config change proposal created. Awaiting approval in AI Pending Actions."
        }
        
    except Exception as e:
        logger.error(f"Failed to propose config change: {e}")
        return {
            "error": True,
            "safe_message": "I couldn't create the config change proposal. Please try again or contact support."
        }

def propose_feature_flag_change(
    flag_name: str,
    new_state: bool,
    scope: str,
    reason: str,
    created_by_user_id: int,
    rollout_percent: Optional[int] = None
) -> Dict[str, Any]:
    """
    Propose a feature flag change (does NOT execute immediately).
    Creates an AI action proposal that requires approval.
    
    Args:
        flag_name: Feature flag name
        new_state: True to enable, False to disable
        scope: 'web', 'backend', or 'mobile'
        reason: Human-readable reason for the change
        created_by_user_id: User ID proposing the change
        rollout_percent: Optional rollout percentage (0-100)
    
    Returns:
        Action proposal details
    """
    try:
        # Get current state for comparison
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT is_enabled, rollout_percent FROM feature_flags
                    WHERE scope = %s AND flag_name = %s
                """, (scope, flag_name))
                result = cur.fetchone()
                if result:
                    result_dict = dict(result)
                    old_state = result_dict["is_enabled"]
                    old_rollout = result_dict["rollout_percent"]
                else:
                    old_state = None
                    old_rollout = None
        
        # Create action proposal
        from app.admin.ai_actions import create_action
        
        payload = {
            "scope": scope,
            "flag_name": flag_name,
            "old_state": old_state,
            "new_state": new_state,
            "reason": reason
        }
        
        if rollout_percent is not None:
            payload["rollout_percent"] = rollout_percent
            payload["old_rollout_percent"] = old_rollout
        
        action = create_action(
            action_type="FEATURE_FLAG_UPDATE",
            payload=payload,
            created_by_user_id=created_by_user_id,
            summary=f"{'Enable' if new_state else 'Disable'} {scope} feature flag '{flag_name}'"
        )
        
        return {
            "success": True,
            "action_id": action["id"],
            "action_type": "FEATURE_FLAG_UPDATE",
            "summary": f"Proposed feature flag change for {scope}.{flag_name}",
            "message": "Feature flag change proposal created. Awaiting approval in AI Pending Actions."
        }
        
    except Exception as e:
        logger.error(f"Failed to propose feature flag change: {e}")
        return {
            "error": True,
            "safe_message": "I couldn't create the feature flag change proposal. Please try again or contact support."
        }

def execute_config_update(payload: Dict[str, Any], executed_by_user_id: int) -> Dict[str, Any]:
    """
    Execute an approved config update.
    Called by the action executor when a CONFIG_UPDATE action is approved.
    
    Args:
        payload: Action payload with scope, key, new_value, reason
        executed_by_user_id: User ID executing the action
    
    Returns:
        Execution result
    """
    try:
        scope = payload["scope"]
        key = payload["key"]
        new_value = payload["new_value"]
        old_value = payload.get("old_value")
        reason = payload.get("reason", "")
        
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                # Update or insert config
                cur.execute("""
                    INSERT INTO app_config (scope, key, value_json, updated_by)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (scope, key) DO UPDATE
                    SET value_json = EXCLUDED.value_json,
                        updated_at = CURRENT_TIMESTAMP,
                        updated_by = EXCLUDED.updated_by
                """, (scope, key, json.dumps(new_value), executed_by_user_id))
                
                # Log the change
                cur.execute("""
                    INSERT INTO config_change_log (scope, key, old_value, new_value, changed_by, change_reason)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (scope, key, json.dumps(old_value) if old_value else None, json.dumps(new_value), executed_by_user_id, reason))
                
                conn.commit()
        
        return {
            "success": True,
            "message": f"Config {scope}.{key} updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to execute config update: {e}")
        return {
            "error": True,
            "message": f"Failed to update config: {str(e)}"
        }

def execute_feature_flag_update(payload: Dict[str, Any], executed_by_user_id: int) -> Dict[str, Any]:
    """
    Execute an approved feature flag update.
    Called by the action executor when a FEATURE_FLAG_UPDATE action is approved.
    
    Args:
        payload: Action payload with scope, flag_name, new_state, rollout_percent
        executed_by_user_id: User ID executing the action
    
    Returns:
        Execution result
    """
    try:
        scope = payload["scope"]
        flag_name = payload["flag_name"]
        new_state = payload["new_state"]
        rollout_percent = payload.get("rollout_percent", 100)
        
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                # Update or insert feature flag
                cur.execute("""
                    INSERT INTO feature_flags (scope, flag_name, is_enabled, rollout_percent, updated_by)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (scope, flag_name) DO UPDATE
                    SET is_enabled = EXCLUDED.is_enabled,
                        rollout_percent = EXCLUDED.rollout_percent,
                        updated_at = CURRENT_TIMESTAMP,
                        updated_by = EXCLUDED.updated_by
                """, (scope, flag_name, new_state, rollout_percent, executed_by_user_id))
                
                conn.commit()
        
        return {
            "success": True,
            "message": f"Feature flag {scope}.{flag_name} {'enabled' if new_state else 'disabled'} successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to execute feature flag update: {e}")
        return {
            "error": True,
            "message": f"Failed to update feature flag: {str(e)}"
        }
