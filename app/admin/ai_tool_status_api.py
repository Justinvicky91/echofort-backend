"""
AI Tool Status API Endpoint
Provides a REST API for checking AI tool configuration and health.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from app.admin.ai_tool_status import check_tool_status, get_configured_tools_summary

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/admin/ai/tools/status")
async def get_ai_tools_status() -> Dict[str, Any]:
    """
    Get the configuration and health status of all AI tools.
    
    Returns:
        {
          "web_search": {
            "configured": true/false,
            "last_success": "ISO timestamp or null",
            "last_error": "error message or null"
          },
          ...
        }
    
    Requires admin authentication.
    """
    try:
        status = check_tool_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get tool status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tool status")

@router.get("/admin/ai/tools/summary")
async def get_ai_tools_summary() -> Dict[str, str]:
    """
    Get a human-readable summary of configured tools.
    
    Returns:
        {
          "summary": "✅ Configured tools: web_fetch, config_update, feature_flag\n⚠️ Not configured: web_search, code_change, mobile_release"
        }
    
    Requires admin authentication.
    """
    try:
        summary = get_configured_tools_summary()
        return {"summary": summary}
    except Exception as e:
        logger.error(f"Failed to get tools summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tools summary")
