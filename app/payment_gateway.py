"""Payment gateway switcher"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import os

router = APIRouter(prefix="/api/payment-gateway", tags=["Payment Gateway"])

class GatewayConfig(BaseModel):
    gateway_name: Literal["razorpay", "stripe", "paypal"]
    api_key: str
    api_secret: str

@router.post("/configure")
async def configure_gateway(request: Request, config: GatewayConfig, admin_key: str):
    if admin_key != os.getenv("ADMIN_KEY"): raise HTTPException(403, "Unauthorized")
    await request.app.state.db.execute("UPDATE payment_gateways SET is_active = FALSE", {})
    await request.app.state.db.execute("""
        INSERT INTO payment_gateways (gateway_name, api_key, api_secret, is_active)
        VALUES (:name, :key, :secret, TRUE)
        ON CONFLICT (gateway_name) DO UPDATE SET api_key = :key, is_active = TRUE
    """, {"name": config.gateway_name, "key": config.api_key, "secret": config.api_secret})
    return {"success": True}

@router.get("/active")
async def get_active_gateway(request: Request, admin_key: str):
    if admin_key != os.getenv("ADMIN_KEY"): raise HTTPException(403, "Unauthorized")
    r = await request.app.state.db.execute("SELECT gateway_name FROM payment_gateways WHERE is_active = TRUE LIMIT 1", {})
    row = r.fetchone()
    return {"gateway": row[0] if row else None}
