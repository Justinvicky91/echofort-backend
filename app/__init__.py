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
        # Debug: Print masked DATABASE_URL to see what we're getting
        masked = value[:30] + "..." + value[-30:] if len(value) > 60 else value
        print(f"[DEBUG] DATABASE_URL (masked): {masked}")
        
        # Known wrong password from Railway UI
        wrong_password = "cMoeoOlFKQRosoMfIMetyZqASli1JOHsm"
        # Correct password from Postgres service  
        correct_password = "cMoeoOlFKQRosoMfIMetyZqASl1JlOHsm"
        
        # Replace wrong password with correct one if found
        if wrong_password in value:
            value = value.replace(wrong_password, correct_password)
            print(f"[FIX] DATABASE_URL password auto-corrected in __init__.py")
        else:
            print(f"[DEBUG] Wrong password NOT found in DATABASE_URL - checking password...")
            # Extract password from DATABASE_URL for debugging
            if "@" in value and ":" in value:
                try:
                    password_part = value.split("://")[1].split("@")[0].split(":")[1]
                    print(f"[DEBUG] Password in DATABASE_URL: {password_part}")
                    print(f"[DEBUG] Expected wrong: {wrong_password}")
                    print(f"[DEBUG] Expected correct: {correct_password}")
                except:
                    print(f"[DEBUG] Could not extract password for comparison")
    
    return value

# Patch os.getenv globally BEFORE any other imports
os.getenv = _fixed_getenv

print("[FIX] DATABASE_URL auto-correction enabled in app/__init__.py")

