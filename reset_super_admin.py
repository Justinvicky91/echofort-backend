#!/usr/bin/env python3
"""
Direct password reset for super admin
"""
import asyncio
import aiomysql
import bcrypt
import os
import ssl

async def reset_password():
    # Parse MySQL connection URL
    db_url = os.environ['DATABASE_URL']
    # Format: mysql://user:pass@host:port/dbname
    
    # Extract components
    parts = db_url.replace('mysql://', '').split('@')
    user_pass = parts[0].split(':')
    host_parts = parts[1].split('/')
    host_port = host_parts[0].split(':')
    
    user = user_pass[0]
    password = user_pass[1]
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 3306
    database = host_parts[1].split('?')[0]
    
    print(f"Connecting to {host}:{port}/{database}")
    
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
            # Check current state
            await cursor.execute("""
                SELECT id, username, email, is_super_admin
                FROM employees
                WHERE username = %s
            """, ('EchofortSuperAdmin91',))
            
            result = await cursor.fetchone()
            
            if not result:
                print("❌ Super admin not found in employees table")
                return
            
            emp_id, username, email, is_super = result
            print(f"\n✅ Found super admin:")
            print(f"   ID: {emp_id}")
            print(f"   Username: {username}")
            print(f"   Email: {email}")
            print(f"   Is Super Admin: {is_super}")
            
            # Generate new password hash
            new_password = "SecureAdmin@2025"
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Update password
            await cursor.execute("""
                UPDATE employees
                SET password_hash = %s
                WHERE id = %s
            """, (password_hash, emp_id))
            
            await conn.commit()
            
            print(f"\n✅ Password reset successfully!")
            print(f"   Username: {username}")
            print(f"   New Password: {new_password}")
            print(f"\n🔐 You can now login at https://echofort.ai/login")
            
    finally:
        conn.close()

if __name__ == '__main__':
    asyncio.run(reset_password())
