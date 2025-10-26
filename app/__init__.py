# app/__init__.py
"""
TEMPORARY FIX: Hardcode correct DATABASE_URL to bypass Railway env var issues.
This runs FIRST when the app package is loaded, before any other imports.
TODO: Remove this after Railway Variable Reference is properly set up.
"""

import os

# CORRECT DATABASE_URL from Postgres service
CORRECT_DATABASE_URL = "postgresql://Postgres:cMoeoOlFKQRosoMfIMetyZqASl1JlOHsm@postgres.railway.internal:5432/railway"

# Override the DATABASE_URL environment variable
os.environ["DATABASE_URL"] = CORRECT_DATABASE_URL

print("[FIX] DATABASE_URL hardcoded to bypass Railway env var issues")
print(f"[FIX] DATABASE_URL password: ...{CORRECT_DATABASE_URL.split(':')[2].split('@')[0][-10:]}")
print("[FIX] This is a TEMPORARY workaround - use Variable Reference for production!")

