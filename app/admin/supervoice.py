from fastapi import APIRouter, UploadFile, File, HTTPException
from ..utils import is_admin

router = APIRouter(prefix="/superadmin/ai", tags=["admin"])

@router.post("/voice")
async def super_voice(user_id: int, audio: UploadFile = File(...)):
    if not is_admin(user_id):
        raise HTTPException(403, "Not admin")
    return {"ok": True, "actions": ["approve_latest_push", "set_ai_cost_cap:1800", "switch_gateway:razorpay"]}
