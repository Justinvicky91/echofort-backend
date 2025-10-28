#!/usr/bin/env python3
import asyncio
import aiomysql
import os
import ssl
import bcrypt

async def test_password():
    db_url = os.environ['DATABASE_URL']
    parts = db_url.replace('mysql://', '').split('@')
    user_pass = parts[0].split(':')
    host_parts = parts[1].split('/')
    host_port = host_parts[0].split(':')
    
    user = user_pass[0]
    password = user_pass[1]
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 3306
    database = host_parts[1].split('?')[0]
    
    conn = await aiomysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        db=database,
        ssl=ssl.create_default_context()
    )
    
    try:
        async with conn.cursor() as cursor:
            # Get super admin record
            await cursor.execute("""
                SELECT id, username, password_hash, role, is_super_admin
                FROM employees
                WHERE username = %s
            """, ('EchofortSuperAdmin91',))
            
            result = await cursor.fetchone()
            
            if not result:
                print("❌ Super admin not found!")
                return
            
            emp_id, username, password_hash, role, is_super = result
            
            print(f"\n📊 Super Admin Record:")
            print(f"  ID: {emp_id}")
            print(f"  Username: {username}")
            print(f"  Role: {role}")
            print(f"  Is Super Admin: {is_super}")
            print(f"  Password Hash: {password_hash[:50]}...")
            
            # Test password
            test_password = "SecureAdmin@2025"
            print(f"\n🔐 Testing password: {test_password}")
            
            try:
                # bcrypt.checkpw expects bytes
                password_match = bcrypt.checkpw(
                    test_password.encode('utf-8'),
                    password_hash.encode('utf-8')
                )
                
                if password_match:
                    print("  ✅ Password verification SUCCESSFUL!")
                else:
                    print("  ❌ Password verification FAILED!")
                    
                    # Try creating a new hash and testing
                    print("\n  Debugging: Creating fresh hash...")
                    new_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    print(f"  New hash: {new_hash[:50]}...")
                    
                    new_match = bcrypt.checkpw(test_password.encode('utf-8'), new_hash.encode('utf-8'))
                    print(f"  Fresh hash test: {'✅ PASS' if new_match else '❌ FAIL'}")
                    
            except Exception as e:
                print(f"  ❌ Password verification error: {e}")
                
    finally:
        conn.close()

if __name__ == '__main__':
    asyncio.run(test_password())
