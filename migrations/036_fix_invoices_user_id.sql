-- Migration: Fix invoices table - add user_id column
-- Date: 2025-11-05
-- Purpose: Add missing user_id column to invoices table for Super Admin billing queries

-- Add user_id column if it doesn't exist
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add foreign key constraint
ALTER TABLE invoices DROP CONSTRAINT IF EXISTS fk_invoices_user;
ALTER TABLE invoices ADD CONSTRAINT fk_invoices_user 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);

-- Update existing invoices without user_id (if any)
-- This sets user_id to NULL for orphaned invoices
-- In production, you may want to link them to actual users
UPDATE invoices SET user_id = NULL WHERE user_id IS NULL;

-- Add comment
COMMENT ON COLUMN invoices.user_id IS 'Foreign key to users table - identifies invoice owner';
