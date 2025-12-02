"""
API Endpoint to Create Test Employees for RBAC Testing
Block 24 - Part A
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from datetime import datetime
import bcrypt

router = APIRouter(prefix="/admin", tags=["admin"])

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


@router.post("/create-test-employees")
async def create_test_employees(request: Request):
    """
    Create test employee accounts with different roles for RBAC testing.
    
    This endpoint is for development/testing only.
    Creates 5 test employees: admin, support, marketing, legal, engineering.
    """
    try:
        db = request.app.state.db
        created = []
        existing = []
        
        for emp in TEST_EMPLOYEES:
            # Check if employee already exists
            result = await db.execute(
                text("SELECT id, role FROM employees WHERE username = :username"),
                {"username": emp["username"]}
            )
            row = result.fetchone()
            
            if row:
                existing.append({
                    "username": emp["username"],
                    "id": row[0],
                    "role": row[1]
                })
                continue
            
            # Hash password
            password_hash = bcrypt.hashpw(
                emp["password"].encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # Insert employee
            result = await db.execute(
                text("""
                    INSERT INTO employees (username, password_hash, role, department, is_super_admin, created_at)
                    VALUES (:username, :password_hash, :role, :department, :is_super_admin, :created_at)
                    RETURNING id
                """),
                {
                    "username": emp["username"],
                    "password_hash": password_hash,
                    "role": emp["role"],
                    "department": emp["department"],
                    "is_super_admin": emp["is_super_admin"],
                    "created_at": datetime.utcnow()
                }
            )
            
            emp_id = result.fetchone()[0]
            created.append({
                "username": emp["username"],
                "id": emp_id,
                "role": emp["role"],
                "password": emp["password"]  # Only return password for newly created accounts
            })
        
        return {
            "success": True,
            "created": created,
            "existing": existing,
            "message": f"Created {len(created)} new test employees. {len(existing)} already existed.",
            "login_url": "https://echofort.ai/login",
            "credentials": [
                {
                    "username": emp["username"],
                    "password": emp["password"],
                    "role": emp["role"]
                }
                for emp in TEST_EMPLOYEES
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create test employees: {str(e)}"
        )
