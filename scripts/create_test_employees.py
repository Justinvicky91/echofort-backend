"""
Create Test Employees for RBAC Testing
Block 24 - Part A

Creates test employee accounts with different roles for testing role-based access control.
"""

import os
import bcrypt
import psycopg
from datetime import datetime

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")

# Test employees to create
TEST_EMPLOYEES = [
    {
        "username": "testadmin",
        "password": "Admin@123",
        "role": "admin",
        "department": "Operations",
        "is_super_admin": False,
    },
    {
        "username": "testsupport",
        "password": "Support@123",
        "role": "employee_support",
        "department": "Customer Support",
        "is_super_admin": False,
    },
    {
        "username": "testmarketing",
        "password": "Marketing@123",
        "role": "employee_marketing",
        "department": "Marketing",
        "is_super_admin": False,
    },
    {
        "username": "testlegal",
        "password": "Legal@123",
        "role": "employee_legal",
        "department": "Legal & Compliance",
        "is_super_admin": False,
    },
    {
        "username": "testengineering",
        "password": "Engineering@123",
        "role": "employee_engineering",
        "department": "Engineering",
        "is_super_admin": False,
    },
]

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_test_employees():
    """Create test employee accounts in the database"""
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                for emp in TEST_EMPLOYEES:
                    # Check if employee already exists
                    cur.execute(
                        "SELECT id FROM employees WHERE username = %s",
                        (emp["username"],)
                    )
                    existing = cur.fetchone()
                    
                    if existing:
                        print(f"✓ Employee '{emp['username']}' already exists (ID: {existing[0]})")
                        continue
                    
                    # Hash password
                    password_hash = hash_password(emp["password"])
                    
                    # Insert employee
                    cur.execute(
                        """
                        INSERT INTO employees (username, password_hash, role, department, is_super_admin, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            emp["username"],
                            password_hash,
                            emp["role"],
                            emp["department"],
                            emp["is_super_admin"],
                            datetime.utcnow()
                        )
                    )
                    
                    emp_id = cur.fetchone()[0]
                    print(f"✓ Created employee '{emp['username']}' (ID: {emp_id}, Role: {emp['role']})")
                
                conn.commit()
                
                print("\n" + "="*60)
                print("Test Employee Accounts Created Successfully!")
                print("="*60)
                print("\nLogin Credentials:")
                print("-" * 60)
                for emp in TEST_EMPLOYEES:
                    print(f"Username: {emp['username']:<20} Password: {emp['password']:<20} Role: {emp['role']}")
                print("-" * 60)
                print("\nYou can now log in at: https://echofort.ai/login")
                print("Each role will see different sidebar items based on permissions.")
                
    except Exception as e:
        print(f"❌ Error creating test employees: {e}")
        raise

if __name__ == "__main__":
    create_test_employees()
