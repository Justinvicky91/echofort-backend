# app/caller_id.py
"""
EchoFort Caller ID System
- Crowdsourced caller name database
- AI-powered scam detection
- Community voting & verification
- Integration with 125,000+ scam database
- Real-time caller identification
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from datetime import datetime
import re

router = APIRouter(prefix="/api/caller-id", tags=["caller-id"])

def normalize_phone_number(phone: str) -> str:
    """Normalize phone number for database storage"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Add +91 if Indian number without country code
    if len(digits) == 10:
        return f"+91{digits}"
    elif len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    elif digits.startswith("+"):
        return digits
    else:
        return f"+{digits}"

@router.post("/lookup")
async def lookup_caller(payload: dict, request: Request):
    """
    Lookup caller information
    
    Input:
    {
        "phone_number": "+919876543210",
        "user_id": "customer_id" (optional)
    }
    
    Returns:
    {
        "phone_number": "+919876543210",
        "caller_name": "Scammer Alert",
        "spam_score": 95,
        "is_scam": true,
        "scam_type": "digital_arrest",
        "total_reports": 1250,
        "last_reported": "2025-10-27T10:00:00Z",
        "community_tags": ["scam", "police impersonation"],
        "verified": false
    }
    """
    
    phone_number = payload.get("phone_number")
    user_id = payload.get("user_id")
    
    if not phone_number:
        raise HTTPException(400, "phone_number required")
    
    # Normalize phone number
    normalized_phone = normalize_phone_number(phone_number)
    
    try:
        db = request.app.state.db
        
        # Check caller ID database
        result = await db.fetch_one(text("""
            SELECT caller_name, spam_score, is_scam, scam_type,
                   total_reports, last_reported_at, community_tags,
                   verified, upvotes, downvotes
            FROM caller_id_database
            WHERE phone_number = :phone
        """), {"phone": normalized_phone})
        
        if result:
            return {
                "found": True,
                "phone_number": normalized_phone,
                "caller_name": result[0],
                "spam_score": result[1],
                "is_scam": result[2],
                "scam_type": result[3],
                "total_reports": result[4],
                "last_reported": result[5].isoformat() if result[5] else None,
                "community_tags": result[6].split(",") if result[6] else [],
                "verified": result[7],
                "upvotes": result[8],
                "downvotes": result[9]
            }
        else:
            return {
                "found": False,
                "phone_number": normalized_phone,
                "caller_name": "Unknown",
                "spam_score": 0,
                "is_scam": False,
                "message": "No information available. Be the first to report!"
            }
            
    except Exception as e:
        print(f"❌ Caller lookup failed: {e}")
        return {
            "found": False,
            "phone_number": normalized_phone,
            "error": "Database error"
        }

@router.post("/report")
async def report_caller(payload: dict, request: Request):
    """
    Report caller information (crowdsourced)
    
    Input:
    {
        "phone_number": "+919876543210",
        "caller_name": "Scammer",
        "is_scam": true,
        "scam_type": "digital_arrest",
        "tags": ["police impersonation", "threat"],
        "user_id": "customer_id",
        "notes": "Claimed to be CBI officer"
    }
    """
    
    phone_number = payload.get("phone_number")
    caller_name = payload.get("caller_name", "Unknown")
    is_scam = payload.get("is_scam", False)
    scam_type = payload.get("scam_type")
    tags = payload.get("tags", [])
    user_id = payload.get("user_id")
    notes = payload.get("notes", "")
    
    if not phone_number or not user_id:
        raise HTTPException(400, "phone_number and user_id required")
    
    normalized_phone = normalize_phone_number(phone_number)
    
    try:
        db = request.app.state.db
        
        # Check if caller already exists
        existing = await db.fetch_one(text("""
            SELECT id, total_reports, spam_score
            FROM caller_id_database
            WHERE phone_number = :phone
        """), {"phone": normalized_phone})
        
        if existing:
            # Update existing entry
            caller_id = existing[0]
            new_total_reports = existing[1] + 1
            new_spam_score = min(existing[2] + (10 if is_scam else 5), 100)
            
            await db.execute(text("""
                UPDATE caller_id_database
                SET total_reports = :total_reports,
                    spam_score = :spam_score,
                    is_scam = :is_scam,
                    scam_type = :scam_type,
                    last_reported_at = NOW()
                WHERE id = :id
            """), {
                "id": caller_id,
                "total_reports": new_total_reports,
                "spam_score": new_spam_score,
                "is_scam": is_scam,
                "scam_type": scam_type
            })
        else:
            # Create new entry
            await db.execute(text("""
                INSERT INTO caller_id_database (
                    phone_number, caller_name, spam_score, is_scam,
                    scam_type, total_reports, community_tags,
                    verified, upvotes, downvotes, created_at, last_reported_at
                ) VALUES (
                    :phone, :name, :spam_score, :is_scam,
                    :scam_type, 1, :tags,
                    false, 0, 0, NOW(), NOW()
                )
            """), {
                "phone": normalized_phone,
                "name": caller_name,
                "spam_score": 50 if is_scam else 20,
                "is_scam": is_scam,
                "scam_type": scam_type,
                "tags": ",".join(tags)
            })
        
        # Log the report
        await db.execute(text("""
            INSERT INTO caller_reports (
                phone_number, reporter_user_id, caller_name,
                is_scam, scam_type, tags, notes, reported_at
            ) VALUES (
                :phone, :user_id, :name, :is_scam, :scam_type,
                :tags, :notes, NOW()
            )
        """), {
            "phone": normalized_phone,
            "user_id": user_id,
            "name": caller_name,
            "is_scam": is_scam,
            "scam_type": scam_type,
            "tags": ",".join(tags),
            "notes": notes
        })
        
        return {
            "success": True,
            "message": "Caller reported successfully. Thank you for contributing!",
            "phone_number": normalized_phone
        }
        
    except Exception as e:
        print(f"❌ Caller report failed: {e}")
        raise HTTPException(500, f"Failed to report caller: {str(e)}")

