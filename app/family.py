# app/family.py
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy import text
from .utils import get_current_user

router = APIRouter(prefix="/family", tags=["family"])

@router.post("/create")
async def create_family(
    payload: dict,
    request: Request,
    user = Depends(get_current_user)
):
    """
    Create family group (user becomes family head)
    Payload: {"family_name": "My Family"}
    """
    family_name = payload.get("family_name", "My Family")
    
    db = request.app.state.db
    result = await db.execute(text("""
        INSERT INTO families(name, head_user_id, created_at)
        VALUES (:name, :uid, NOW())
        RETURNING id
    """), {"name": family_name, "uid": user["user_id"]})
    
    family_id = result.fetchone()[0]
    
    # Add creator as first member
    await db.execute(text("""
        INSERT INTO family_members(family_id, user_id, role, joined_at)
        VALUES (:fid, :uid, 'head', NOW())
    """), {"fid": family_id, "uid": user["user_id"]})
    
    return {"ok": True, "family_id": family_id, "message": "Family created"}


@router.post("/add-member")
async def add_family_member(
    payload: dict,
    request: Request,
    user = Depends(get_current_user)
):
    """
    Add member to family (only family head can do this)
    Payload: {"member_phone": "+919876543210", "member_name": "Mom", "role": "parent"}
    """
    member_phone = payload.get("member_phone")
    member_name = payload.get("member_name")
    role = payload.get("role", "member")
    
    if not member_phone:
        raise HTTPException(400, "Missing member_phone")
    
    db = request.app.state.db
    
    # Check if user is family head
    family = (await db.execute(text("""
        SELECT id FROM families WHERE head_user_id = :uid
    """), {"uid": user["user_id"]})).fetchone()
    
    if not family:
        raise HTTPException(403, "You are not a family head")
    
    # Create or get member user
    await db.execute(text("""
        INSERT INTO users(identity, name, created_at)
        VALUES (:phone, :name, NOW())
        ON CONFLICT (identity) DO NOTHING
    """), {"phone": member_phone, "name": member_name})
    
    member = (await db.execute(text("""
        SELECT user_id FROM users WHERE identity = :phone
    """), {"phone": member_phone})).fetchone()
    
    # Add to family
    await db.execute(text("""
        INSERT INTO family_members(family_id, user_id, role, joined_at)
        VALUES (:fid, :uid, :role, NOW())
        ON CONFLICT DO NOTHING
    """), {"fid": family["id"], "uid": member["user_id"], "role": role})
    
    return {"ok": True, "message": f"Member {member_name} added to family"}


@router.get("/members")
async def list_family_members(
    request: Request,
    user = Depends(get_current_user)
):
    """Get all family members"""
    db = request.app.state.db
    rows = (await db.execute(text("""
        SELECT u.user_id, u.name, u.identity, fm.role, fm.joined_at
        FROM family_members fm
        JOIN users u ON fm.user_id = u.user_id
        WHERE fm.family_id IN (
            SELECT id FROM families WHERE head_user_id = :uid
        )
        ORDER BY fm.joined_at ASC
    """), {"uid": user["user_id"]})).fetchall()
    
    return {"members": [dict(r._mapping) for r in rows]}


@router.get("/alerts")
async def family_alerts(
    request: Request,
    user = Depends(get_current_user),
    limit: int = 50
):
    """Get family threat alerts (family head only)"""
    db = request.app.state.db
    rows = (await db.execute(text("""
        SELECT 
            u.name as member_name,
            a.alert_type,
            a.severity,
            a.message,
            a.created_at
        FROM family_alerts a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.family_id IN (
            SELECT id FROM families WHERE head_user_id = :uid
        )
        ORDER BY a.created_at DESC
        LIMIT :lim
    """), {"uid": user["user_id"], "lim": limit})).fetchall()
    
    return {
        "alerts": [dict(r._mapping) for r in rows],
        "count": len(rows)
    }
