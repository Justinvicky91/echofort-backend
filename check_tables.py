#!/usr/bin/env python3
import asyncio
import aiomysql
import os
import ssl

async def check_tables():
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
            await cursor.execute("SHOW TABLES")
            tables = await cursor.fetchall()
            print(f"\n📊 Tables in database '{database}':")
            print("=" * 50)
            for (table_name,) in tables:
                print(f"  ✓ {table_name}")
            print("=" * 50)
            print(f"Total: {len(tables)} tables\n")
    finally:
        conn.close()

if __name__ == '__main__':
    asyncio.run(check_tables())
