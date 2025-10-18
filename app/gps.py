# app/gps.py
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy import text
from datetime import datetime
from .utils import get_current_user

router = APIRouter(prefix="/gps", tags=["gps"])

@router.post("/location")
async def save_location(
    payload: dict,
    request: Request,
    user = Depends(get_current_user)
):
    """
    Save user GPS location
    Payload: {"latitude": 12.9716, "longitude": 77.5946, "accuracy": 10}
    """
    lat = payload.get("latitude")
    lon = payload.get("longitude")
    accuracy = payload.get("accuracy", 0)
    
    if not lat or not lon:
        raise HTTPException(400, "Missing latitude or longitude")
    
    db = request.app.state.db
    await db.execute(text("""
        INSERT INTO gps_locations(user_id, latitude, longitude, accuracy, recorded_at)
        VALUES (:uid, :lat, :lon, :acc, NOW())
    """), {"uid": user["user_id"], "lat": lat, "lon": lon, "acc": accuracy})
    
    return {"ok": True, "message": "Location saved"}


@router.get("/history")
async def location_history(
    request: Request,
    user = Depends(get_current_user),
    limit: int = 100
):
    """Get user's location history (last 60 days)"""
    db = request.app.state.db
    rows = (await db.execute(text("""
        SELECT latitude, longitude, accuracy, recorded_at
        FROM gps_locations
        WHERE user_id = :uid
        AND recorded_at >= NOW() - INTERVAL '60 days'
        ORDER BY recorded_at DESC
        LIMIT :lim
    """), {"uid": user["user_id"], "lim": limit})).fetchall()
    
    return {
        "locations": [dict(r._mapping) for r in rows],
        "count": len(rows)
    }


@router.post("/geofence")
async def create_geofence(
    payload: dict,
    request: Request,
    user = Depends(get_current_user)
):
    """
    Create geofence zone
    Payload: {
        "name": "Home",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "radius": 100
    }
    """
    name = payload.get("name")
    lat = payload.get("latitude")
    lon = payload.get("longitude")
    radius = payload.get("radius", 100)
    
    if not all([name, lat, lon]):
        raise HTTPException(400, "Missing required fields")
    
    db = request.app.state.db
    await db.execute(text("""
        INSERT INTO geofences(user_id, name, latitude, longitude, radius_meters, created_at)
        VALUES (:uid, :name, :lat, :lon, :rad, NOW())
    """), {"uid": user["user_id"], "name": name, "lat": lat, "lon": lon, "rad": radius})
    
    return {"ok": True, "message": f"Geofence '{name}' created"}


@router.get("/geofences")
async def list_geofences(
    request: Request,
    user = Depends(get_current_user)
):
    """Get all user geofences"""
    db = request.app.state.db
    rows = (await db.execute(text("""
        SELECT id, name, latitude, longitude, radius_meters, created_at
        FROM geofences
        WHERE user_id = :uid
        ORDER BY created_at DESC
    """), {"uid": user["user_id"]})).fetchall()
    
    return {"geofences": [dict(r._mapping) for r in rows]}