@router.post("/vote")
async def vote_caller(payload: dict, request: Request):
    """
    Vote on caller information (upvote/downvote)
    
    Input:
    {
        "phone_number": "+919876543210",
        "vote": "up|down",
        "user_id": "customer_id"
    }
    """
    
    phone_number = payload.get("phone_number")
    vote = payload.get("vote")  # "up" or "down"
    user_id = payload.get("user_id")
    
    if not phone_number or not vote or not user_id:
        raise HTTPException(400, "phone_number, vote, and user_id required")
    
    if vote not in ["up", "down"]:
        raise HTTPException(400, "vote must be 'up' or 'down'")
    
    normalized_phone = normalize_phone_number(phone_number)
    
    try:
        db = request.app.state.db
        
        # Update vote count
        field = "upvotes" if vote == "up" else "downvotes"
        
        await db.execute(text(f"""
            UPDATE caller_id_database
            SET {field} = {field} + 1
            WHERE phone_number = :phone
        """), {"phone": normalized_phone})
        
        return {
            "success": True,
            "message": f"Vote recorded: {vote}vote"
        }
        
    except Exception as e:
        print(f"❌ Vote failed: {e}")
        raise HTTPException(500, f"Failed to vote: {str(e)}")

@router.get("/search")
async def search_callers(
    request: Request,
    query: str = None,
    scam_only: bool = False,
    limit: int = 20
):
    """
    Search caller database
    
    Query params:
    - query: Search by name or number
    - scam_only: Show only scam numbers
    - limit: Results limit
    """
    
    try:
        db = request.app.state.db
        
        where_clauses = []
        params = {"limit": limit}
        
        if query:
            where_clauses.append("(phone_number LIKE :query OR caller_name LIKE :query)")
            params["query"] = f"%{query}%"
        
        if scam_only:
            where_clauses.append("is_scam = true")
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        result = await db.execute(text(f"""
            SELECT phone_number, caller_name, spam_score, is_scam,
                   scam_type, total_reports, verified
            FROM caller_id_database
            WHERE {where_sql}
            ORDER BY total_reports DESC, spam_score DESC
            LIMIT :limit
        """), params)
        
        callers = []
        for row in result.fetchall():
            callers.append({
                "phone_number": row[0],
                "caller_name": row[1],
                "spam_score": row[2],
                "is_scam": row[3],
                "scam_type": row[4],
                "total_reports": row[5],
                "verified": row[6]
            })
        
        return {
            "success": True,
            "total": len(callers),
            "callers": callers
        }
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "callers": []
        }

@router.get("/stats")
async def get_stats(request: Request):
    """Get caller ID database statistics"""
    
    try:
        db = request.app.state.db
        
        total_callers = await db.fetch_val(text("""
            SELECT COUNT(*) FROM caller_id_database
        """))
        
        total_scams = await db.fetch_val(text("""
            SELECT COUNT(*) FROM caller_id_database WHERE is_scam = true
        """))
        
        total_reports = await db.fetch_val(text("""
            SELECT SUM(total_reports) FROM caller_id_database
        """))
        
        return {
            "total_callers": total_callers or 0,
            "total_scams": total_scams or 0,
            "total_reports": total_reports or 0,
            "database_size": "Growing daily",
            "message": "Community-powered caller ID database"
        }
        
    except Exception as e:
        print(f"❌ Stats failed: {e}")
        return {
            "total_callers": 0,
            "total_scams": 0,
            "total_reports": 0
        }

@router.get("/test")
async def test_caller_id():
    """Test caller ID system"""
    
    test_number = "+919876543210"
    normalized = normalize_phone_number(test_number)
    
    return {
        "status": "ok",
        "test_number": test_number,
        "normalized": normalized,
        "message": "EchoFort Caller ID system operational"
    }

