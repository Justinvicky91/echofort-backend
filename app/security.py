# app/security.py
"""
Security middleware for EchoFort backend
- Rate limiting
- CORS restrictions  
- JWT token expiry
- Input validation
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import jwt
from .deps import get_settings

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Allowed origins for CORS (will be configured from env)
def get_allowed_origins():
    settings = get_settings()
    if settings.ALLOW_ORIGINS == "*":
        # In production, this should be restricted
        return ["https://echofort.ai", "https://www.echofort.ai", "https://admin.echofort.ai"]
    return settings.ALLOW_ORIGINS.split(",")

# JWT token validation with expiry
def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT token with expiry"""
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)  # 24-hour default
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    return encoded_jwt

def verify_token(token: str):
    """Verify JWT token and check expiry"""
    settings = get_settings()
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        
        # Check if token is expired
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(401, "Token expired")
        
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

# Input validation helpers
def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not text:
        return ""
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '\\', ';', '--', '/*', '*/']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text.strip()

def validate_email(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    import re
    # Allow international format: +[country code][number]
    pattern = r'^\+?[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone.replace(' ', '').replace('-', '')))

# Security headers middleware
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Enable XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Strict transport security (HTTPS only)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Content security policy
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    
    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions policy
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response

# IP whitelist for admin endpoints
ADMIN_IP_WHITELIST = [
    "127.0.0.1",  # Localhost
    # Add your admin IPs here
]

def check_admin_ip(request: Request):
    """Check if request is from whitelisted admin IP"""
    client_ip = request.client.host
    
    # In development, allow all
    settings = get_settings()
    if settings.APP_ENV == "dev":
        return True
    
    # In production, check whitelist
    if client_ip not in ADMIN_IP_WHITELIST:
        raise HTTPException(403, "Access denied: IP not whitelisted")
    
    return True

# Request logging for audit trail
async def log_request(request: Request, call_next):
    """Log all requests for audit trail"""
    import logging
    logger = logging.getLogger("echofort.security")
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path} from {request.client.host}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    logger.info(f"Response: {response.status_code}")
    
    return response

