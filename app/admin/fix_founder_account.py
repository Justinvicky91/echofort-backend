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
            # Update to super_admin role
            await db.execute(
                text("""
                UPDATE employees 
                SET role = 'super_admin',
                    is_super_admin = true,
                    department = 'Executive'
                WHERE id = :id
                """),
                {"id": account["id"]}
            )
            
            # Fetch updated account
            updated_result = await db.execute(
                text("SELECT id, username, role, is_super_admin, department FROM employees WHERE id = :id"),
                {"id": account["id"]}
            )
            updated = updated_result.first()
            
            results.append({
                "id": account["id"],
                "username": account["username"],
                "before": {
                    "role": account["role"],
                    "is_super_admin": account["is_super_admin"],
                    "department": account["department"],
                },
                "after": {
                    "role": updated["role"],
                    "is_super_admin": updated["is_super_admin"],
                    "department": updated["department"],
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
