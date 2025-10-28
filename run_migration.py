#!/usr/bin/env python3
import asyncio
import aiomysql
import os
import ssl

async def run_migration():
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
            # Read migration file
            with open('migrations/014_employees_table.sql', 'r') as f:
                migration_sql = f.read()
            
            # Split by semicolons and execute each statement
            statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]
            
            print(f"\n🔄 Running migration: 014_employees_table.sql")
            print("=" * 60)
            
            for i, statement in enumerate(statements, 1):
                # Skip comments
                if statement.startswith('COMMENT'):
                    print(f"  {i}. Skipping COMMENT (not supported in MySQL)")
                    continue
                
                # Convert PostgreSQL syntax to MySQL
                statement = statement.replace('SERIAL', 'INT AUTO_INCREMENT')
                statement = statement.replace('NOW()', 'CURRENT_TIMESTAMP')
                statement = statement.replace('TIMESTAMP DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP')
                
                try:
                    await cursor.execute(statement)
                    print(f"  ✓ Statement {i} executed successfully")
                except Exception as e:
                    print(f"  ✗ Statement {i} failed: {e}")
                    if "already exists" not in str(e).lower():
                        raise
            
            await conn.commit()
            print("=" * 60)
            print("✅ Migration completed successfully!\n")
            
    finally:
        conn.close()

if __name__ == '__main__':
    asyncio.run(run_migration())
