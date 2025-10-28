#!/usr/bin/env python3
import asyncio
import aiomysql
import os
import ssl
import bcrypt

async def create_employees_table():
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
            print("\n🔄 Creating employees table...")
            
            # Create employees table (MySQL syntax)
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NULL,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NULL,
                    role VARCHAR(50) NOT NULL,
                    department VARCHAR(100) NULL,
                    is_super_admin BOOLEAN DEFAULT false,
                    active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL,
                    created_by INT NULL,
                    INDEX idx_employees_username (username),
                    INDEX idx_employees_role (role),
                    INDEX idx_employees_active (active),
                    INDEX idx_employees_super_admin (is_super_admin)
                )
            """)
            print("  ✓ employees table created")
            
            await conn.commit()
            
            # Check if super admin exists
            await cursor.execute("""
                SELECT COUNT(*) FROM employees WHERE username = 'EchofortSuperAdmin91'
            """)
            count = (await cursor.fetchone())[0]
            
            if count == 0:
                print("\n🔄 Creating super admin account...")
                
                # Create super admin
                password_hash = bcrypt.hashpw(b'SecureAdmin@2025', bcrypt.gensalt()).decode('utf-8')
                
                await cursor.execute("""
                    INSERT INTO employees (
                        username, password_hash, email, role, department,
                        is_super_admin, active
                    ) VALUES (
                        'EchofortSuperAdmin91',
                        %s,
                        'Vicky.Jvsap@gmail.com',
                        'super_admin',
                        'Management',
                        true,
                        true
                    )
                """, (password_hash,))
                
                await conn.commit()
                
                print("  ✓ Super admin created")
                print("\n" + "=" * 60)
                print("✅ SUPER ADMIN CREDENTIALS")
                print("=" * 60)
                print("  Username: EchofortSuperAdmin91")
                print("  Password: SecureAdmin@2025")
                print("  Email: Vicky.Jvsap@gmail.com")
                print("  Login URL: https://echofort.ai/login")
                print("=" * 60)
            else:
                print("\n  ℹ️  Super admin already exists, updating password...")
                
                password_hash = bcrypt.hashpw(b'SecureAdmin@2025', bcrypt.gensalt()).decode('utf-8')
                
                await cursor.execute("""
                    UPDATE employees
                    SET password_hash = %s
                    WHERE username = 'EchofortSuperAdmin91'
                """, (password_hash,))
                
                await conn.commit()
                
                print("  ✓ Password updated")
                print("\n" + "=" * 60)
                print("✅ SUPER ADMIN PASSWORD RESET")
                print("=" * 60)
                print("  Username: EchofortSuperAdmin91")
                print("  New Password: SecureAdmin@2025")
                print("  Login URL: https://echofort.ai/login")
                print("=" * 60)
            
    finally:
        conn.close()

if __name__ == '__main__':
    asyncio.run(create_employees_table())
