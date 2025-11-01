"""
Mobile User Profile API
User profile management for mobile app
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime, date
from sqlalchemy import text
from .deps import get_db, get_current_user
import base64

router = APIRouter(prefix="/api/mobile/profile", tags=["Mobile User Profile"])


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    dateOfBirth: Optional[date] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    timezone: Optional[str] = None


class PreferencesUpdateRequest(BaseModel):
    languagePreference: Optional[str] = None
    themePreference: Optional[str] = None
    notificationSound: Optional[bool] = None
    vibrationEnabled: Optional[bool] = None
    biometricEnabled: Optional[bool] = None
    autoBackupEnabled: Optional[bool] = None
    dataSaverMode: Optional[bool] = None


class AppPreferencesUpdateRequest(BaseModel):
    defaultCallAction: Optional[str] = None
    autoRecordCalls: Optional[bool] = None
    autoScanSms: Optional[bool] = None
    autoCheckUrls: Optional[bool] = None
    showCallerId: Optional[bool] = None
    blockUnknownCallers: Optional[bool] = None
    blockPrivateNumbers: Optional[bool] = None
    enableCallRecordingNotification: Optional[bool] = None
    enableScamPrediction: Optional[bool] = None
    enableAiAssistant: Optional[bool] = None


class FeedbackRequest(BaseModel):
    feedbackType: str
    category: Optional[str] = None
    subject: Optional[str] = None
    message: str
    rating: Optional[int] = Field(None, ge=1, le=5)


@router.get("")
async def get_profile(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get complete user profile
    """
    try:
        # Get basic user info
        user_query = text("""
            SELECT id, username, email, phone, created_at
            FROM users
            WHERE id = :user_id
        """)
        
        user = db.execute(user_query, {"user_id": current_user["id"]}).fetchone()
        
        # Get extended profile
        profile_query = text("""
            SELECT 
                avatar_url, bio, date_of_birth, gender, country, city, timezone,
                language_preference, theme_preference, notification_sound, 
                vibration_enabled, biometric_enabled, auto_backup_enabled, data_saver_mode
            FROM user_profiles_mobile
            WHERE user_id = :user_id
        """)
        
        profile = db.execute(profile_query, {"user_id": current_user["id"]}).fetchone()
        
        # Get statistics
        stats_query = text("""
            SELECT 
                total_scams_blocked, total_calls_protected, total_sms_scanned,
                total_urls_checked, total_reports_submitted, protection_score,
                community_reputation, days_active
            FROM user_statistics_summary
            WHERE user_id = :user_id
        """)
        
        stats = db.execute(stats_query, {"user_id": current_user["id"]}).fetchone()
        
        result = {
            "ok": True,
            "profile": {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "phone": user[3],
                "createdAt": user[4].isoformat() if user[4] else None,
                "avatarUrl": profile[0] if profile else None,
                "bio": profile[1] if profile else None,
                "dateOfBirth": profile[2].isoformat() if profile and profile[2] else None,
                "gender": profile[3] if profile else None,
                "country": profile[4] if profile else None,
                "city": profile[5] if profile else None,
                "timezone": profile[6] if profile else None,
                "languagePreference": profile[7] if profile else "en",
                "themePreference": profile[8] if profile else "light",
                "notificationSound": profile[9] if profile else True,
                "vibrationEnabled": profile[10] if profile else True,
                "biometricEnabled": profile[11] if profile else False,
                "autoBackupEnabled": profile[12] if profile else True,
                "dataSaverMode": profile[13] if profile else False
            },
            "statistics": {
                "totalScamsBlocked": stats[0] if stats else 0,
                "totalCallsProtected": stats[1] if stats else 0,
                "totalSmsScanned": stats[2] if stats else 0,
                "totalUrlsChecked": stats[3] if stats else 0,
                "totalReportsSubmitted": stats[4] if stats else 0,
                "protectionScore": stats[5] if stats else 0,
                "communityReputation": stats[6] if stats else 50,
                "daysActive": stats[7] if stats else 0
            }
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("")
async def update_profile(
    request: ProfileUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Update user profile
    """
    try:
        # Update basic user info if provided
        if request.name or request.email or request.phone:
            user_updates = []
            user_params = {"user_id": current_user["id"]}
            
            if request.name:
                user_updates.append("username = :username")
                user_params["username"] = request.name
            if request.email:
                user_updates.append("email = :email")
                user_params["email"] = request.email
            if request.phone:
                user_updates.append("phone = :phone")
                user_params["phone"] = request.phone
            
            if user_updates:
                user_query = text(f"""
                    UPDATE users
                    SET {', '.join(user_updates)}
                    WHERE id = :user_id
                """)
                db.execute(user_query, user_params)
        
        # Update extended profile
        profile_updates = []
        profile_params = {"user_id": current_user["id"]}
        
        if request.bio is not None:
            profile_updates.append("bio = :bio")
            profile_params["bio"] = request.bio
        if request.dateOfBirth:
            profile_updates.append("date_of_birth = :dob")
            profile_params["dob"] = request.dateOfBirth
        if request.gender:
            profile_updates.append("gender = :gender")
            profile_params["gender"] = request.gender
        if request.country:
            profile_updates.append("country = :country")
            profile_params["country"] = request.country
        if request.city:
            profile_updates.append("city = :city")
            profile_params["city"] = request.city
        if request.timezone:
            profile_updates.append("timezone = :timezone")
            profile_params["timezone"] = request.timezone
        
        if profile_updates:
            profile_updates.append("updated_at = CURRENT_TIMESTAMP")
            
            profile_query = text(f"""
                INSERT INTO user_profiles_mobile (user_id)
                VALUES (:user_id)
                ON CONFLICT (user_id) DO UPDATE
                SET {', '.join(profile_updates)}
            """)
            db.execute(profile_query, profile_params)
        
        # Log activity
        db.execute(text("SELECT log_user_activity(:user_id, 'profile_update', NULL, NULL, NULL)"),
                  {"user_id": current_user["id"]})
        
        db.commit()
        
        return {"ok": True, "message": "Profile updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/preferences")
async def update_preferences(
    request: PreferencesUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Update user preferences
    """
    try:
        updates = []
        params = {"user_id": current_user["id"]}
        
        if request.languagePreference:
            updates.append("language_preference = :lang")
            params["lang"] = request.languagePreference
        if request.themePreference:
            updates.append("theme_preference = :theme")
            params["theme"] = request.themePreference
        if request.notificationSound is not None:
            updates.append("notification_sound = :notif_sound")
            params["notif_sound"] = request.notificationSound
        if request.vibrationEnabled is not None:
            updates.append("vibration_enabled = :vibration")
            params["vibration"] = request.vibrationEnabled
        if request.biometricEnabled is not None:
            updates.append("biometric_enabled = :biometric")
            params["biometric"] = request.biometricEnabled
        if request.autoBackupEnabled is not None:
            updates.append("auto_backup_enabled = :backup")
            params["backup"] = request.autoBackupEnabled
        if request.dataSaverMode is not None:
            updates.append("data_saver_mode = :data_saver")
            params["data_saver"] = request.dataSaverMode
        
        if not updates:
            raise HTTPException(status_code=400, detail="No preferences provided")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        query = text(f"""
            INSERT INTO user_profiles_mobile (user_id)
            VALUES (:user_id)
            ON CONFLICT (user_id) DO UPDATE
            SET {', '.join(updates)}
        """)
        
        db.execute(query, params)
        db.commit()
        
        return {"ok": True, "message": "Preferences updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/app-preferences")
async def get_app_preferences(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get app-specific preferences
    """
    try:
        query = text("""
            SELECT 
                default_call_action, auto_record_calls, auto_scan_sms, auto_check_urls,
                show_caller_id, block_unknown_callers, block_private_numbers,
                enable_call_recording_notification, enable_scam_prediction, enable_ai_assistant
            FROM user_app_preferences
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": current_user["id"]}).fetchone()
        
        if result:
            return {
                "ok": True,
                "preferences": {
                    "defaultCallAction": result[0],
                    "autoRecordCalls": result[1],
                    "autoScanSms": result[2],
                    "autoCheckUrls": result[3],
                    "showCallerId": result[4],
                    "blockUnknownCallers": result[5],
                    "blockPrivateNumbers": result[6],
                    "enableCallRecordingNotification": result[7],
                    "enableScamPrediction": result[8],
                    "enableAiAssistant": result[9]
                }
            }
        else:
            # Return defaults
            return {
                "ok": True,
                "preferences": {
                    "defaultCallAction": "ask",
                    "autoRecordCalls": False,
                    "autoScanSms": True,
                    "autoCheckUrls": True,
                    "showCallerId": True,
                    "blockUnknownCallers": False,
                    "blockPrivateNumbers": False,
                    "enableCallRecordingNotification": True,
                    "enableScamPrediction": True,
                    "enableAiAssistant": True
                }
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/app-preferences")
async def update_app_preferences(
    request: AppPreferencesUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Update app-specific preferences
    """
    try:
        updates = []
        params = {"user_id": current_user["id"]}
        
        if request.defaultCallAction:
            updates.append("default_call_action = :default_call_action")
            params["default_call_action"] = request.defaultCallAction
        if request.autoRecordCalls is not None:
            updates.append("auto_record_calls = :auto_record_calls")
            params["auto_record_calls"] = request.autoRecordCalls
        if request.autoScanSms is not None:
            updates.append("auto_scan_sms = :auto_scan_sms")
            params["auto_scan_sms"] = request.autoScanSms
        if request.autoCheckUrls is not None:
            updates.append("auto_check_urls = :auto_check_urls")
            params["auto_check_urls"] = request.autoCheckUrls
        if request.showCallerId is not None:
            updates.append("show_caller_id = :show_caller_id")
            params["show_caller_id"] = request.showCallerId
        if request.blockUnknownCallers is not None:
            updates.append("block_unknown_callers = :block_unknown_callers")
            params["block_unknown_callers"] = request.blockUnknownCallers
        if request.blockPrivateNumbers is not None:
            updates.append("block_private_numbers = :block_private_numbers")
            params["block_private_numbers"] = request.blockPrivateNumbers
        if request.enableCallRecordingNotification is not None:
            updates.append("enable_call_recording_notification = :enable_call_recording_notification")
            params["enable_call_recording_notification"] = request.enableCallRecordingNotification
        if request.enableScamPrediction is not None:
            updates.append("enable_scam_prediction = :enable_scam_prediction")
            params["enable_scam_prediction"] = request.enableScamPrediction
        if request.enableAiAssistant is not None:
            updates.append("enable_ai_assistant = :enable_ai_assistant")
            params["enable_ai_assistant"] = request.enableAiAssistant
        
        if not updates:
            raise HTTPException(status_code=400, detail="No preferences provided")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        query = text(f"""
            INSERT INTO user_app_preferences (user_id)
            VALUES (:user_id)
            ON CONFLICT (user_id) DO UPDATE
            SET {', '.join(updates)}
        """)
        
        db.execute(query, params)
        db.commit()
        
        return {"ok": True, "message": "App preferences updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Submit user feedback
    """
    try:
        query = text("""
            INSERT INTO user_feedback 
            (user_id, feedback_type, category, subject, message, rating)
            VALUES (:user_id, :feedback_type, :category, :subject, :message, :rating)
            RETURNING id
        """)
        
        feedback_id = db.execute(query, {
            "user_id": current_user["id"],
            "feedback_type": request.feedbackType,
            "category": request.category,
            "subject": request.subject,
            "message": request.message,
            "rating": request.rating
        }).fetchone()[0]
        
        db.commit()
        
        return {
            "ok": True,
            "feedbackId": feedback_id,
            "message": "Thank you for your feedback!"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/achievements")
async def get_achievements(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user achievements
    """
    try:
        query = text("""
            SELECT 
                achievement_type,
                achievement_name,
                achievement_description,
                icon_url,
                earned_at
            FROM user_achievements
            WHERE user_id = :user_id
            ORDER BY earned_at DESC
        """)
        
        results = db.execute(query, {"user_id": current_user["id"]}).fetchall()
        
        achievements = []
        for row in results:
            achievements.append({
                "type": row[0],
                "name": row[1],
                "description": row[2],
                "iconUrl": row[3],
                "earnedAt": row[4].isoformat() if row[4] else None
            })
        
        return {"ok": True, "achievements": achievements}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity-log")
async def get_activity_log(
    limit: int = 50,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user activity log
    """
    try:
        query = text("""
            SELECT 
                activity_type,
                activity_details,
                timestamp
            FROM user_activity_log
            WHERE user_id = :user_id
            ORDER BY timestamp DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {
            "user_id": current_user["id"],
            "limit": limit
        }).fetchall()
        
        activities = []
        for row in results:
            activities.append({
                "activityType": row[0],
                "activityDetails": row[1],
                "timestamp": row[2].isoformat() if row[2] else None
            })
        
        return {"ok": True, "activities": activities}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh-statistics")
async def refresh_statistics(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Refresh user statistics
    """
    try:
        db.execute(text("SELECT update_user_statistics(:user_id)"),
                  {"user_id": current_user["id"]})
        db.commit()
        
        return {"ok": True, "message": "Statistics refreshed"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
