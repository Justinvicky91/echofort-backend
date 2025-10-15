# app/ai/voice.py
from fastapi import APIRouter, UploadFile, File, Depends, Request, HTTPException
import io, wave, numpy as np
from ..ai.guard import ensure_ai_budget, record_ai_cost
from ..deps import get_settings

router = APIRouter(prefix="/ai/voice", tags=["ai"])

def score_from_wav_bytes(raw: bytes) -> tuple[float, int]:
    # Parse PCM WAV using stdlib
    try:
        with wave.open(io.BytesIO(raw), 'rb') as w:
            n_channels = w.getnchannels()
            sampwidth  = w.getsampwidth()   # bytes per sample
            framerate  = w.getframerate()
            n_frames   = w.getnframes()
            frames     = w.readframes(n_frames)
    except wave.Error:
        raise HTTPException(400, "Unsupported audio format. Please upload a WAV (PCM) file.")

    # convert to np array
    dtype = {1: np.int8, 2: np.int16, 4: np.int32}.get(sampwidth)
    if dtype is None:
        raise HTTPException(400, f"Unsupported WAV sample width: {sampwidth} bytes")
    y = np.frombuffer(frames, dtype=dtype).astype(np.float32)
    if n_channels > 1:
        y = y.reshape(-1, n_channels).mean(axis=1)
    # normalize
    peak = np.max(np.abs(y)) + 1e-9
    y = y / peak

    # simple features
    rms = float(np.sqrt(np.mean(y**2)))
    zcr = float(((y[:-1] * y[1:]) < 0).mean())      # zero-crossing ratio

    # heuristic score 0..10
    score = 10.0 - (zcr * 10.0) + (rms * 8.0)
    score = float(np.clip(score, 0.0, 10.0))
    return score, framerate

@router.post("/score")
async def voice_score(file: UploadFile = File(...), request: Request = None, settings=Depends(get_settings)):
    await ensure_ai_budget(request, estimated_rs=0.10)
    data = await file.read()
    score, sr = score_from_wav_bytes(data)
    color = "green" if score >= 8 else "amber" if score >= 5 else "red"
    spoken = f"Trust {round(score,1)}/10 — {'likely safe' if color=='green' else 'review carefully' if color=='amber' else 'likely scam'}."
    await record_ai_cost(request, "/ai/voice/score", 0.10, {"color": color, "score": score, "sr": sr})
    return {"score": round(score,1), "color": color, "spoken": spoken, "sr": sr, "note": "Upload WAV/PCM for now"}
