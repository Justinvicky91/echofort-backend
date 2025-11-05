from fastapi import APIRouter, Header
from .utils import require_super_admin
from fastapi import Depends

router = APIRouter(prefix="/test", tags=["Test"])

@router.get("/admin-check")
async def test_admin_auth(admin: dict = Depends(require_super_admin)):
    """Test if admin authentication works"""
    return {
        "ok": True,
        "admin": admin,
        "message": "Admin authentication successful!"
    }

@router.get("/admin-key-check")
async def test_admin_key(authorization: str = Header(None)):
    """Test admin key directly"""
    from .deps import get_settings
    settings = get_settings()
    admin_key = getattr(settings, 'ADMIN_KEY', None)
    
    if not authorization:
        return {"error": "No authorization header"}
    
    token = authorization.replace("Bearer ", "")
    
    return {
        "ok": True,
        "token_received": token[:20] + "...",
        "admin_key_set": admin_key is not None,
        "admin_key_preview": admin_key[:20] + "..." if admin_key else None,
        "match": token == admin_key if admin_key else False
    }
