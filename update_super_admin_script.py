#!/usr/bin/env python3
"""
Simple script to update super admin credentials
Run this on Railway using: railway run python update_super_admin_script.py
"""
import asyncio
import asyncpg
import bcrypt
import os

async def update_super_admin():
    # Get DATABASE_URL from environment (Railway provides this)
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable not set!")
        return
    
    print("🔄 Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Check existing super admin
        existing = await conn.fetchrow("""
            SELECT id, user_id, username FROM employees WHERE is_super_admin = true
        """)
        
        if not existing:
            print("❌ No super admin found!")
            return
        
        print(f"✅ Found existing super admin: {existing['username']}")
        
        # New credentials
        new_username = "EchofortSuperAdmin91"
        new_password = "Echo$9176$007$#"
        new_email = "EchofortAI@gmail.com"
        new_name = "Vigneshwaran J"
        new_phone = "+919361440568"
        
        # Hash password
        print("🔐 Hashing password...")
        hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        
        # Update user record
        print("📝 Updating user record...")
        await conn.execute("""
            UPDATE users
            SET email = $1, name = $2
            WHERE id = $3
        """, new_email, new_name, existing['user_id'])
        
        # Update employee record
        print("📝 Updating employee record...")
        await conn.execute("""
            UPDATE employees
            SET username = $1,
                password_hash = $2,
                phone = $3
            WHERE is_super_admin = true
        """, new_username, hashed_password, new_phone)
        
        print("\n🎉 SUCCESS! Super admin updated:")
        print(f"   Username: {new_username}")
        print(f"   Password: {new_password}")
        print(f"   Email: {new_email}")
        print(f"   Name: {new_name}")
        print(f"   Phone: {new_phone}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(update_super_admin())

