"""AI assistant"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import openai, os

router = APIRouter(prefix="/api/ai-assistant", tags=["AI"])
openai.api_key = os.getenv("OPENAI_API_KEY")

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat(request: Request, req: ChatRequest, admin_key: str):
    if admin_key != os.getenv("ADMIN_KEY"): raise HTTPException(403, "Unauthorized")
    r = await request.app.state.db.execute("SELECT COUNT(*) FROM users", {})
    total = r.fetchone()[0]
    resp = openai.ChatCompletion.create(model="gpt-4", messages=[{"role":"user", "content":f"Total users: {total}. {req.message}"}], max_tokens=300)
    return {"response": resp.choices[0].message.content}

@router.get("/dashboard-report")
async def report(request: Request, admin_key: str):
    if admin_key != os.getenv("ADMIN_KEY"): raise HTTPException(403, "Unauthorized")
    r = await request.app.state.db.execute("SELECT COUNT(*) FROM users", {})
    return {"total_users": r.fetchone()[0], "mrr": 0, "arr": 0}
