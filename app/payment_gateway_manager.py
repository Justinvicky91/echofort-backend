# app/payment_gateway_manager.py - Payment Gateway Management (Super Admin)
"""
Payment Gateway Management System
Super Admin can configure multiple payment gateways without code deployment
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import text
from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel
from .utils import get_current_user
import os
import json
from cryptography.fernet import Fernet

router = APIRouter(prefix="/api/admin/payment-gateways", tags=["Payment Gateway Management"])

# Encryption key for storing sensitive credentials
ENCRYPTION_KEY = os.getenv("PAYMENT_CREDENTIALS_ENCRYPTION_KEY", Fernet.generate_key())
cipher = Fernet(ENCRYPTION_KEY)


class PaymentGatewayConfig(BaseModel):
    gateway_name: Literal["razorpay", "stripe", "paypal", "square", "adyen", "alipay", "wechat"]
    enabled: bool
    test_mode: bool
    api_key: str
    secret_key: str
    webhook_secret: Optional[str] = None
    supported_currencies: List[str]
    supported_regions: List[str]
    priority: int  # 1 = highest priority


class GatewayUpdate(BaseModel):
    gateway_name: str
    enabled: Optional[bool] = None
    test_mode: Optional[bool] = None
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    webhook_secret: Optional[str] = None


def encrypt_credential(credential: str) -> str:
    """Encrypt sensitive credentials"""
    return cipher.encrypt(credential.encode()).decode()


def decrypt_credential(encrypted: str) -> str:
    """Decrypt sensitive credentials"""
    return cipher.decrypt(encrypted.encode()).decode()


def verify_super_admin(current_user: dict) -> bool:
    """Verify user is super admin"""
    return current_user.get("role") == "super_admin" or current_user.get("email") == os.getenv("OWNER_EMAIL")


@router.post("/configure")
async def configure_payment_gateway(
    request: Request,
    config: PaymentGatewayConfig,
    current_user: dict = Depends(get_current_user)
):
    """
    Configure a payment gateway (Super Admin only)
    Credentials are encrypted before storage
    """
    try:
        # Verify super admin
        if not verify_super_admin(current_user):
            raise HTTPException(403, "Super Admin access required")
        
        db = request.app.state.db
        
        # Encrypt sensitive credentials
        encrypted_api_key = encrypt_credential(config.api_key)
        encrypted_secret_key = encrypt_credential(config.secret_key)
        encrypted_webhook_secret = encrypt_credential(config.webhook_secret) if config.webhook_secret else None
        
        # Check if gateway already exists
        existing = (await db.execute(text("""
            SELECT id FROM payment_gateways WHERE gateway_name = :name
        """), {"name": config.gateway_name})).fetchone()
        
        if existing:
            # Update existing gateway
            await db.execute(text("""
                UPDATE payment_gateways SET
                    enabled = :enabled,
                    test_mode = :test_mode,
                    api_key_encrypted = :api_key,
                    secret_key_encrypted = :secret_key,
                    webhook_secret_encrypted = :webhook_secret,
                    supported_currencies = :currencies,
                    supported_regions = :regions,
                    priority = :priority,
                    updated_at = NOW(),
                    updated_by = :admin_id
                WHERE gateway_name = :name
            """), {
                "name": config.gateway_name,
                "enabled": config.enabled,
                "test_mode": config.test_mode,
                "api_key": encrypted_api_key,
                "secret_key": encrypted_secret_key,
                "webhook_secret": encrypted_webhook_secret,
                "currencies": json.dumps(config.supported_currencies),
                "regions": json.dumps(config.supported_regions),
                "priority": config.priority,
                "admin_id": current_user["id"]
            })
            
            action = "updated"
        else:
            # Insert new gateway
            await db.execute(text("""
                INSERT INTO payment_gateways (
                    gateway_name, enabled, test_mode,
                    api_key_encrypted, secret_key_encrypted, webhook_secret_encrypted,
                    supported_currencies, supported_regions, priority,
                    created_at, created_by
                ) VALUES (
                    :name, :enabled, :test_mode,
                    :api_key, :secret_key, :webhook_secret,
                    :currencies, :regions, :priority,
                    NOW(), :admin_id
                )
            """), {
                "name": config.gateway_name,
                "enabled": config.enabled,
                "test_mode": config.test_mode,
                "api_key": encrypted_api_key,
                "secret_key": encrypted_secret_key,
                "webhook_secret": encrypted_webhook_secret,
                "currencies": json.dumps(config.supported_currencies),
                "regions": json.dumps(config.supported_regions),
                "priority": config.priority,
                "admin_id": current_user["id"]
            })
            
            action = "configured"
        
        # Log the action
        await db.execute(text("""
            INSERT INTO admin_audit_log (
                admin_id, action, details, created_at
            ) VALUES (
                :admin_id, :action, :details, NOW()
            )
        """), {
            "admin_id": current_user["id"],
            "action": f"payment_gateway_{action}",
            "details": json.dumps({
                "gateway": config.gateway_name,
                "enabled": config.enabled,
                "test_mode": config.test_mode,
                "regions": config.supported_regions
            })
        })
        
        return {
            "ok": True,
            "message": f"Payment gateway {config.gateway_name} {action} successfully",
            "gateway": config.gateway_name,
            "enabled": config.enabled,
            "test_mode": config.test_mode
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Configuration error: {str(e)}")


@router.get("/list")
async def list_payment_gateways(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    List all configured payment gateways (Super Admin only)
    Credentials are masked for security
    """
    try:
        # Verify super admin
        if not verify_super_admin(current_user):
            raise HTTPException(403, "Super Admin access required")
        
        db = request.app.state.db
        
        gateways = (await db.execute(text("""
            SELECT 
                id, gateway_name, enabled, test_mode,
                supported_currencies, supported_regions, priority,
                created_at, updated_at
            FROM payment_gateways
            ORDER BY priority ASC, gateway_name ASC
        """))).fetchall()
        
        return {
            "ok": True,
            "total": len(gateways),
            "gateways": [
                {
                    "id": g[0],
                    "gateway_name": g[1],
                    "enabled": g[2],
                    "test_mode": g[3],
                    "supported_currencies": json.loads(g[4]) if g[4] else [],
                    "supported_regions": json.loads(g[5]) if g[5] else [],
                    "priority": g[6],
                    "configured_at": str(g[7]),
                    "last_updated": str(g[8]) if g[8] else None
                }
                for g in gateways
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"List error: {str(e)}")


@router.get("/credentials/{gateway_name}")
async def get_gateway_credentials(
    request: Request,
    gateway_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get decrypted credentials for a gateway (Super Admin only)
    Use with caution - only for editing
    """
    try:
        # Verify super admin
        if not verify_super_admin(current_user):
            raise HTTPException(403, "Super Admin access required")
        
        db = request.app.state.db
        
        gateway = (await db.execute(text("""
            SELECT 
                api_key_encrypted, secret_key_encrypted, webhook_secret_encrypted
            FROM payment_gateways
            WHERE gateway_name = :name
        """), {"name": gateway_name})).fetchone()
        
        if not gateway:
            raise HTTPException(404, "Payment gateway not found")
        
        # Decrypt credentials
        api_key = decrypt_credential(gateway[0])
        secret_key = decrypt_credential(gateway[1])
        webhook_secret = decrypt_credential(gateway[2]) if gateway[2] else None
        
        # Mask credentials (show first 4 and last 4 characters)
        def mask_credential(cred: str) -> str:
            if len(cred) <= 8:
                return "*" * len(cred)
            return cred[:4] + "*" * (len(cred) - 8) + cred[-4:]
        
        return {
            "ok": True,
            "gateway_name": gateway_name,
            "api_key": api_key,  # Full key for editing
            "secret_key": secret_key,  # Full key for editing
            "webhook_secret": webhook_secret,
            "api_key_masked": mask_credential(api_key),
            "secret_key_masked": mask_credential(secret_key)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Credentials fetch error: {str(e)}")


@router.patch("/toggle/{gateway_name}")
async def toggle_gateway(
    request: Request,
    gateway_name: str,
    enabled: bool,
    current_user: dict = Depends(get_current_user)
):
    """
    Enable/disable a payment gateway (Super Admin only)
    """
    try:
        # Verify super admin
        if not verify_super_admin(current_user):
            raise HTTPException(403, "Super Admin access required")
        
        db = request.app.state.db
        
        await db.execute(text("""
            UPDATE payment_gateways
            SET enabled = :enabled, updated_at = NOW()
            WHERE gateway_name = :name
        """), {"enabled": enabled, "name": gateway_name})
        
        # Log the action
        await db.execute(text("""
            INSERT INTO admin_audit_log (
                admin_id, action, details, created_at
            ) VALUES (
                :admin_id, :action, :details, NOW()
            )
        """), {
            "admin_id": current_user["id"],
            "action": "payment_gateway_toggled",
            "details": json.dumps({
                "gateway": gateway_name,
                "enabled": enabled
            })
        })
        
        return {
            "ok": True,
            "message": f"Payment gateway {gateway_name} {'enabled' if enabled else 'disabled'}",
            "gateway_name": gateway_name,
            "enabled": enabled
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Toggle error: {str(e)}")


@router.get("/active")
async def get_active_gateways(
    request: Request,
    region: Optional[str] = None,
    currency: Optional[str] = None
):
    """
    Get active payment gateways for a region/currency
    Public endpoint for frontend
    """
    try:
        db = request.app.state.db
        
        query = """
            SELECT 
                gateway_name, test_mode, supported_currencies, supported_regions, priority
            FROM payment_gateways
            WHERE enabled = TRUE
        """
        
        params = {}
        
        if region:
            query += " AND supported_regions @> :region::jsonb"
            params["region"] = json.dumps([region])
        
        if currency:
            query += " AND supported_currencies @> :currency::jsonb"
            params["currency"] = json.dumps([currency])
        
        query += " ORDER BY priority ASC"
        
        gateways = (await db.execute(text(query), params)).fetchall()
        
        return {
            "ok": True,
            "region": region,
            "currency": currency,
            "gateways": [
                {
                    "gateway_name": g[0],
                    "test_mode": g[1],
                    "supported_currencies": json.loads(g[2]) if g[2] else [],
                    "supported_regions": json.loads(g[3]) if g[3] else [],
                    "priority": g[4]
                }
                for g in gateways
            ]
        }
    
    except Exception as e:
        raise HTTPException(500, f"Active gateways error: {str(e)}")


@router.delete("/delete/{gateway_name}")
async def delete_gateway(
    request: Request,
    gateway_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a payment gateway configuration (Super Admin only)
    """
    try:
        # Verify super admin
        if not verify_super_admin(current_user):
            raise HTTPException(403, "Super Admin access required")
        
        db = request.app.state.db
        
        await db.execute(text("""
            DELETE FROM payment_gateways WHERE gateway_name = :name
        """), {"name": gateway_name})
        
        # Log the action
        await db.execute(text("""
            INSERT INTO admin_audit_log (
                admin_id, action, details, created_at
            ) VALUES (
                :admin_id, :action, :details, NOW()
            )
        """), {
            "admin_id": current_user["id"],
            "action": "payment_gateway_deleted",
            "details": json.dumps({"gateway": gateway_name})
        })
        
        return {
            "ok": True,
            "message": f"Payment gateway {gateway_name} deleted",
            "gateway_name": gateway_name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Deletion error: {str(e)}")


@router.get("/test-connection/{gateway_name}")
async def test_gateway_connection(
    request: Request,
    gateway_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Test payment gateway connection (Super Admin only)
    """
    try:
        # Verify super admin
        if not verify_super_admin(current_user):
            raise HTTPException(403, "Super Admin access required")
        
        db = request.app.state.db
        
        # Get gateway credentials
        gateway = (await db.execute(text("""
            SELECT api_key_encrypted, secret_key_encrypted, test_mode
            FROM payment_gateways
            WHERE gateway_name = :name AND enabled = TRUE
        """), {"name": gateway_name})).fetchone()
        
        if not gateway:
            raise HTTPException(404, "Payment gateway not found or disabled")
        
        # Decrypt credentials
        api_key = decrypt_credential(gateway[0])
        secret_key = decrypt_credential(gateway[1])
        test_mode = gateway[2]
        
        # Test connection based on gateway type
        if gateway_name == "razorpay":
            import razorpay
            client = razorpay.Client(auth=(api_key, secret_key))
            # Test API call
            try:
                client.payment.fetch_all()
                status = "success"
                message = "Razorpay connection successful"
            except Exception as e:
                status = "failed"
                message = f"Razorpay connection failed: {str(e)}"
        
        elif gateway_name == "stripe":
            import stripe
            stripe.api_key = secret_key
            # Test API call
            try:
                stripe.Customer.list(limit=1)
                status = "success"
                message = "Stripe connection successful"
            except Exception as e:
                status = "failed"
                message = f"Stripe connection failed: {str(e)}"
        
        else:
            status = "not_implemented"
            message = f"Connection test not implemented for {gateway_name}"
        
        return {
            "ok": status == "success",
            "gateway_name": gateway_name,
            "status": status,
            "message": message,
            "test_mode": test_mode
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Connection test error: {str(e)}")

