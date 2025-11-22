"""
Admin endpoint to manually create refund_requests table
This bypasses the broken migration system
"""
from fastapi import APIRouter, Depends
from app.utils import require_super_admin
from app.deps import get_settings
import psycopg

router = APIRouter(prefix="/admin/fix", tags=["admin-fix"])

@router.post("/refunds-schema")
def fix_refunds_schema(user: dict = Depends(require_super_admin)):
    """
    Manually create refund_requests table with correct schema.
    This endpoint bypasses the broken migration system.
    """
    
    sql = """
-- Create refund_requests table
CREATE TABLE IF NOT EXISTS refund_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    invoice_id INTEGER REFERENCES invoices(id),
    razorpay_payment_id VARCHAR(100) NOT NULL,
    razorpay_order_id VARCHAR(100),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    
    -- Timestamps
    payment_date TIMESTAMP NOT NULL,
    request_date TIMESTAMP DEFAULT NOW(),
    processed_date TIMESTAMP,
    
    -- 24-hour validation
    hours_since_payment DECIMAL(5, 2),
    within_24_hours BOOLEAN DEFAULT TRUE,
    
    -- Razorpay refund details
    razorpay_refund_id VARCHAR(100),
    refund_status VARCHAR(20),
    refund_speed VARCHAR(20) DEFAULT 'normal',
    
    -- Admin details
    processed_by INTEGER REFERENCES users(id),
    admin_notes TEXT,
    
    -- Customer details
    customer_name VARCHAR(255),
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),
    
    CONSTRAINT chk_status CHECK (status IN ('pending', 'approved', 'rejected', 'processed', 'failed')),
    CONSTRAINT chk_refund_status CHECK (refund_status IS NULL OR refund_status IN ('pending', 'processed', 'failed'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_refund_requests_user_id ON refund_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_refund_requests_invoice_id ON refund_requests(invoice_id);
CREATE INDEX IF NOT EXISTS idx_refund_requests_payment_id ON refund_requests(razorpay_payment_id);
CREATE INDEX IF NOT EXISTS idx_refund_requests_status ON refund_requests(status);
CREATE INDEX IF NOT EXISTS idx_refund_requests_request_date ON refund_requests(request_date DESC);
CREATE INDEX IF NOT EXISTS idx_refund_requests_within_24h ON refund_requests(within_24_hours);

-- Create function to calculate hours since payment
CREATE OR REPLACE FUNCTION calculate_hours_since_payment()
RETURNS TRIGGER AS $$
BEGIN
    NEW.hours_since_payment := EXTRACT(EPOCH FROM (NEW.request_date - NEW.payment_date)) / 3600;
    NEW.within_24_hours := NEW.hours_since_payment <= 24;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-calculate hours on insert/update
DROP TRIGGER IF EXISTS trg_calculate_hours_since_payment ON refund_requests;
CREATE TRIGGER trg_calculate_hours_since_payment
BEFORE INSERT OR UPDATE ON refund_requests
FOR EACH ROW
EXECUTE FUNCTION calculate_hours_since_payment();
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
            "message": "Refund requests table schema created successfully",
            "details": {
                "action": "CREATE refund_requests table with trigger",
                "note": "Table created with 24-hour refund policy enforcement"
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": "Failed to create refund_requests schema"
        }
