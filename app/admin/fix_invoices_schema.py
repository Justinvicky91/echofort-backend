"""
Admin endpoint to manually fix invoices table schema
This bypasses the broken migration system
"""
from fastapi import APIRouter, Depends
from app.utils import require_super_admin
from app.deps import get_settings
import psycopg

router = APIRouter(prefix="/admin/fix", tags=["admin-fix"])

@router.post("/invoices-schema")
def fix_invoices_schema(user: dict = Depends(require_super_admin)):
    """
    Manually drop and recreate invoices table with correct schema.
    This endpoint bypasses the broken migration system.
    
    **WARNING:** This will delete all existing invoice data!
    """
    
    sql = """
-- Drop existing invoices table
DROP TABLE IF EXISTS invoices CASCADE;

-- Recreate with correct schema
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    invoice_id VARCHAR(50) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    subscription_id INTEGER,
    plan_name VARCHAR(100) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    transaction_id VARCHAR(100),
    razorpay_payment_id VARCHAR(100),
    razorpay_order_id VARCHAR(100),
    file_path VARCHAR(255),
    pdf_generated BOOLEAN DEFAULT FALSE,
    email_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    
    -- Business details
    business_name VARCHAR(255) DEFAULT 'EchoFort AI Private Limited',
    business_gstin VARCHAR(50) DEFAULT 'XXXXX',
    business_address TEXT DEFAULT 'Bangalore, India',
    
    -- Customer details
    customer_name VARCHAR(255),
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),
    customer_address TEXT,
    
    -- Invoice metadata
    invoice_date DATE DEFAULT CURRENT_DATE,
    due_date DATE,
    status VARCHAR(20) DEFAULT 'paid',
    notes TEXT
);

-- Create indexes
CREATE INDEX idx_invoices_user_id ON invoices(user_id);
CREATE INDEX idx_invoices_invoice_id ON invoices(invoice_id);
CREATE INDEX idx_invoices_transaction_id ON invoices(transaction_id);
CREATE INDEX idx_invoices_created_at ON invoices(created_at DESC);
CREATE INDEX idx_invoices_email_sent ON invoices(email_sent);

-- Insert sample data
INSERT INTO invoices (
    invoice_id, 
    user_id, 
    plan_name, 
    amount, 
    customer_name, 
    customer_email,
    razorpay_payment_id,
    status,
    invoice_date
) VALUES 
(
    'INV-2025-001',
    1,
    'Premium Monthly',
    499.00,
    'Test User 1',
    'test1@example.com',
    'pay_test123456',
    'paid',
    CURRENT_DATE - INTERVAL '5 days'
),
(
    'INV-2025-002',
    1,
    'Enterprise Annual',
    5999.00,
    'Test User 2',
    'test2@example.com',
    'pay_test789012',
    'paid',
    CURRENT_DATE - INTERVAL '2 days'
);
"""
    
    try:
        settings = get_settings()
        dsn = settings.DATABASE_URL
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        
        return {
            "ok": True,
            "message": "Invoices table schema fixed successfully",
            "details": {
                "action": "DROP and CREATE invoices table",
                "sample_rows_inserted": 2
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": "Failed to fix invoices schema"
        }
