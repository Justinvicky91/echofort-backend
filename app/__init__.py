# app/__init__.py
"""
Database URL configuration using Railway environment variables.
This runs FIRST when the app package is loaded, before any other imports.
"""

import os

# Get DATABASE_URL from environment
database_url = os.getenv("DATABASE_URL")

if database_url:
    # Railway provides postgresql:// but we need to ensure it's properly formatted
    if database_url.startswith("postgres://"):
        # Update to postgresql:// for compatibility
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        os.environ["DATABASE_URL"] = database_url
        print("[INFO] DATABASE_URL loaded from environment and normalized")
    elif database_url.startswith("postgresql://"):
        print("[INFO] DATABASE_URL loaded from environment")
    else:
        print("[WARNING] DATABASE_URL has unexpected format")
else:
    print("[ERROR] DATABASE_URL not found in environment variables!")
    print("[ERROR] Please set DATABASE_URL in Railway environment variables")

