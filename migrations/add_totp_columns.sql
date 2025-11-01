-- Add TOTP 2FA columns to employees table
-- Run this migration to enable Google Authenticator 2FA

-- Add totp_secret column (stores the TOTP secret key)
ALTER TABLE employees 
ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(32);

-- Add totp_enabled column (tracks if TOTP is enabled for the user)
ALTER TABLE employees 
ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_employees_totp_enabled 
ON employees(totp_enabled) 
WHERE totp_enabled = TRUE;

-- Add comment
COMMENT ON COLUMN employees.totp_secret IS 'Google Authenticator TOTP secret (Base32 encoded)';
COMMENT ON COLUMN employees.totp_enabled IS 'Whether Google Authenticator 2FA is enabled';

-- Verify columns were added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'employees' 
AND column_name IN ('totp_secret', 'totp_enabled');
