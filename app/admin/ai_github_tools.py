"""
AI GitHub Integration Tools
Allows EchoFort AI to propose code changes via GitHub PRs.
All PR creation goes through AI Pending Actions for approval.
"""

import os
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import base64

logger = logging.getLogger(__name__)

# GitHub configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_URL = "https://api.github.com"
GITHUB_ORG = "Justinvicky91"  # Your GitHub organization/username

# Repository mapping
REPOS = {
    "backend": "echofort-backend",
    "frontend": "echofort-frontend-prod",
    "mobile": "echofort-mobile"
}

def github_api_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make a request to GitHub API"""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"{GITHUB_API_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        if response.status_code >= 400:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            return {"error": f"GitHub API error: {response.status_code}"}
        
        return response.json()
        
    except Exception as e:
        logger.error(f"GitHub API request failed: {e}")
        return {"error": str(e)}

def github_list_repos() -> List[Dict[str, Any]]:
    """List available repositories"""
    result = github_api_request("GET", f"/users/{GITHUB_ORG}/repos")
    
    if "error" in result:
        return []
    
    return [
        {
            "name": repo["name"],
            "full_name": repo["full_name"],
            "default_branch": repo["default_branch"],
            "private": repo["private"]
        }
        for repo in result
        if repo["name"] in REPOS.values()
    ]

def github_get_file(repo: str, path: str, branch: str = "main") -> Optional[str]:
    """Get file content from GitHub repository"""
    result = github_api_request("GET", f"/repos/{GITHUB_ORG}/{repo}/contents/{path}?ref={branch}")
    
    if "error" in result or "content" not in result:
        return None
    
    # Decode base64 content
    content = base64.b64decode(result["content"]).decode("utf-8")
    return content

def github_create_branch(repo: str, base_branch: str, new_branch_name: str) -> Dict[str, Any]:
    """Create a new branch from base branch"""
    # Get base branch SHA
    result = github_api_request("GET", f"/repos/{GITHUB_ORG}/{repo}/git/refs/heads/{base_branch}")
    
    if "error" in result:
        return result
    
    base_sha = result["object"]["sha"]
    
    # Create new branch
    result = github_api_request("POST", f"/repos/{GITHUB_ORG}/{repo}/git/refs", {
        "ref": f"refs/heads/{new_branch_name}",
        "sha": base_sha
    })
    
    return result

def github_update_file(repo: str, branch: str, path: str, content: str, message: str) -> Dict[str, Any]:
    """Update a file in a GitHub repository"""
    # Get current file SHA if it exists
    current_file = github_api_request("GET", f"/repos/{GITHUB_ORG}/{repo}/contents/{path}?ref={branch}")
    
    file_sha = current_file.get("sha") if "sha" in current_file else None
    
    # Update or create file
    data = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch
    }
    
    if file_sha:
        data["sha"] = file_sha
    
    result = github_api_request("PUT", f"/repos/{GITHUB_ORG}/{repo}/contents/{path}", data)
    return result

def github_create_pr(
    repo: str,
    source_branch: str,
    base_branch: str,
    title: str,
    body: str
) -> Dict[str, Any]:
    """Create a pull request"""
    result = github_api_request("POST", f"/repos/{GITHUB_ORG}/{repo}/pulls", {
        "title": title,
        "head": source_branch,
        "base": base_branch,
        "body": body
    })
    
    return result

def propose_code_change(
    target: str,
    description: str,
    files_to_change: List[Dict[str, str]],
    created_by_user_id: int
) -> Dict[str, Any]:
    """
    Propose a code change via GitHub PR (does NOT execute immediately).
    Creates an AI action proposal that requires approval.
    
    Args:
        target: Target system ('backend', 'frontend', 'mobile')
        description: Description of the code change
        files_to_change: List of {path, content} dicts
        created_by_user_id: User ID proposing the change
    
    Returns:
        Action proposal details
    """
    try:
        # Validate target
        if target not in REPOS:
            return {
                "error": True,
                "safe_message": f"Invalid target: {target}. Must be backend, frontend, or mobile."
            }
        
        repo = REPOS[target]
        
        # Create action proposal
        from app.admin.ai_actions import create_action
        
        action = create_action(
            action_type="CODE_CHANGE_PR",
            payload={
                "target": target,
                "repo": repo,
                "description": description,
                "files_to_change": files_to_change,
                "branch_name": f"ai-change-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
                "base_branch": "main"
            },
            created_by_user_id=created_by_user_id,
            summary=f"Code change PR for {target}: {description[:100]}"
        )
        
        return {
            "success": True,
            "action_id": action["id"],
            "action_type": "CODE_CHANGE_PR",
            "summary": f"Proposed code change for {target}",
            "message": "Code change proposal created. Awaiting approval in AI Pending Actions."
        }
        
    except Exception as e:
        logger.error(f"Failed to propose code change: {e}")
        return {
            "error": True,
            "safe_message": "I couldn't create the code change proposal. Please try again or contact support."
        }

def execute_code_change_pr(payload: Dict[str, Any], executed_by_user_id: int) -> Dict[str, Any]:
    """
    Execute an approved code change PR.
    Called by the action executor when a CODE_CHANGE_PR action is approved.
    
    Args:
        payload: Action payload with target, repo, description, files_to_change
        executed_by_user_id: User ID executing the action
    
    Returns:
        Execution result with PR URL
    """
    try:
        repo = payload["repo"]
        branch_name = payload["branch_name"]
        base_branch = payload.get("base_branch", "main")
        description = payload["description"]
        files_to_change = payload["files_to_change"]
        
        # Create new branch
        branch_result = github_create_branch(repo, base_branch, branch_name)
        
        if "error" in branch_result:
            return {
                "error": True,
                "message": f"Failed to create branch: {branch_result['error']}"
            }
        
        # Update files
        for file_change in files_to_change:
            path = file_change["path"]
            content = file_change["content"]
            
            update_result = github_update_file(
                repo, branch_name, path, content,
                f"AI-proposed change: {description}"
            )
            
            if "error" in update_result:
                return {
                    "error": True,
                    "message": f"Failed to update file {path}: {update_result['error']}"
                }
        
        # Create PR
        pr_result = github_create_pr(
            repo, branch_name, base_branch,
            f"[AI-Proposed] {description}",
            f"""This PR was proposed by EchoFort AI and approved by the team.

**Description:**
{description}

**Files Changed:**
{', '.join([f['path'] for f in files_to_change])}

**Approved by:** User ID {executed_by_user_id}
**Created:** {datetime.utcnow().isoformat()}

Please review the changes and merge if everything looks good.
"""
        )
        
        if "error" in pr_result:
            return {
                "error": True,
                "message": f"Failed to create PR: {pr_result['error']}"
            }
        
        pr_url = pr_result.get("html_url", "")
        pr_number = pr_result.get("number", "")
        
        return {
            "success": True,
            "message": f"PR #{pr_number} created successfully",
            "pr_url": pr_url,
            "pr_number": pr_number
        }
        
    except Exception as e:
        logger.error(f"Failed to execute code change PR: {e}")
        return {
            "error": True,
            "message": f"Failed to create PR: {str(e)}"
        }
