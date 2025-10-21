# app/ai/voice.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi import Depends, Request
import io, wave
import numpy as np

from ..deps import get_settings

router = APIRouter(prefix="/ai/voice", tags=["ai"])

def _score_from_pcm(y: np.ndarray) -> float:
    # normalize
    peak = float(np.max(np.abs(y)) + 1e-9)
    y = (y / peak).astype(np.float32)

    rms = float(np.sqrt(np.mean(y ** 2)))
    zcr = float(((y[:-1] * y[1:]) < 0).mean())  # zero-crossing ratio

    # Heuristic 0..10
    score = 10.0 - (zcr * 10.0) + (rms * 8.0)
    return float(np.clip(score, 0.0, 10.0))

@router.post("/score")
async def voice_score(
    file: UploadFile = File(...),
    request: Request = None,
    settings = Depends(get_settings),
):
    raw = await file.read()

    # Parse WAV via stdlib wave; require PCM 16-bit
    try:
        with wave.open(io.BytesIO(raw), "rb") as w:
            n_channels = w.getnchannels()
            sampwidth  = w.getsampwidth()   # bytes per sample
            framerate  = w.getframerate()
            n_frames   = w.getnframes()

            if sampwidth != 2:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported WAV: expected 16-bit PCM, got {sampwidth*8}-bit",
                )
            frames = w.readframes(n_frames)
    except wave.Error as e:
        raise HTTPException(status_code=400, detail=f"Invalid/unsupported WAV: {e}")

    # Little-endian 16-bit → float32
    y = np.frombuffer(frames, dtype="<i2").astype(np.float32)
    if n_channels > 1:
        y = y.reshape(-1, n_channels).mean(axis=1)

    score = _score_from_pcm(y)
    color = "green" if score >= 8 else "amber" if score >= 5 else "red"
    spoken = f"Trust {round(score,1)}/10 — " + (
        "likely safe" if color == "green" else "review carefully" if color == "amber" else "likely scam"
    )

    return {
        "score": round(score, 1),
        "color": color,
        "spoken": spoken,
        "sr": framerate,
        "channels": n_channels,
        "note": "WAV must be PCM 16-bit. ADPCM/MP3 not supported in this lightweight endpoint.",
    }
