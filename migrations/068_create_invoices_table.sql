-- Migration 068: Create invoices table for payment invoice management
-- BLOCK INVOICE-EMAIL Phase 1
-- Created: 2025-12-03

CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_id TEXT NOT NULL,
    payment_id TEXT,
    amount INTEGER NOT NULL, -- Amount in paise (₹1 = 100 paise)
    currency TEXT NOT NULL DEFAULT 'INR',
    is_internal_test BOOLEAN NOT NULL DEFAULT false,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('paid', 'failed', 'pending')),
    pdf_url TEXT,
    html_content TEXT,
    invoice_number TEXT UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_invoices_order_id ON invoices(order_id);
CREATE INDEX IF NOT EXISTS idx_invoices_payment_id ON invoices(payment_id);
CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at DESC);

-- Create trigger to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_invoices_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_invoices_updated_at
    BEFORE UPDATE ON invoices
    FOR EACH ROW
    EXECUTE FUNCTION update_invoices_updated_at();

-- Create function to generate invoice numbers
CREATE OR REPLACE FUNCTION generate_invoice_number()
RETURNS TEXT AS $$
DECLARE
    next_id INTEGER;
    invoice_num TEXT;
BEGIN
    -- Get the next sequence value
    SELECT COALESCE(MAX(id), 0) + 1 INTO next_id FROM invoices;
    
    -- Format: INV-YYYYMM-XXXXX (e.g., INV-202512-00001)
    invoice_num := 'INV-' || TO_CHAR(NOW(), 'YYYYMM') || '-' || LPAD(next_id::TEXT, 5, '0');
    
    RETURN invoice_num;
END;
$$ LANGUAGE plpgsql;

-- Add comment to table
COMMENT ON TABLE invoices IS 'Stores payment invoices for all transactions including internal tests and real customer payments';
COMMENT ON COLUMN invoices.amount IS 'Amount in paise (100 paise = ₹1)';
COMMENT ON COLUMN invoices.is_internal_test IS 'True for ₹1 internal test payments, false for real customer payments';
COMMENT ON COLUMN invoices.invoice_number IS 'Auto-generated unique invoice number (format: INV-YYYYMM-XXXXX)';
