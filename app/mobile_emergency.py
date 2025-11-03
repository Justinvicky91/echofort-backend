"""
Mobile Emergency Contacts API
Emergency contacts and SOS alert functionality
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from sqlalchemy import text
from .utils import get_current_user

router = APIRouter(prefix="/api/mobile/emergency", tags=["Mobile Emergency"])


class EmergencyContactRequest(BaseModel):
    name: str
    phone: str
    relationship: Optional[str] = None
    email: Optional[str] = None
    isPrimary: bool = False
    priority: int = Field(1, ge=1, le=10)
    notifyOnEmergency: bool = True
    notifyOnLocationAlert: bool = False
    notifyOnScamAlert: bool = False


class EmergencyAlertRequest(BaseModel):
    alertType: str = Field(..., description="sos, panic, location_alert, scam_alert")
    severity: str = Field("high", description="low, medium, high, critical")
    message: Optional[str] = None
    locationLat: Optional[float] = None
    locationLng: Optional[float] = None
    locationAccuracy: Optional[float] = None
    locationAddress: Optional[str] = None


class SOSSettingsRequest(BaseModel):
    sosEnabled: Optional[bool] = None
    autoCallEmergency: Optional[bool] = None
    emergencyNumber: Optional[str] = None
    countdownSeconds: Optional[int] = Field(None, ge=0, le=30)
    shareLocation: Optional[bool] = None
    shareAudio: Optional[bool] = None
    shareVideo: Optional[bool] = None
    autoRecordAudio: Optional[bool] = None
    autoRecordVideo: Optional[bool] = None
    silentMode: Optional[bool] = None


@router.get("/contacts")
async def get_emergency_contacts(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get all emergency contacts for user
    """
    try:
        query = text("""
            SELECT 
                id, name, phone, relationship, email, is_primary, priority,
                notify_on_emergency, notify_on_location_alert, notify_on_scam_alert,
                created_at
            FROM emergency_contacts
            WHERE user_id = :user_id
            ORDER BY priority ASC, created_at ASC
        """)
        
        results = db.execute(query, {"user_id": current_user["id"]}).fetchall()
        
        contacts = []
        for row in results:
            contacts.append({
                "id": row[0],
                "name": row[1],
                "phone": row[2],
                "relationship": row[3],
                "email": row[4],
                "isPrimary": row[5],
                "priority": row[6],
                "notifyOnEmergency": row[7],
                "notifyOnLocationAlert": row[8],
                "notifyOnScamAlert": row[9],
                "createdAt": row[10].isoformat() if row[10] else None
            })
        
        return {"ok": True, "contacts": contacts}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contacts")
