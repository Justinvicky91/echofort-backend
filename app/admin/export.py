from fastapi import APIRouter, Response, Depends, Request
from sqlalchemy import text
from ..rbac import guard_marketing

router = APIRouter(prefix="/admin/export", tags=["admin"])

@router.get("/marketing.csv", dependencies=[Depends(guard_marketing)])
async def export_marketing_csv(request: Request):
    rows = (await request.app.state.db.execute(text(
      "SELECT id, title, status, approver_id, approved_at, sent_at, created_at FROM marketing_push ORDER BY created_at DESC"
    ))).fetchall()
    lines = ["id,title,status,approver_id,approved_at,sent_at,created_at"]
    for r in rows:
      m = r._mapping
      lines.append(f'{m["id"]},"{m["title"]}",{m["status"]},{m["approver_id"]},{m["approved_at"]},{m["sent_at"]},{m["created_at"]}')
    csv = "\n".join(lines)
    return Response(content=csv, media_type="text/csv")
