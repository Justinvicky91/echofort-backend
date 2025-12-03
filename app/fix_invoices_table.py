"""
Fix invoices table schema
BLOCK S1 Phase 2 - Add missing columns for invoice system
"""
from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.post("/fix-invoices-table")
async def fix_invoices_table(request: Request):
    """
    Add missing columns to invoices table
    """
    try:
        db = request.app.state.db
        
        # Add missing columns
        await db.execute(text("""
            ALTER TABLE invoices 
            ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(50) UNIQUE,
            ADD COLUMN IF NOT EXISTS is_internal_test BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS invoice_html TEXT,
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """))
        
        # Create index on invoice_number
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoices(invoice_number)
        """))
        
        # Create index on is_internal_test
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_is_internal_test ON invoices(is_internal_test)
        """))
        
        return {
            "ok": True,
            "message": "Invoices table schema fixed successfully"
        }
    
    except Exception as e:
        print(f"❌ Error fixing invoices table: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "ok": False,
            "error": str(e)
        }
