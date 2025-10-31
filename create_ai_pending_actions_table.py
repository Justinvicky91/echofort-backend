#!/usr/bin/env python3
"""
Simple script to create ai_pending_actions table directly in the database.
Run this once to fix the missing table issue.
"""

import asyncio
from sqlalchemy import create_engine, text
import os

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL environment variable not set!")
    exit(1)

# Create SQL to create the table
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ai_pending_actions (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    sql_command TEXT,
    file_path TEXT,
    code_changes TEXT,
    package_name TEXT,
    rollback_plan TEXT,
    risk_level VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    approved_at TIMESTAMP,
    approved_by VARCHAR(255),
    executed_at TIMESTAMP,
    execution_result TEXT
);
"""

def create_table():
    """Create the ai_pending_actions table"""
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Execute the CREATE TABLE statement
        with engine.connect() as conn:
            conn.execute(text(CREATE_TABLE_SQL))
            conn.commit()
            print("✅ SUCCESS: ai_pending_actions table created!")
            
            # Verify the table exists
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'ai_pending_actions'
            """))
            
            if result.fetchone():
                print("✅ VERIFIED: Table exists in database!")
            else:
                print("❌ ERROR: Table creation failed!")
                
    except Exception as e:
        print(f"❌ ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    create_table()
