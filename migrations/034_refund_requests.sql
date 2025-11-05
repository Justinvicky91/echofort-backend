-- Migration: Create refund_requests table for 24-hour refund policy
-- Date: 2025-11-05
-- Purpose: Track refund requests and enforce 24-hour policy

-- Create refund_requests table
CREATE TABLE IF NOT EXISTS refund_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    invoice_id VARCHAR(50) REFERENCES invoices(invoice_id),
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
CREATE TRIGGER trg_calculate_hours_since_payment
BEFORE INSERT OR UPDATE ON refund_requests
FOR EACH ROW
EXECUTE FUNCTION calculate_hours_since_payment();

COMMENT ON TABLE refund_requests IS 'Tracks refund requests with 24-hour policy enforcement';
COMMENT ON COLUMN refund_requests.hours_since_payment IS 'Hours elapsed between payment and refund request';
COMMENT ON COLUMN refund_requests.within_24_hours IS 'Whether request is within 24-hour refund window';
COMMENT ON COLUMN refund_requests.status IS 'Request status: pending, approved, rejected, processed, failed';
