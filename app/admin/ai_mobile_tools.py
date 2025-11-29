"""
AI Mobile Tools
Allows EchoFort AI to control mobile app configuration and trigger releases.
All actions go through AI Pending Actions for approval.
"""

import os
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# GitHub Actions workflow configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_ORG = "Justinvicky91"
MOBILE_REPO = "echofort-mobile"
WORKFLOW_FILE = "build-and-release.yml"  # GitHub Actions workflow file

def trigger_github_workflow(workflow_file: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Trigger a GitHub Actions workflow"""
    url = f"https://api.github.com/repos/{GITHUB_ORG}/{MOBILE_REPO}/actions/workflows/{workflow_file}/dispatches"
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    data = {
        "ref": "main",
        "inputs": inputs
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 204:
            return {"success": True, "message": "Workflow triggered successfully"}
        else:
            logger.error(f"GitHub workflow trigger failed: {response.status_code} - {response.text}")
            return {"error": f"Failed to trigger workflow: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Failed to trigger GitHub workflow: {e}")
        return {"error": str(e)}

def propose_mobile_release(
    version_hint: str,
    notes: str,
    created_by_user_id: int,
    build_type: str = "release"
) -> Dict[str, Any]:
    """
    Propose a mobile app release (does NOT execute immediately).
    Creates an AI action proposal that requires approval.
    
    Args:
        version_hint: Version number hint (e.g., "1.0.13")
        notes: Release notes
        created_by_user_id: User ID proposing the release
        build_type: 'release' or 'beta'
    
    Returns:
        Action proposal details
    """
    try:
        # Create action proposal
        from app.admin.ai_actions import create_action
        
        action = create_action(
            action_type="MOBILE_RELEASE_TRIGGER",
            payload={
                "version_hint": version_hint,
                "notes": notes,
                "build_type": build_type,
                "repo": MOBILE_REPO,
                "workflow_file": WORKFLOW_FILE,
                "timestamp": datetime.utcnow().isoformat()
            },
            created_by_user_id=created_by_user_id,
            summary=f"Mobile release trigger for v{version_hint} ({build_type})"
        )
        
        return {
            "success": True,
            "action_id": action["id"],
            "action_type": "MOBILE_RELEASE_TRIGGER",
            "summary": f"Proposed mobile release for v{version_hint}",
            "message": "Mobile release proposal created. Awaiting approval in AI Pending Actions."
        }
        
    except Exception as e:
        logger.error(f"Failed to propose mobile release: {e}")
        return {
            "error": True,
            "safe_message": "I couldn't create the mobile release proposal. Please try again or contact support."
        }

def execute_mobile_release_trigger(payload: Dict[str, Any], executed_by_user_id: int) -> Dict[str, Any]:
    """
    Execute an approved mobile release trigger.
    Called by the action executor when a MOBILE_RELEASE_TRIGGER action is approved.
    
    Args:
        payload: Action payload with version_hint, notes, build_type
        executed_by_user_id: User ID executing the action
    
    Returns:
        Execution result
    """
    try:
        version_hint = payload["version_hint"]
        notes = payload["notes"]
        build_type = payload.get("build_type", "release")
        workflow_file = payload.get("workflow_file", WORKFLOW_FILE)
        
        # Trigger GitHub Actions workflow
        workflow_inputs = {
            "version": version_hint,
            "release_notes": notes,
            "build_type": build_type,
            "triggered_by": f"User ID {executed_by_user_id}"
        }
        
        result = trigger_github_workflow(workflow_file, workflow_inputs)
        
        if "error" in result:
            return {
                "error": True,
                "message": f"Failed to trigger mobile release: {result['error']}"
            }
        
        return {
            "success": True,
            "message": f"Mobile release v{version_hint} triggered successfully",
            "workflow_url": f"https://github.com/{GITHUB_ORG}/{MOBILE_REPO}/actions",
            "version": version_hint,
            "build_type": build_type
        }
        
    except Exception as e:
        logger.error(f"Failed to execute mobile release trigger: {e}")
        return {
            "error": True,
            "message": f"Failed to trigger mobile release: {str(e)}"
        }

# Note: Mobile remote config is already handled by ai_config_tools.py
# with scope="mobile", so no additional functions needed here.
