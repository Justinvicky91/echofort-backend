"""
TEMPORARY DEV MODE: Disable TOTP for Founder account
This script:
1. Disables TOTP for EchofortSuperAdmin91
2. Sets password to SecureAdmin@2025 (hashed)
"""

import asyncio
import os
from sqlalchemy import text
from app.database import get_db_connection
from passlib.context import CryptContext

# Password hashing (same as used in backend)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def disable_totp_and_set_password():
    """Disable TOTP and set password for Founder account"""
    
    # Get database connection
    db = await get_db_connection()
    
    try:
        # Hash the password
        hashed_password = pwd_context.hash("SecureAdmin@2025")
        
        print("🔧 Updating Founder account (id=1, username=EchofortSuperAdmin91)...")
        print("   - Disabling TOTP (totp_enabled = false)")
        print("   - Setting password (hashed)")
        print("   - Clearing totp_secret")
        
        # Update the employee record
        update_query = text("""
            UPDATE employees 
            SET 
                totp_enabled = false,
                totp_secret = NULL,
                password = :password
            WHERE id = 1 
            AND username = 'EchofortSuperAdmin91'
            AND role = 'super_admin'
            RETURNING id, username, role, totp_enabled
        """)
        
        result = await db.execute(update_query, {"password": hashed_password})
        await db.commit()
        
        row = result.fetchone()
        
        if row:
            print(f"\n✅ SUCCESS!")
            print(f"   ID: {row[0]}")
            print(f"   Username: {row[1]}")
            print(f"   Role: {row[2]}")
            print(f"   TOTP Enabled: {row[3]}")
            print(f"\n🔐 Password set to: SecureAdmin@2025 (hashed in DB)")
            print(f"\n⚠️  TEMPORARY DEV MODE - Will re-enable 2FA in Block 24B")
        else:
            print("❌ ERROR: Founder account not found or not updated")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        await db.rollback()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(disable_totp_and_set_password())
