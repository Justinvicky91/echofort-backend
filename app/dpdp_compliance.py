"""
DPDP (Digital Personal Data Protection Act, 2023) Compliance API
User consent management, data access, deletion, and portability
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import text
from .utils import get_current_user
from .deps import get_db
import json

router = APIRouter(prefix="/api/privacy", tags=["DPDP Compliance"])


class ConsentRequest(BaseModel):
    consent_type: str = Field(..., description="Type of consent: data_collection, location_tracking, call_recording, data_sharing, marketing")
    purpose: str = Field(..., description="Specific purpose for data processing")
    consent_given: bool


class PrivacyPolicyAcceptance(BaseModel):
    policy_version: str
    acceptance_method: str = "explicit"


class DataDeletionRequest(BaseModel):
    request_type: str = Field(..., description="full_account, specific_data, or anonymize")
    data_categories: Optional[List[str]] = None
    reason: Optional[str] = None


class DataExportRequest(BaseModel):
    export_format: str = Field(default="json", description="json, csv, or pdf")
    data_categories: Optional[List[str]] = None


class PrivacyPreferences(BaseModel):
    allow_analytics: bool = True
    allow_marketing: bool = False
    allow_data_sharing: bool = False
    allow_location_tracking: bool = True
    allow_call_recording: bool = True
    data_retention_preference: str = "standard"


# ============================================================================
# CONSENT MANAGEMENT
# ============================================================================

@router.post("/consent")
async def give_consent(
    request: ConsentRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Give or withdraw consent for data processing
    """
    try:
        # Deactivate previous consents of the same type
        await db.execute(text("""
            UPDATE user_consents
            SET is_active = FALSE
            WHERE user_id = :user_id
            AND consent_type = :consent_type
        """), {
            "user_id": current_user["id"],
            "consent_type": request.consent_type
        })
        
        # Insert new consent record
        query = text("""
            INSERT INTO user_consents 
            (user_id, consent_type, purpose, consent_given, consent_date, is_active)
            VALUES (:user_id, :consent_type, :purpose, :consent_given, CURRENT_TIMESTAMP, TRUE)
            RETURNING id
        """)
        
        result = db.execute(query, {
            "user_id": current_user["id"],
            "consent_type": request.consent_type,
            "purpose": request.purpose,
            "consent_given": request.consent_given
        })
        
        consent_id = result.fetchone()[0]
        db.commit()
        
        return {
            "ok": True,
            "consent_id": consent_id,
            "message": f"Consent {'given' if request.consent_given else 'withdrawn'} successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consents")
