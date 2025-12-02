-- Migration 053: Add name and email columns to employees table
-- Fixes P0 blocker: Customer Hub showing N/A for name and email

-- Add name column
ALTER TABLE employees 
ADD COLUMN IF NOT EXISTS name VARCHAR(255);

-- Add email column
ALTER TABLE employees 
ADD COLUMN IF NOT EXISTS email VARCHAR(255);

-- Add unique constraint on email
CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_email ON employees(email) WHERE email IS NOT NULL;

-- Add comments
COMMENT ON COLUMN employees.name IS 'Full name of the employee';
COMMENT ON COLUMN employees.email IS 'Email address of the employee (unique)';

-- Populate name and email for existing employees (using username as fallback)
UPDATE employees 
SET 
    name = CASE 
        WHEN username = 'EchofortSuperAdmin91' THEN 'Admin'
        WHEN username = 'testengineering' THEN 'Test Engineering'
        WHEN username = 'testlegal' THEN 'Test Legal'
        WHEN username = 'testmarketing' THEN 'Test Marketing'
        WHEN username = 'testsupport' THEN 'Test Support'
        WHEN username = 'hr1' THEN 'HR Manager'
        WHEN username = 'testadmin' THEN 'Test Admin'
        WHEN username = 'support1' THEN 'Support Agent'
        WHEN username = 'marketing1' THEN 'Marketing Manager'
        WHEN username = 'accounting1' THEN 'Accountant'
        ELSE INITCAP(REPLACE(username, '_', ' '))
    END,
    email = CASE 
        WHEN username = 'EchofortSuperAdmin91' THEN 'admin@echofort.ai'
        WHEN username = 'testengineering' THEN 'engineering@echofort.ai'
        WHEN username = 'testlegal' THEN 'legal@echofort.ai'
        WHEN username = 'testmarketing' THEN 'marketing@echofort.ai'
        WHEN username = 'testsupport' THEN 'support@echofort.ai'
        WHEN username = 'hr1' THEN 'hr@echofort.ai'
        WHEN username = 'testadmin' THEN 'testadmin@echofort.ai'
        WHEN username = 'support1' THEN 'support1@echofort.ai'
        WHEN username = 'marketing1' THEN 'marketing1@echofort.ai'
        WHEN username = 'accounting1' THEN 'accounting1@echofort.ai'
        ELSE username || '@echofort.ai'
    END
WHERE name IS NULL OR email IS NULL;
