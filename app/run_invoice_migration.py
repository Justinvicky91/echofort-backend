"""
One-time migration runner for invoices table
"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text

router = APIRouter(prefix="/api/admin", tags=["Admin Migrations"])


@router.post("/create-invoices-table")
async def create_invoices_table(request: Request):
    """
    Create invoices table and related functions
    """
    try:
        db = request.app.state.db
        
        # Create invoices table
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                order_id VARCHAR(255) NOT NULL,
                payment_id VARCHAR(255) NOT NULL,
                amount INTEGER NOT NULL,
                currency VARCHAR(10) NOT NULL DEFAULT 'INR',
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                invoice_number VARCHAR(100) UNIQUE NOT NULL,
                html_content TEXT,
                pdf_url TEXT,
                is_internal_test BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        
        # Create indexes
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_invoices_order_id ON invoices(order_id)"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_invoices_payment_id ON invoices(payment_id)"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id)"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at)"))
        
        # Create invoice number generator function
        await db.execute(text("""
            CREATE OR REPLACE FUNCTION generate_invoice_number()
            RETURNS TEXT AS $$
            DECLARE
                invoice_num TEXT;
            BEGIN
                SELECT 'INV-' || TO_CHAR(NOW(), 'YYYYMM') || '-' || 
                       LPAD((SELECT COUNT(*) + 1 FROM invoices 
                             WHERE TO_CHAR(created_at, 'YYYYMM') = TO_CHAR(NOW(), 'YYYYMM'))::TEXT, 5, '0')
                INTO invoice_num;
                RETURN invoice_num;
            END;
            $$ LANGUAGE plpgsql
        """))
        
        # Create updated_at trigger function
        await db.execute(text("""
            CREATE OR REPLACE FUNCTION update_invoices_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """))
        
        # Create trigger
        await db.execute(text("""
            DROP TRIGGER IF EXISTS trigger_update_invoices_updated_at ON invoices
        """))
        
        await db.execute(text("""
            CREATE TRIGGER trigger_update_invoices_updated_at
            BEFORE UPDATE ON invoices
            FOR EACH ROW
            EXECUTE FUNCTION update_invoices_updated_at()
        """))
        
        return {
            "ok": True,
            "message": "Invoices table created successfully with indexes and functions"
        }
    
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise HTTPException(500, f"Migration failed: {str(e)}")
