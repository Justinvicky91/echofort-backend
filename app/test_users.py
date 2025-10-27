"""
Test user creation endpoint for EchoFort
Creates test users for role-based testing
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg
import bcrypt
import os

router = APIRouter(prefix="/test", tags=["testing"])

class TestUserResponse(BaseModel):
    success: bool
    message: str
    users_created: list[dict]

@router.post("/create-test-users", response_model=TestUserResponse)
async def create_test_users():
    """
    Create test users for all roles
    WARNING: Only use in development/testing!
    """
    
    # Test users with passwords
    test_users = [
        {
            'username': 'testadmin',
            'password': 'Admin@123',
            'role': 'admin',
            'department': 'Administration'
        },
        {
            'username': 'support1',
            'password': 'Support@123',
            'role': 'customer_support',
            'department': 'Support'
        },
        {
            'username': 'marketing1',
            'password': 'Marketing@123',
            'role': 'marketing',
            'department': 'Marketing'
        },
        {
            'username': 'accounting1',
            'password': 'Accounting@123',
            'role': 'accounting',
            'department': 'Accounting'
        },
        {
            'username': 'hr1',
            'password': 'HR@123',
            'role': 'hr',
            'department': 'Human Resources'
        }
    ]
    
    try:
        # Get database URL
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        # Connect to database
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
        
        created_users = []
        
        # Insert each user
        for user in test_users:
            # Hash password
            password_hash = bcrypt.hashpw(
                user['password'].encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            try:
                cur.execute("""
                    INSERT INTO employees (username, password_hash, role, department, is_super_admin, active)
                    VALUES (%s, %s, %s, %s, false, true)
                    ON CONFLICT (username) DO NOTHING
                    RETURNING id, username, role, department
                """, (user['username'], password_hash, user['role'], user['department']))
                
                result = cur.fetchone()
                if result:
                    created_users.append({
                        'id': result[0],
                        'username': result[1],
                        'password': user['password'],  # Return plain password for testing
                        'role': result[2],
                        'department': result[3]
                    })
                    
            except Exception as e:
                print(f"Error creating {user['username']}: {e}")
        
        # Commit changes
        conn.commit()
        cur.close()
        conn.close()
        
        return TestUserResponse(
            success=True,
            message=f"Created {len(created_users)} test users",
            users_created=created_users
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/list-employees")
async def list_employees():
    """List all employees in database"""
    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, username, role, department, is_super_admin, active, created_at
            FROM employees
            ORDER BY created_at DESC
        """)
        
        employees = []
        for row in cur.fetchall():
            employees.append({
                'id': row[0],
                'username': row[1],
                'role': row[2],
                'department': row[3],
                'is_super_admin': row[4],
                'active': row[5],
                'created_at': row[6].isoformat() if row[6] else None
            })
        
        cur.close()
        conn.close()
        
        return {
            'success': True,
            'count': len(employees),
            'employees': employees
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

