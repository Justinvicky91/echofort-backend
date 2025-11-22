-- Add user_id column to invoices table if it doesn't exist
-- This column was in the original schema but may not have been applied

DO $$ 
BEGIN
    -- Check if user_id column exists
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'invoices' 
        AND column_name = 'user_id'
    ) THEN
        -- Add user_id column
        ALTER TABLE invoices 
        ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
        
        -- Create index
        CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
    END IF;
END $$;
