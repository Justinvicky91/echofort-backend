-- Add KYC and address fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS full_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS email VARCHAR(255),
ADD COLUMN IF NOT EXISTS phone VARCHAR(20),
ADD COLUMN IF NOT EXISTS address_line1 VARCHAR(500),
ADD COLUMN IF NOT EXISTS address_line2 VARCHAR(500),
ADD COLUMN IF NOT EXISTS city VARCHAR(100),
ADD COLUMN IF NOT EXISTS district VARCHAR(100),
ADD COLUMN IF NOT EXISTS state VARCHAR(100),
ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'India',
ADD COLUMN IF NOT EXISTS pincode VARCHAR(20),
ADD COLUMN IF NOT EXISTS id_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS id_number VARCHAR(100),
ADD COLUMN IF NOT EXISTS id_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS kyc_status VARCHAR(50) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS kyc_verified_at TIMESTAMP;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_kyc_status ON users(kyc_status);

COMMENT ON COLUMN users.full_name IS 'User full name for KYC';
COMMENT ON COLUMN users.address_line1 IS 'Primary address line';
COMMENT ON COLUMN users.id_type IS 'ID type: Aadhaar, PAN, Passport, Driving License';
COMMENT ON COLUMN users.id_number IS 'Government ID number';
COMMENT ON COLUMN users.kyc_status IS 'KYC verification status: pending, verified, rejected';
