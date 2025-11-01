"""
Google Authenticator (TOTP) 2FA Service for Super Admin
Time-based One-Time Password authentication
100% FREE - No external services needed!
"""

import pyotp
import qrcode
import io
import base64
from datetime import datetime

def generate_totp_secret():
    """
    Generate a new TOTP secret for a user
    
    Returns:
        str: Base32 encoded secret
    """
    return pyotp.random_base32()

def get_totp_uri(secret: str, username: str, issuer: str = "EchoFort"):
    """
    Generate TOTP URI for QR code
    
    Args:
        secret: TOTP secret
        username: User identifier
        issuer: Service name
        
    Returns:
        str: TOTP URI
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=username,
        issuer_name=issuer
    )

def generate_qr_code(secret: str, username: str) -> str:
    """
    Generate QR code image as base64 string
    
    Args:
        secret: TOTP secret
        username: User identifier
        
    Returns:
        str: Base64 encoded QR code image
    """
    uri = get_totp_uri(secret, username)
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"

def verify_totp(secret: str, token: str, window: int = 1) -> bool:
    """
    Verify TOTP token
    
    Args:
        secret: TOTP secret
        token: 6-digit TOTP code from user
        window: Time window tolerance (default 1 = ±30 seconds)
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        totp = pyotp.TOTP(secret)
        # Verify with time window tolerance
        return totp.verify(token, valid_window=window)
    except Exception as e:
        print(f"❌ TOTP verification error: {e}")
        return False

def get_current_totp(secret: str) -> str:
    """
    Get current TOTP code (for testing/debugging)
    
    Args:
        secret: TOTP secret
        
    Returns:
        str: Current 6-digit TOTP code
    """
    totp = pyotp.TOTP(secret)
    return totp.now()

def generate_backup_codes(count: int = 10) -> list:
    """
    Generate backup recovery codes
    
    Args:
        count: Number of codes to generate
        
    Returns:
        list: List of backup codes (format: XXXX-XXXX)
    """
    import random
    import string
    
    codes = []
    for _ in range(count):
        # Generate 8-character alphanumeric code
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        # Format as XXXX-XXXX
        formatted_code = f"{code[:4]}-{code[4:]}"
        codes.append(formatted_code)
    
    return codes
