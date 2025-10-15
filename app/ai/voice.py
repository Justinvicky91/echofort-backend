from fastapi import APIRouter, UploadFile, File, Depends, Request
import numpy as np, soundfile as sf, librosa, io
from ..ai.guard import ensure_ai_budget, record_ai_cost
from ..deps import get_settings

router = APIRouter(prefix="/ai/voice", tags=["ai"])

def trust_from_signal(y: np.ndarray, sr: int) -> float:
    y = librosa.util.normalize(y)
    rms = librosa.feature.rms(y=y).mean()
    cent = librosa.feature.spectral_centroid(y=y, sr=sr).std()
    zcr = librosa.feature.zero_crossing_rate(y).mean()
    score = 10.0 - (cent/1000.0) - (zcr*5.0) + (rms*8.0)
    return float(np.clip(score, 0.0, 10.0))

@router.post("/score")
async def voice_score(file: UploadFile = File(...), request: Request = None, settings=Depends(get_settings)):
    await ensure_ai_budget(request, estimated_rs=0.25)
    data = await file.read()
    with io.BytesIO(data) as bio:
        y, sr = sf.read(bio)
    if hasattr(y, "ndim") and y.ndim > 1:
        y = y.mean(axis=1)
    import numpy as np
    score = trust_from_signal(np.array(y), sr)
    color = "green" if score >= 8 else "amber" if score >= 5 else "red"
    spoken = f"Trust {round(score,1)}/10 — {'likely safe' if color=='green' else 'review carefully' if color=='amber' else 'likely scam'}."
    await record_ai_cost(request, "/ai/voice/score", 0.25, {"color": color, "score": score})
    return {"score": round(score,1), "color": color, "spoken": spoken}
