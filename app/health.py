"""
Health Check and System Status Endpoints
"""

from fastapi import APIRouter, Depends
from datetime import datetime
import psutil
import os
from .deps import get_db, DBShim

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "EchoFort API",
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health_check(db: DBShim = Depends(get_db)):
    """Detailed health check with database and system metrics"""
    try:
        # Check database connection
        db_status = "healthy"
        try:
            result = db.execute("SELECT 1").fetchone()
            if result and result[0] == 1:
                db_status = "healthy"
            else:
                db_status = "unhealthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "EchoFort API",
            "version": "1.0.0",
            "components": {
                "database": {
                    "status": db_status,
                    "type": "MySQL"
                },
                "api": {
                    "status": "healthy"
                }
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            },
            "environment": {
                "python_version": os.sys.version.split()[0],
                "platform": os.sys.platform
            }
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/ping")
async def ping():
    """Simple ping endpoint for uptime monitoring"""
    return {"ping": "pong", "timestamp": datetime.utcnow().isoformat()}

