from fastapi import APIRouter, UploadFile, File
from PIL import Image
import io, numpy as np

router = APIRouter(prefix="/ai/media", tags=["ai"])

@router.post("/scan")
async def media_scan(file: UploadFile = File(...)):
    data = await file.read()
    img = Image.open(io.BytesIO(data)).convert("RGB")
    arr = np.asarray(img)
    suspicious = bool(arr.std() < 12)
    risk = 0.9 if suspicious else 0.2
    return {"risk": risk, "flags": ["baseline-only"], "recommendation": "If risk >0.7, warn user and require manual confirmation."}