async def add_emergency_contact(
    request: EmergencyContactRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Add a new emergency contact
    """
    try:
        # If this is primary, unset other primary contacts
        if request.isPrimary:
            db.execute(text("""
                UPDATE emergency_contacts
                SET is_primary = FALSE
                WHERE user_id = :user_id
            """), {"user_id": current_user["id"]})
        
        # Insert new contact
        query = text("""
            INSERT INTO emergency_contacts 
            (user_id, name, phone, relationship, email, is_primary, priority,
             notify_on_emergency, notify_on_location_alert, notify_on_scam_alert)
            VALUES (:user_id, :name, :phone, :relationship, :email, :is_primary, :priority,
                    :notify_emergency, :notify_location, :notify_scam)
            RETURNING id
        """)
        
        contact_id = db.execute(query, {
            "user_id": current_user["id"],
            "name": request.name,
            "phone": request.phone,
            "relationship": request.relationship,
            "email": request.email,
            "is_primary": request.isPrimary,
            "priority": request.priority,
            "notify_emergency": request.notifyOnEmergency,
            "notify_location": request.notifyOnLocationAlert,
            "notify_scam": request.notifyOnScamAlert
        }).fetchone()[0]
        
        db.commit()
        
        return {
            "ok": True,
            "contactId": contact_id,
            "message": "Emergency contact added"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/contacts/{contact_id}")
async def update_emergency_contact(
    contact_id: int,
    request: EmergencyContactRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Update an emergency contact
    """
    try:
        # If this is primary, unset other primary contacts
        if request.isPrimary:
            db.execute(text("""
                UPDATE emergency_contacts
                SET is_primary = FALSE
                WHERE user_id = :user_id AND id != :contact_id
            """), {"user_id": current_user["id"], "contact_id": contact_id})
        
        query = text("""
            UPDATE emergency_contacts
            SET name = :name,
                phone = :phone,
                relationship = :relationship,
                email = :email,
                is_primary = :is_primary,
                priority = :priority,
                notify_on_emergency = :notify_emergency,
                notify_on_location_alert = :notify_location,
                notify_on_scam_alert = :notify_scam,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :contact_id AND user_id = :user_id
            RETURNING id
        """)
        
        result = db.execute(query, {
            "contact_id": contact_id,
            "user_id": current_user["id"],
            "name": request.name,
            "phone": request.phone,
            "relationship": request.relationship,
            "email": request.email,
            "is_primary": request.isPrimary,
            "priority": request.priority,
            "notify_emergency": request.notifyOnEmergency,
            "notify_location": request.notifyOnLocationAlert,
            "notify_scam": request.notifyOnScamAlert
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        db.commit()
        
        return {"ok": True, "message": "Contact updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/contacts/{contact_id}")
async def delete_emergency_contact(
    contact_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Delete an emergency contact
    """
    try:
        query = text("""
            DELETE FROM emergency_contacts
            WHERE id = :contact_id AND user_id = :user_id
            RETURNING id
        """)
        
        result = db.execute(query, {
            "contact_id": contact_id,
            "user_id": current_user["id"]
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        db.commit()
        
        return {"ok": True, "message": "Contact deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alert")
async def trigger_emergency_alert(
    request: EmergencyAlertRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Trigger an emergency alert (SOS)
    """
    try:
        # Use database function to trigger alert
        query = text("""
            SELECT trigger_emergency_alert(
                :user_id,
                :alert_type,
                :severity,
                :message,
                :location_lat,
                :location_lng,
                :location_accuracy,
                :location_address,
                NULL
            )
        """)
        
        alert_id = db.execute(query, {
            "user_id": current_user["id"],
            "alert_type": request.alertType,
            "severity": request.severity,
            "message": request.message,
            "location_lat": request.locationLat,
            "location_lng": request.locationLng,
            "location_accuracy": request.locationAccuracy,
            "location_address": request.locationAddress
        }).fetchone()[0]
        
        db.commit()
        
        return {
            "ok": True,
            "alertId": alert_id,
            "message": "Emergency alert triggered. Your contacts have been notified.",
            "alertsSent": True
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to trigger alert: {str(e)}")


@router.get("/alerts")
async def get_emergency_alerts(
    limit: int = 20,
    active_only: bool = False,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user's emergency alerts
    """
    try:
        status_filter = "AND status = 'active'" if active_only else ""
        
        query = text(f"""
            SELECT 
                id, alert_type, severity, message, 
                location_lat, location_lng, location_address,
                triggered_at, resolved_at, status
            FROM emergency_alerts
            WHERE user_id = :user_id {status_filter}
            ORDER BY triggered_at DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {
            "user_id": current_user["id"],
            "limit": limit
        }).fetchall()
        
        alerts = []
        for row in results:
            alerts.append({
                "id": row[0],
                "alertType": row[1],
                "severity": row[2],
                "message": row[3],
                "locationLat": float(row[4]) if row[4] else None,
                "locationLng": float(row[5]) if row[5] else None,
                "locationAddress": row[6],
                "triggeredAt": row[7].isoformat() if row[7] else None,
                "resolvedAt": row[8].isoformat() if row[8] else None,
                "status": row[9]
            })
        
        return {"ok": True, "alerts": alerts}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/alert/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Resolve an emergency alert
    """
    try:
        # Verify alert belongs to user
        verify_query = text("""
            SELECT user_id FROM emergency_alerts WHERE id = :alert_id
        """)
        result = db.execute(verify_query, {"alert_id": alert_id}).fetchone()
        
        if not result or result[0] != current_user["id"]:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Resolve alert
        resolve_query = text("""
            SELECT resolve_emergency_alert(:alert_id, :user_id)
        """)
        
        resolved = db.execute(resolve_query, {
            "alert_id": alert_id,
            "user_id": current_user["id"]
        }).fetchone()[0]
        
        db.commit()
        
        if resolved:
            return {"ok": True, "message": "Alert resolved"}
        else:
            return {"ok": False, "message": "Alert already resolved or not found"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sos-settings")
async def get_sos_settings(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get SOS settings
    """
    try:
        query = text("""
            SELECT 
                sos_enabled, auto_call_emergency, emergency_number, countdown_seconds,
                share_location, share_audio, share_video, auto_record_audio,
                auto_record_video, silent_mode
            FROM sos_settings
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": current_user["id"]}).fetchone()
        
        if result:
            return {
                "ok": True,
                "settings": {
                    "sosEnabled": result[0],
                    "autoCallEmergency": result[1],
                    "emergencyNumber": result[2],
                    "countdownSeconds": result[3],
                    "shareLocation": result[4],
                    "shareAudio": result[5],
                    "shareVideo": result[6],
                    "autoRecordAudio": result[7],
                    "autoRecordVideo": result[8],
                    "silentMode": result[9]
                }
            }
        else:
            # Return defaults
            return {
                "ok": True,
                "settings": {
                    "sosEnabled": True,
                    "autoCallEmergency": False,
                    "emergencyNumber": "112",
                    "countdownSeconds": 5,
                    "shareLocation": True,
                    "shareAudio": False,
                    "shareVideo": False,
                    "autoRecordAudio": True,
                    "autoRecordVideo": False,
                    "silentMode": False
                }
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sos-settings")
async def update_sos_settings(
    request: SOSSettingsRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Update SOS settings
    """
    try:
        updates = []
        params = {"user_id": current_user["id"]}
        
        if request.sosEnabled is not None:
            updates.append("sos_enabled = :sos_enabled")
            params["sos_enabled"] = request.sosEnabled
        if request.autoCallEmergency is not None:
            updates.append("auto_call_emergency = :auto_call_emergency")
            params["auto_call_emergency"] = request.autoCallEmergency
        if request.emergencyNumber:
            updates.append("emergency_number = :emergency_number")
            params["emergency_number"] = request.emergencyNumber
        if request.countdownSeconds is not None:
            updates.append("countdown_seconds = :countdown_seconds")
            params["countdown_seconds"] = request.countdownSeconds
        if request.shareLocation is not None:
            updates.append("share_location = :share_location")
            params["share_location"] = request.shareLocation
        if request.shareAudio is not None:
            updates.append("share_audio = :share_audio")
            params["share_audio"] = request.shareAudio
        if request.shareVideo is not None:
            updates.append("share_video = :share_video")
            params["share_video"] = request.shareVideo
        if request.autoRecordAudio is not None:
            updates.append("auto_record_audio = :auto_record_audio")
            params["auto_record_audio"] = request.autoRecordAudio
        if request.autoRecordVideo is not None:
            updates.append("auto_record_video = :auto_record_video")
            params["auto_record_video"] = request.autoRecordVideo
        if request.silentMode is not None:
            updates.append("silent_mode = :silent_mode")
            params["silent_mode"] = request.silentMode
        
        if not updates:
            raise HTTPException(status_code=400, detail="No settings provided")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        query = text(f"""
            INSERT INTO sos_settings (user_id)
            VALUES (:user_id)
            ON CONFLICT (user_id) DO UPDATE
            SET {', '.join(updates)}
        """)
        
        db.execute(query, params)
        db.commit()
        
        return {"ok": True, "message": "SOS settings updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
