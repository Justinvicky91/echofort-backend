"""
AI Tool Status Module
Provides diagnostic information about AI tool configuration and health.
Used to give specific error messages instead of generic failures.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

def check_tool_status() -> Dict[str, Dict[str, Any]]:
    """
    Check the configuration and health status of all AI tools.
    
    Returns:
        Dictionary with status for each tool
    """
    status = {}
    
    # Check web_search tool
    search_api_key = os.getenv("SEARCH_API_KEY", "")
    status["web_search"] = {
        "configured": bool(search_api_key),
        "last_success": None,
        "last_error": None if search_api_key else "SEARCH_API_KEY not configured in Railway environment variables"
    }
    
    # Check web_fetch tool (no API key needed, always available)
    status["web_fetch"] = {
        "configured": True,
        "last_success": None,
        "last_error": None
    }
    
    # Check config_update tool (database-based, check if tables exist)
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'app_config'
                    )
                """)
                config_table_exists = cur.fetchone()[0]
                
                status["config_update"] = {
                    "configured": config_table_exists,
                    "last_success": None,
                    "last_error": None if config_table_exists else "app_config table not found in database"
                }
    except Exception as e:
        status["config_update"] = {
            "configured": False,
            "last_success": None,
            "last_error": f"Database error: {str(e)}"
        }
    
    # Check feature_flag tool
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'feature_flags'
                    )
                """)
                flags_table_exists = cur.fetchone()[0]
                
                status["feature_flag"] = {
                    "configured": flags_table_exists,
                    "last_success": None,
                    "last_error": None if flags_table_exists else "feature_flags table not found in database"
                }
    except Exception as e:
        status["feature_flag"] = {
            "configured": False,
            "last_success": None,
            "last_error": f"Database error: {str(e)}"
        }
    
    # Check code_change tool (GitHub PR creation)
    github_token = os.getenv("GITHUB_TOKEN", "")
    status["code_change"] = {
        "configured": bool(github_token),
        "last_success": None,
        "last_error": None if github_token else "GITHUB_TOKEN not configured in Railway environment variables"
    }
    
    # Check mobile_release tool (GitHub Actions trigger)
    status["mobile_release"] = {
        "configured": bool(github_token),
        "last_success": None,
        "last_error": None if github_token else "GITHUB_TOKEN not configured in Railway environment variables"
    }
    
    # Try to get last success/error from database logs if available
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Check for recent web searches
                cur.execute("""
                    SELECT created_at, results_count 
                    FROM ai_web_logs 
                    WHERE results_count > 0 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
                last_search = cur.fetchone()
                if last_search:
                    status["web_search"]["last_success"] = last_search["created_at"].isoformat()
                
                # Check for recent AI pending actions (for other tools)
                cur.execute("""
                    SELECT action_type, created_at, status 
                    FROM ai_pending_actions 
                    WHERE action_type IN ('CONFIG_UPDATE', 'FEATURE_FLAG_UPDATE', 'CODE_CHANGE_PR', 'MOBILE_RELEASE_TRIGGER')
                    ORDER BY created_at DESC 
                    LIMIT 10
                """)
                recent_actions = cur.fetchall()
                
                for action in recent_actions:
                    action_type = action["action_type"]
                    created_at = action["created_at"].isoformat()
                    
                    if action_type == "CONFIG_UPDATE" and status["config_update"]["configured"]:
                        if action["status"] == "executed":
                            status["config_update"]["last_success"] = created_at
                        elif action["status"] == "failed":
                            status["config_update"]["last_error"] = f"Last action failed at {created_at}"
                    
                    elif action_type == "FEATURE_FLAG_UPDATE" and status["feature_flag"]["configured"]:
                        if action["status"] == "executed":
                            status["feature_flag"]["last_success"] = created_at
                        elif action["status"] == "failed":
                            status["feature_flag"]["last_error"] = f"Last action failed at {created_at}"
                    
                    elif action_type == "CODE_CHANGE_PR" and status["code_change"]["configured"]:
                        if action["status"] == "executed":
                            status["code_change"]["last_success"] = created_at
                        elif action["status"] == "failed":
                            status["code_change"]["last_error"] = f"Last action failed at {created_at}"
                    
                    elif action_type == "MOBILE_RELEASE_TRIGGER" and status["mobile_release"]["configured"]:
                        if action["status"] == "executed":
                            status["mobile_release"]["last_success"] = created_at
                        elif action["status"] == "failed":
                            status["mobile_release"]["last_error"] = f"Last action failed at {created_at}"
    
    except Exception as e:
        logger.warning(f"Could not fetch tool usage history: {e}")
    
    return status

def get_tool_error_message(tool_name: str) -> str:
    """
    Get a specific, helpful error message for a tool that is not configured.
    
    Args:
        tool_name: Name of the tool (web_search, web_fetch, config_update, etc.)
    
    Returns:
        User-friendly error message with guidance
    """
    status = check_tool_status()
    
    if tool_name not in status:
        return f"Unknown tool: {tool_name}"
    
    tool_status = status[tool_name]
    
    if tool_status["configured"]:
        if tool_status["last_error"]:
            return f"The {tool_name} tool encountered an error: {tool_status['last_error']}"
        return f"The {tool_name} tool is configured and ready to use."
    
    # Tool not configured - provide specific guidance
    if tool_name == "web_search":
        return ("Internet search is not configured. The SEARCH_API_KEY environment variable is missing. "
                "Please ask your DevOps engineer to set up a Serper API key in Railway environment variables.")
    
    elif tool_name in ["code_change", "mobile_release"]:
        return ("GitHub integration is not configured. The GITHUB_TOKEN environment variable is missing. "
                "Please ask your DevOps engineer to set up a GitHub Personal Access Token in Railway environment variables.")
    
    elif tool_name in ["config_update", "feature_flag"]:
        return (f"Configuration management is not available. The required database table is missing. "
                f"Error: {tool_status['last_error']}")
    
    else:
        return f"The {tool_name} tool is not configured: {tool_status['last_error']}"

def get_configured_tools_summary() -> str:
    """
    Get a human-readable summary of which tools are configured.
    
    Returns:
        Summary string for display to users
    """
    status = check_tool_status()
    
    configured = []
    not_configured = []
    
    for tool_name, tool_status in status.items():
        if tool_status["configured"]:
            configured.append(tool_name)
        else:
            not_configured.append(tool_name)
    
    summary = []
    
    if configured:
        summary.append(f"✅ Configured tools: {', '.join(configured)}")
    
    if not_configured:
        summary.append(f"⚠️ Not configured: {', '.join(not_configured)}")
    
    return "\n".join(summary)
