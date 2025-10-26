# app/fix_database_url.py
"""
Automatic DATABASE_URL password fixer for Railway UI bug.

This module patches os.getenv to automatically fix the wrong DATABASE_URL password
that Railway UI sometimes provides due to a copy/paste bug.

Import this module BEFORE any code that uses DATABASE_URL!
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
            print(f"[FIX] DATABASE_URL password auto-corrected")
    
    return value

# Patch os.getenv globally
os.getenv = _fixed_getenv

print("[FIX] DATABASE_URL auto-correction enabled")