async def get_user_consents(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get all user consents
    """
    try:
        query = text("""
            SELECT consent_type, purpose, consent_given, consent_date, is_active
            FROM user_consents
            WHERE user_id = :user_id
            ORDER BY consent_date DESC
        """)
        
        results = db.execute(query, {"user_id": current_user["id"]}).fetchall()
        
        consents = []
        for row in results:
            consents.append({
                "consentType": row[0],
                "purpose": row[1],
                "consentGiven": row[2],
                "consentDate": row[3].isoformat() if row[3] else None,
                "isActive": row[4]
            })
        
        return {"ok": True, "consents": consents}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/privacy-policy/accept")
async def accept_privacy_policy(
    request: PrivacyPolicyAcceptance,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    req: Request = None
):
    """
    Record privacy policy acceptance
    """
    try:
        ip_address = req.client.host if req else None
        user_agent = req.headers.get("user-agent") if req else None
        
        query = text("""
            INSERT INTO privacy_policy_acceptances 
            (user_id, policy_version, ip_address, user_agent, acceptance_method)
            VALUES (:user_id, :policy_version, :ip_address, :user_agent, :acceptance_method)
            RETURNING id
        """)
        
        result = db.execute(query, {
            "user_id": current_user["id"],
            "policy_version": request.policy_version,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "acceptance_method": request.acceptance_method
        })
        
        acceptance_id = result.fetchone()[0]
        db.commit()
        
        return {
            "ok": True,
            "acceptance_id": acceptance_id,
            "message": "Privacy policy acceptance recorded"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATA ACCESS (RIGHT TO ACCESS)
# ============================================================================

@router.get("/my-data")
async def get_my_data(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get all personal data (Right to Access)
    """
    try:
        # Log data access
        await db.execute(text("""
            SELECT log_data_access(
                :user_id, :accessed_by, 'view', 'all_data', 'User requested data access'
            )
        """), {
            "user_id": current_user["id"],
            "accessed_by": current_user["id"]
        })
        
        # Get profile data
        profile = db.execute(text("""
            SELECT name, identity, email, created_at
            FROM users WHERE id = :user_id
        """), {"user_id": current_user["id"]}).fetchone()
        
        # Get consents
        consents = db.execute(text("""
            SELECT consent_type, consent_given, consent_date
            FROM user_consents
            WHERE user_id = :user_id AND is_active = TRUE
        """), {"user_id": current_user["id"]}).fetchall()
        
        # Get location data count
        location_count = db.execute(text("""
            SELECT COUNT(*) FROM gps_locations WHERE user_id = :user_id
        """), {"user_id": current_user["id"]}).fetchone()[0]
        
        # Get call analysis count
        call_count = db.execute(text("""
            SELECT COUNT(*) FROM realtime_call_sessions WHERE user_id = :user_id
        """), {"user_id": current_user["id"]}).fetchone()[0]
        
        db.commit()
        
        return {
            "ok": True,
            "data": {
                "profile": {
                    "name": profile[0] if profile else None,
                    "phone": profile[1] if profile else None,
                    "email": profile[2] if profile else None,
                    "memberSince": profile[3].isoformat() if profile and profile[3] else None
                },
                "consents": [
                    {
                        "type": c[0],
                        "given": c[1],
                        "date": c[2].isoformat() if c[2] else None
                    } for c in consents
                ],
                "dataCategories": {
                    "locationRecords": location_count,
                    "callAnalysisRecords": call_count
                }
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATA DELETION (RIGHT TO BE FORGOTTEN)
# ============================================================================

@router.post("/delete-data")
async def request_data_deletion(
    request: DataDeletionRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Request data deletion (Right to be Forgotten)
    """
    try:
        query = text("""
            INSERT INTO data_deletion_requests 
            (user_id, request_type, data_categories, reason, status)
            VALUES (:user_id, :request_type, :data_categories, :reason, 'pending')
            RETURNING id
        """)
        
        result = db.execute(query, {
            "user_id": current_user["id"],
            "request_type": request.request_type,
            "data_categories": json.dumps(request.data_categories) if request.data_categories else None,
            "reason": request.reason
        })
        
        request_id = result.fetchone()[0]
        db.commit()
        
        return {
            "ok": True,
            "request_id": request_id,
            "message": "Data deletion request submitted. Will be processed within 30 days.",
            "status": "pending"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deletion-requests")
async def get_deletion_requests(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user's data deletion requests
    """
    try:
        query = text("""
            SELECT id, request_type, data_categories, reason, status, requested_at, completed_at
            FROM data_deletion_requests
            WHERE user_id = :user_id
            ORDER BY requested_at DESC
        """)
        
        results = db.execute(query, {"user_id": current_user["id"]}).fetchall()
        
        requests = []
        for row in results:
            requests.append({
                "id": row[0],
                "requestType": row[1],
                "dataCategories": json.loads(row[2]) if row[2] else None,
                "reason": row[3],
                "status": row[4],
                "requestedAt": row[5].isoformat() if row[5] else None,
                "completedAt": row[6].isoformat() if row[6] else None
            })
        
        return {"ok": True, "requests": requests}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATA PORTABILITY (RIGHT TO DATA PORTABILITY)
# ============================================================================

@router.post("/export-data")
async def request_data_export(
    request: DataExportRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Request data export (Data Portability)
    """
    try:
        # Set expiry to 7 days from now
        expires_at = datetime.now() + timedelta(days=7)
        
        query = text("""
            INSERT INTO data_export_requests 
            (user_id, export_format, data_categories, status, expires_at)
            VALUES (:user_id, :export_format, :data_categories, 'pending', :expires_at)
            RETURNING id
        """)
        
        result = db.execute(query, {
            "user_id": current_user["id"],
            "export_format": request.export_format,
            "data_categories": json.dumps(request.data_categories) if request.data_categories else None,
            "expires_at": expires_at
        })
        
        request_id = result.fetchone()[0]
        db.commit()
        
        return {
            "ok": True,
            "request_id": request_id,
            "message": f"Data export request submitted. File will be ready within 24 hours.",
            "status": "pending",
            "expiresAt": expires_at.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-requests")
async def get_export_requests(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user's data export requests
    """
    try:
        query = text("""
            SELECT id, export_format, data_categories, status, file_url, 
                   requested_at, completed_at, expires_at, downloaded_at
            FROM data_export_requests
            WHERE user_id = :user_id
            ORDER BY requested_at DESC
        """)
        
        results = db.execute(query, {"user_id": current_user["id"]}).fetchall()
        
        requests = []
        for row in results:
            requests.append({
                "id": row[0],
                "exportFormat": row[1],
                "dataCategories": json.loads(row[2]) if row[2] else None,
                "status": row[3],
                "fileUrl": row[4],
                "requestedAt": row[5].isoformat() if row[5] else None,
                "completedAt": row[6].isoformat() if row[6] else None,
                "expiresAt": row[7].isoformat() if row[7] else None,
                "downloadedAt": row[8].isoformat() if row[8] else None
            })
        
        return {"ok": True, "requests": requests}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PRIVACY PREFERENCES
# ============================================================================

@router.put("/preferences")
async def update_privacy_preferences(
    preferences: PrivacyPreferences,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Update user privacy preferences
    """
    try:
        query = text("""
            INSERT INTO user_privacy_preferences 
            (user_id, allow_analytics, allow_marketing, allow_data_sharing, 
             allow_location_tracking, allow_call_recording, data_retention_preference)
            VALUES (:user_id, :analytics, :marketing, :sharing, :location, :recording, :retention)
            ON CONFLICT (user_id) DO UPDATE SET
                allow_analytics = EXCLUDED.allow_analytics,
                allow_marketing = EXCLUDED.allow_marketing,
                allow_data_sharing = EXCLUDED.allow_data_sharing,
                allow_location_tracking = EXCLUDED.allow_location_tracking,
                allow_call_recording = EXCLUDED.allow_call_recording,
                data_retention_preference = EXCLUDED.data_retention_preference,
                updated_at = CURRENT_TIMESTAMP
        """)
        
        db.execute(query, {
            "user_id": current_user["id"],
            "analytics": preferences.allow_analytics,
            "marketing": preferences.allow_marketing,
            "sharing": preferences.allow_data_sharing,
            "location": preferences.allow_location_tracking,
            "recording": preferences.allow_call_recording,
            "retention": preferences.data_retention_preference
        })
        
        db.commit()
        
        return {
            "ok": True,
            "message": "Privacy preferences updated successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences")
async def get_privacy_preferences(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get user privacy preferences
    """
    try:
        query = text("""
            SELECT allow_analytics, allow_marketing, allow_data_sharing,
                   allow_location_tracking, allow_call_recording, data_retention_preference
            FROM user_privacy_preferences
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": current_user["id"]}).fetchone()
        
        if not result:
            # Return defaults if no preferences set
            return {
                "ok": True,
                "preferences": {
                    "allowAnalytics": True,
                    "allowMarketing": False,
                    "allowDataSharing": False,
                    "allowLocationTracking": True,
                    "allowCallRecording": True,
                    "dataRetentionPreference": "standard"
                }
            }
        
        return {
            "ok": True,
            "preferences": {
                "allowAnalytics": result[0],
                "allowMarketing": result[1],
                "allowDataSharing": result[2],
                "allowLocationTracking": result[3],
                "allowCallRecording": result[4],
                "dataRetentionPreference": result[5]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATA RETENTION POLICIES (READ-ONLY)
# ============================================================================

@router.get("/retention-policies")
async def get_retention_policies(db=Depends(get_db)):
    """
    Get data retention policies
    """
    try:
        query = text("""
            SELECT data_category, retention_days, description, legal_basis
            FROM data_retention_policies
            ORDER BY data_category
        """)
        
        results = db.execute(query).fetchall()
        
        policies = []
        for row in results:
            policies.append({
                "dataCategory": row[0],
                "retentionDays": row[1],
                "description": row[2],
                "legalBasis": row[3]
            })
        
        return {"ok": True, "policies": policies}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATA PROCESSING ACTIVITIES (READ-ONLY)
# ============================================================================

@router.get("/processing-activities")
async def get_processing_activities(db=Depends(get_db)):
    """
    Get data processing activities (transparency)
    """
    try:
        query = text("""
            SELECT activity_name, data_categories, processing_purpose, 
                   legal_basis, data_recipients, retention_period, security_measures
            FROM data_processing_activities
            WHERE is_active = TRUE
            ORDER BY activity_name
        """)
        
        results = db.execute(query).fetchall()
        
        activities = []
        for row in results:
            activities.append({
                "activityName": row[0],
                "dataCategories": json.loads(row[1]) if row[1] else [],
                "processingPurpose": row[2],
                "legalBasis": row[3],
                "dataRecipients": row[4],
                "retentionPeriod": row[5],
                "securityMeasures": row[6]
            })
        
        return {"ok": True, "activities": activities}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
