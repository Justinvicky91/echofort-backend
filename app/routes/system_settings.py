"""
System Settings Management API
Allows Super Admin to manage system-wide settings like WhatsApp chat toggle
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel
from ..utils import get_current_user
import os

router = APIRouter(prefix="/api/admin/settings", tags=["System Settings"])


class SettingUpdate(BaseModel):
    setting_key: str
    setting_value: str


def verify_super_admin(current_user: dict) -> bool:
    """Verify user is super admin"""
    return current_user.get("role") == "super_admin" or current_user.get("email") == os.getenv("OWNER_EMAIL")


@router.get("/list")
async def get_all_settings(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all system settings (Super Admin only)
    """
    try:
        if not verify_super_admin(current_user):
            raise HTTPException(403, "Super Admin access required")
        
        db = request.app.state.db
        
        result = await db.execute(text("""
            SELECT setting_key, setting_value, setting_type, description, updated_at
            FROM system_settings
            ORDER BY setting_key
        """))
        
        settings = []
        for row in result.fetchall():
            settings.append({
                "key": row[0],
                "value": row[1],
                "type": row[2],
                "description": row[3],
                "updated_at": str(row[4]) if row[4] else None
            })
        
        return {
            "ok": True,
            "settings": settings
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch settings: {str(e)}")


@router.get("/get/{setting_key}")
async def get_setting(
    request: Request,
    setting_key: str
):
    """
    Get a specific setting value (Public endpoint for website)
    """
    try:
        db = request.app.state.db
        
        result = await db.execute(text("""
            SELECT setting_value, setting_type
            FROM system_settings
            WHERE setting_key = :key
        """), {"key": setting_key})
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(404, f"Setting '{setting_key}' not found")
        
        value = row[0]
        setting_type = row[1]
        
        # Convert value based on type
        if setting_type == "boolean":
            value = value.lower() in ('true', '1', 'yes')
        elif setting_type == "integer":
            value = int(value)
        elif setting_type == "float":
            value = float(value)
        
        return {
            "ok": True,
            "key": setting_key,
            "value": value,
            "type": setting_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch setting: {str(e)}")


@router.post("/update")
async def update_setting(
    request: Request,
    setting: SettingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a system setting (Super Admin only)
    """
    try:
        if not verify_super_admin(current_user):
            raise HTTPException(403, "Super Admin access required")
        
        db = request.app.state.db
        
        # Check if setting exists
        existing = await db.execute(text("""
            SELECT id FROM system_settings WHERE setting_key = :key
        """), {"key": setting.setting_key})
        
        if not existing.fetchone():
            raise HTTPException(404, f"Setting '{setting.setting_key}' not found")
        
        # Update setting
        await db.execute(text("""
            UPDATE system_settings
            SET setting_value = :value,
                updated_at = NOW(),
                updated_by = :admin_id
            WHERE setting_key = :key
        """), {
            "key": setting.setting_key,
            "value": setting.setting_value,
            "admin_id": current_user.get("id") or current_user.get("employee_id") or current_user.get("sub")
        })
        
        return {
            "ok": True,
            "message": f"Setting '{setting.setting_key}' updated successfully",
            "key": setting.setting_key,
            "value": setting.setting_value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update setting: {str(e)}")


@router.get("/whatsapp-chat")
async def get_whatsapp_chat_config(request: Request):
    """
    Get WhatsApp chat configuration (Public endpoint for website)
    """
    try:
        db = request.app.state.db
        
        result = await db.execute(text("""
            SELECT setting_key, setting_value
            FROM system_settings
            WHERE setting_key IN ('whatsapp_chat_enabled', 'whatsapp_chat_number', 'whatsapp_chat_message')
        """))
        
        config = {}
        for row in result.fetchall():
            key = row[0]
            value = row[1]
            
            if key == 'whatsapp_chat_enabled':
                config['enabled'] = value.lower() in ('true', '1', 'yes')
            elif key == 'whatsapp_chat_number':
                config['number'] = value
            elif key == 'whatsapp_chat_message':
                config['message'] = value
        
        return {
            "ok": True,
            "config": config
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch WhatsApp config: {str(e)}")
