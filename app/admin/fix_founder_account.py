"""
Fix Founder's SuperAdmin Account

One-time endpoint to ensure the Founder's account has super_admin role.
"""

from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/fix-founder-account")
async def fix_founder_account(request: Request):
    """
    One-time migration to fix the Founder's account.
    
    Ensures:
    - Role is set to 'super_admin'
    - is_super_admin flag is true
    - Department is set appropriately
    """
    db = request.app.state.db
    
    try:
        from sqlalchemy import text
        
        # Find the Founder's account by username pattern
        # Looking for @EchofortSuperAdmin91 or similar
        result = await db.execute(
            text("""
            SELECT id, username, role, is_super_admin, department 
            FROM employees 
            WHERE username ILIKE '%echofort%' 
               OR username ILIKE '%superadmin%'
               OR username ILIKE '%founder%'
               OR id = 1
            ORDER BY id
            """)
        )
        founder_accounts = result.fetchall()
        
        if not founder_accounts:
            return {
                "success": False,
                "message": "No founder account found",
                "searched_patterns": ["echofort", "superadmin", "founder", "id=1"]
            }
        
        results = []
        for account in founder_accounts:
            # account is a tuple: (id, username, role, is_super_admin, department)
            account_id, username, role, is_super_admin, department = account
            
            # Update to super_admin role
            await db.execute(
                text("""
                UPDATE employees 
                SET role = 'super_admin',
                    is_super_admin = true,
                    department = 'Executive'
                WHERE id = :id
                """),
                {"id": account_id}
            )
            
            # Fetch updated account
            updated_result = await db.execute(
                text("SELECT id, username, role, is_super_admin, department FROM employees WHERE id = :id"),
                {"id": account_id}
            )
            updated = updated_result.first()
            # updated is also a tuple: (id, username, role, is_super_admin, department)
            
            results.append({
                "id": account_id,
                "username": username,
                "before": {
                    "role": role,
                    "is_super_admin": is_super_admin,
                    "department": department,
                },
                "after": {
                    "role": updated[2],  # role is 3rd column
                    "is_super_admin": updated[3],  # is_super_admin is 4th column
                    "department": updated[4],  # department is 5th column
                }
            })
        
        return {
            "success": True,
            "message": f"Fixed {len(results)} account(s)",
            "accounts": results,
            "note": "All matching accounts have been updated to super_admin role"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error fixing founder account: {str(e)}")
