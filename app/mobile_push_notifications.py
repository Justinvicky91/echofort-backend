"""
Mobile Push Notifications API
Real-time alerts and notifications for mobile devices
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, time
from sqlalchemy import text
from .deps import get_db, get_current_user

router = APIRouter(prefix="/api/mobile/notifications", tags=["Mobile Push Notifications"])


class RegisterTokenRequest(BaseModel):
    deviceToken: str
    platform: str = Field(..., description="ios or android")
    deviceModel: Optional[str] = None
    osVersion: Optional[str] = None
    appVersion: Optional[str] = None


class SendNotificationRequest(BaseModel):
    userId: int
    title: str
    body: str
    notificationType: str
    priority: str = "normal"
    data: Optional[Dict[str, Any]] = None


class NotificationSettingsRequest(BaseModel):
    enableScamAlerts: Optional[bool] = None
    enableFamilyAlerts: Optional[bool] = None
    enableCallAlerts: Optional[bool] = None
    enableSmsAlerts: Optional[bool] = None
    enableLocationAlerts: Optional[bool] = None
    enableAppUsageAlerts: Optional[bool] = None
    enableEmergencyAlerts: Optional[bool] = None
    enableMarketing: Optional[bool] = None
    quietHoursEnabled: Optional[bool] = None
    quietHoursStart: Optional[str] = None  # Format: "HH:MM"
    quietHoursEnd: Optional[str] = None


@router.post("/register-token")
async def register_device_token(
    request: RegisterTokenRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Register a device token for push notifications
    """
    try:
        # Deactivate old tokens for this user on same platform
        deactivate_query = text("""
            UPDATE device_tokens
            SET is_active = FALSE
            WHERE user_id = :user_id AND platform = :platform AND device_token != :new_token
        """)
        
        db.execute(deactivate_query, {
            "user_id": current_user["id"],
            "platform": request.platform,
            "new_token": request.deviceToken
        })
        
        # Insert or update token
        query = text("""
            INSERT INTO device_tokens 
            (user_id, device_token, platform, device_model, os_version, app_version, is_active)
            VALUES (:user_id, :token, :platform, :model, :os_version, :app_version, TRUE)
            ON CONFLICT (device_token) DO UPDATE
            SET user_id = :user_id,
                platform = :platform,
                device_model = :model,
                os_version = :os_version,
                app_version = :app_version,
                is_active = TRUE,
                last_used_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """)
        
        result = db.execute(query, {
            "user_id": current_user["id"],
            "token": request.deviceToken,
            "platform": request.platform,
            "model": request.deviceModel,
            "os_version": request.osVersion,
            "app_version": request.appVersion
        })
        
        token_id = result.fetchone()[0]
        db.commit()
        
        return {
            "ok": True,
            "tokenId": token_id,
            "message": "Device registered for push notifications"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Token registration failed: {str(e)}")


@router.post("/send")
async def send_notification(
    request: SendNotificationRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Send a push notification to a user
    (Admin/System use - queues notification for delivery)
    """
    try:
        # Use database function to queue notification
        query = text("""
            SELECT queue_notification(
                :user_id,
                :title,
                :body,
                :notification_type,
                :priority,
                :data
            )
        """)
        
        result = db.execute(query, {
            "user_id": request.userId,
            "title": request.title,
            "body": request.body,
            "notification_type": request.notificationType,
            "priority": request.priority,
            "data": request.data
        })
        
        notification_id = result.fetchone()[0]
        db.commit()
        
        if notification_id:
            return {
                "ok": True,
                "notificationId": notification_id,
                "message": "Notification queued for delivery"
            }
        else:
            return {
                "ok": False,
                "message": "Notification not sent (user settings or quiet hours)"
            }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Send notification failed: {str(e)}")


@router.get("/history")
async def get_notification_history(
    limit: int = 50,
    unread_only: bool = False,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user's notification history
    """
    try:
        read_filter = "AND read_at IS NULL" if unread_only else ""
        
        query = text(f"""
            SELECT 
                id,
                title,
                body,
                notification_type,
                priority,
                data,
                status,
                sent_at,
                read_at,
                created_at
            FROM push_notifications
            WHERE user_id = :user_id {read_filter}
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {
            "user_id": current_user["id"],
            "limit": limit
        }).fetchall()
        
        notifications = []
        for row in results:
            notifications.append({
                "id": row[0],
                "title": row[1],
                "body": row[2],
                "notificationType": row[3],
                "priority": row[4],
                "data": row[5],
                "status": row[6],
                "sentAt": row[7].isoformat() if row[7] else None,
                "readAt": row[8].isoformat() if row[8] else None,
                "createdAt": row[9].isoformat() if row[9] else None
            })
        
        return {"ok": True, "notifications": notifications}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/mark-read/{notification_id}")
async def mark_notification_read(
    notification_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Mark a notification as read
    """
    try:
        query = text("""
            UPDATE push_notifications
            SET read_at = CURRENT_TIMESTAMP
            WHERE id = :notification_id AND user_id = :user_id AND read_at IS NULL
            RETURNING id
        """)
        
        result = db.execute(query, {
            "notification_id": notification_id,
            "user_id": current_user["id"]
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Notification not found or already read")
        
        # Update statistics
        stats_query = text("""
            UPDATE notification_statistics
            SET total_read = total_read + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
        """)
        db.execute(stats_query, {"user_id": current_user["id"]})
        
        db.commit()
        
        return {"ok": True, "message": "Notification marked as read"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Delete a notification
    """
    try:
        query = text("""
            DELETE FROM push_notifications
            WHERE id = :notification_id AND user_id = :user_id
            RETURNING id
        """)
        
        result = db.execute(query, {
            "notification_id": notification_id,
            "user_id": current_user["id"]
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        db.commit()
        
        return {"ok": True, "message": "Notification deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings")
async def get_notification_settings(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user's notification settings
    """
    try:
        query = text("""
            SELECT 
                enable_scam_alerts,
                enable_family_alerts,
                enable_call_alerts,
                enable_sms_alerts,
                enable_location_alerts,
                enable_app_usage_alerts,
                enable_emergency_alerts,
                enable_marketing,
                quiet_hours_enabled,
                quiet_hours_start,
                quiet_hours_end
            FROM notification_settings
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": current_user["id"]}).fetchone()
        
        if result:
            return {
                "ok": True,
                "settings": {
                    "enableScamAlerts": result[0],
                    "enableFamilyAlerts": result[1],
                    "enableCallAlerts": result[2],
                    "enableSmsAlerts": result[3],
                    "enableLocationAlerts": result[4],
                    "enableAppUsageAlerts": result[5],
                    "enableEmergencyAlerts": result[6],
                    "enableMarketing": result[7],
                    "quietHoursEnabled": result[8],
                    "quietHoursStart": str(result[9]) if result[9] else None,
                    "quietHoursEnd": str(result[10]) if result[10] else None
                }
            }
        else:
            # Return defaults
            return {
                "ok": True,
                "settings": {
                    "enableScamAlerts": True,
                    "enableFamilyAlerts": True,
                    "enableCallAlerts": True,
                    "enableSmsAlerts": True,
                    "enableLocationAlerts": True,
                    "enableAppUsageAlerts": True,
                    "enableEmergencyAlerts": True,
                    "enableMarketing": False,
                    "quietHoursEnabled": False,
                    "quietHoursStart": None,
                    "quietHoursEnd": None
                }
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
async def update_notification_settings(
    request: NotificationSettingsRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Update user's notification settings
    """
    try:
        # Build update query dynamically based on provided fields
        updates = []
        params = {"user_id": current_user["id"]}
        
        if request.enableScamAlerts is not None:
            updates.append("enable_scam_alerts = :enable_scam_alerts")
            params["enable_scam_alerts"] = request.enableScamAlerts
        
        if request.enableFamilyAlerts is not None:
            updates.append("enable_family_alerts = :enable_family_alerts")
            params["enable_family_alerts"] = request.enableFamilyAlerts
        
        if request.enableCallAlerts is not None:
            updates.append("enable_call_alerts = :enable_call_alerts")
            params["enable_call_alerts"] = request.enableCallAlerts
        
        if request.enableSmsAlerts is not None:
            updates.append("enable_sms_alerts = :enable_sms_alerts")
            params["enable_sms_alerts"] = request.enableSmsAlerts
        
        if request.enableLocationAlerts is not None:
            updates.append("enable_location_alerts = :enable_location_alerts")
            params["enable_location_alerts"] = request.enableLocationAlerts
        
        if request.enableAppUsageAlerts is not None:
            updates.append("enable_app_usage_alerts = :enable_app_usage_alerts")
            params["enable_app_usage_alerts"] = request.enableAppUsageAlerts
        
        if request.enableEmergencyAlerts is not None:
            updates.append("enable_emergency_alerts = :enable_emergency_alerts")
            params["enable_emergency_alerts"] = request.enableEmergencyAlerts
        
        if request.enableMarketing is not None:
            updates.append("enable_marketing = :enable_marketing")
            params["enable_marketing"] = request.enableMarketing
        
        if request.quietHoursEnabled is not None:
            updates.append("quiet_hours_enabled = :quiet_hours_enabled")
            params["quiet_hours_enabled"] = request.quietHoursEnabled
        
        if request.quietHoursStart is not None:
            updates.append("quiet_hours_start = :quiet_hours_start")
            params["quiet_hours_start"] = request.quietHoursStart
        
        if request.quietHoursEnd is not None:
            updates.append("quiet_hours_end = :quiet_hours_end")
            params["quiet_hours_end"] = request.quietHoursEnd
        
        if not updates:
            raise HTTPException(status_code=400, detail="No settings provided to update")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        query = text(f"""
            INSERT INTO notification_settings (user_id)
            VALUES (:user_id)
            ON CONFLICT (user_id) DO UPDATE
            SET {', '.join(updates)}
            RETURNING user_id
        """)
        
        db.execute(query, params)
        db.commit()
        
        return {"ok": True, "message": "Notification settings updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_notification_statistics(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get notification statistics
    """
    try:
        query = text("""
            SELECT 
                total_sent,
                total_delivered,
                total_read,
                total_failed,
                last_notification_at
            FROM notification_statistics
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": current_user["id"]}).fetchone()
        
        if result:
            return {
                "ok": True,
                "statistics": {
                    "totalSent": result[0] or 0,
                    "totalDelivered": result[1] or 0,
                    "totalRead": result[2] or 0,
                    "totalFailed": result[3] or 0,
                    "lastNotificationAt": result[4].isoformat() if result[4] else None
                }
            }
        else:
            return {
                "ok": True,
                "statistics": {
                    "totalSent": 0,
                    "totalDelivered": 0,
                    "totalRead": 0,
                    "totalFailed": 0,
                    "lastNotificationAt": None
                }
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unread-count")
async def get_unread_count(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get count of unread notifications
    """
    try:
        query = text("""
            SELECT COUNT(*)
            FROM push_notifications
            WHERE user_id = :user_id AND read_at IS NULL
        """)
        
        result = db.execute(query, {"user_id": current_user["id"]}).fetchone()
        
        return {
            "ok": True,
            "unreadCount": result[0] if result else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
