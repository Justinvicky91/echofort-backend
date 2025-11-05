-- Migration: Create invoices table for auto-invoice generation
-- Date: 2025-11-05
-- Purpose: Store invoice records for subscription payments

-- Create invoices table
CREATE TABLE IF NOT EXISTS invoices (
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

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_id ON invoices(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoices_transaction_id ON invoices(transaction_id);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_email_sent ON invoices(email_sent);

-- Create invoice sequence for generating invoice numbers
CREATE SEQUENCE IF NOT EXISTS invoice_number_seq START 1000;

COMMENT ON TABLE invoices IS 'Stores invoice records for subscription payments with PDF generation and email dispatch';
COMMENT ON COLUMN invoices.invoice_id IS 'Unique invoice identifier (e.g., INV-2025-001)';
COMMENT ON COLUMN invoices.pdf_generated IS 'Whether PDF invoice has been generated';
COMMENT ON COLUMN invoices.email_sent IS 'Whether invoice email has been sent to customer';
