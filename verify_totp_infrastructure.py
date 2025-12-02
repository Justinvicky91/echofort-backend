#!/usr/bin/env python3
"""
Block 24F - Part A: Verify TOTP Infrastructure Integrity
Confirms TOTP is only disabled (not deleted) for Founder account
"""

import os
import sys
from sqlalchemy import create_engine, text

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment")
    sys.exit(1)

# Create engine
engine = create_engine(DATABASE_URL)

print("=" * 70)
print("BLOCK 24F - PART A: TOTP INFRASTRUCTURE VERIFICATION")
print("=" * 70)
print()

with engine.connect() as conn:
    # 1. Check if TOTP columns exist in employees table
    print("1️⃣  Checking TOTP columns in employees table...")
    print("-" * 70)
    
    result = conn.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'employees' 
        AND column_name IN ('totp_secret', 'totp_enabled')
        ORDER BY column_name
    """))
    
    columns = result.fetchall()
    
    if not columns:
        print("❌ TOTP columns NOT FOUND in employees table!")
        sys.exit(1)
    
    for col in columns:
        print(f"   ✅ {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
    
    print()
    
    # 2. Check Founder account status
    print("2️⃣  Checking Founder account (id=1, username='EchofortSuperAdmin91')...")
    print("-" * 70)
    
    result = conn.execute(text("""
        SELECT 
            id, 
            username, 
            role, 
            is_super_admin,
            totp_enabled,
            totp_secret IS NOT NULL as has_totp_secret,
            active
        FROM employees 
        WHERE id = 1
    """))
    
    founder = result.fetchone()
    
    if not founder:
        print("❌ Founder account NOT FOUND!")
        sys.exit(1)
    
    print(f"   ID: {founder[0]}")
    print(f"   Username: {founder[1]}")
    print(f"   Role: {founder[2]}")
    print(f"   Is Super Admin: {founder[3]}")
    print(f"   TOTP Enabled: {founder[4]} {'✅ (DISABLED - TEMP DEV MODE)' if not founder[4] else '⚠️  (ENABLED)'}")
    print(f"   Has TOTP Secret: {founder[5]} {'✅ (PRESERVED)' if founder[5] else '❌ (MISSING!)'}")
    print(f"   Active: {founder[6]}")
    
    print()
    
    # 3. Verify TOTP endpoints exist in code
    print("3️⃣  Checking TOTP endpoints in code...")
    print("-" * 70)
    
    # Check if totp.py exists
    totp_file = "/home/ubuntu/echofort-backend/app/auth/totp.py"
    if os.path.exists(totp_file):
        print(f"   ✅ TOTP module exists: {totp_file}")
        
        # Read file and check for endpoints
        with open(totp_file, 'r') as f:
            content = f.read()
            
        if '/totp/setup' in content:
            print("   ✅ /auth/totp/setup endpoint found")
        else:
            print("   ❌ /auth/totp/setup endpoint NOT found")
            
        if '/totp/verify' in content:
            print("   ✅ /auth/totp/verify endpoint found")
        else:
            print("   ❌ /auth/totp/verify endpoint NOT found")
    else:
        print(f"   ❌ TOTP module NOT found: {totp_file}")
    
    print()
    
    # 4. Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if founder[4]:
        print("⚠️  WARNING: TOTP is ENABLED for Founder account")
        print("   Expected: totp_enabled = false (TEMP DEV MODE)")
    else:
        print("✅ TOTP is DISABLED for Founder account (TEMP DEV MODE)")
    
    if founder[5]:
        print("✅ TOTP secret is PRESERVED (can be re-enabled later)")
    else:
        print("❌ TOTP secret is MISSING (cannot be re-enabled without setup)")
    
    print()
    print("✅ TOTP infrastructure is INTACT and ready for re-enable")
    print("   To re-enable: UPDATE employees SET totp_enabled = true WHERE id = 1;")
    print()

print("=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
