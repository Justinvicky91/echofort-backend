"""
Enhanced Error Handling Middleware
Provides consistent error responses and logging
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent format"""
    logger.warning(
        f"HTTP {exc.status_code}: {request.method} {request.url.path} - {exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed field information"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation Error: {request.method} {request.url.path} - {len(errors)} errors"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": 422,
                "message": "Validation failed",
                "details": errors,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(
        f"Unhandled Exception: {request.method} {request.url.path}\n"
        f"Error: {str(exc)}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal server error",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def request_logging_middleware(request: Request, call_next):
    """Log all incoming requests"""
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(
        f"→ {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    # Log response
    logger.info(
        f"← {request.method} {request.url.path} "
        f"[{response.status_code}] {duration:.2f}ms"
    )
    
    return response

