# app/__init__.py
"""
CRITICAL: This file is imported FIRST when the app package is loaded.
It patches os.getenv to fix the DATABASE_URL password bug from Railway UI.
"""

import os

# Store the original getenv function
_original_getenv = os.getenv

def _fixed_getenv(key, default=None):
    """Patched getenv that automatically fixes DATABASE_URL password"""
    value = _original_getenv(key, default)
    
    # Only fix DATABASE_URL
    if key == "DATABASE_URL" and value:
        # Known wrong password from Railway UI
        wrong_password = "cMoeoOlFKQRosoMfIMetyZqASli1JOHsm"
        # Correct password from Postgres service
        correct_password = "cMoeoOlFKQRosoMfIMetyZqASl1JlOHsm"
        
        # Replace wrong password with correct one if found
        if wrong_password in value:
            value = value.replace(wrong_password, correct_password)
            print(f"[FIX] DATABASE_URL password auto-corrected in __init__.py")
    
    return value

# Patch os.getenv globally BEFORE any other imports
os.getenv = _fixed_getenv

print("[FIX] DATABASE_URL auto-correction enabled in app/__init__.py")

