-- Migration: Update payment_gateways table schema
-- Date: 2025-10-29
-- Purpose: Add missing columns for full payment gateway configuration

-- Rename existing columns to match code expectations
ALTER TABLE payment_gateways 
  RENAME COLUMN api_key TO api_key_encrypted;

ALTER TABLE payment_gateways 
  RENAME COLUMN api_secret TO secret_key_encrypted;

ALTER TABLE payment_gateways 
  RENAME COLUMN is_active TO enabled;

-- Add missing columns
ALTER TABLE payment_gateways 
  ADD COLUMN IF NOT EXISTS test_mode BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS webhook_secret_encrypted TEXT,
  ADD COLUMN IF NOT EXISTS supported_currencies TEXT DEFAULT '["INR"]',
  ADD COLUMN IF NOT EXISTS supported_regions TEXT DEFAULT '["India"]',
  ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 1,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS created_by INTEGER,
  ADD COLUMN IF NOT EXISTS updated_by INTEGER;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_payment_gateways_name ON payment_gateways(gateway_name);
CREATE INDEX IF NOT EXISTS idx_payment_gateways_enabled ON payment_gateways(enabled);

-- Add comments
COMMENT ON TABLE payment_gateways IS 'Payment gateway configurations for EchoFort platform';
COMMENT ON COLUMN payment_gateways.api_key_encrypted IS 'Encrypted API key using Fernet encryption';
COMMENT ON COLUMN payment_gateways.secret_key_encrypted IS 'Encrypted secret key using Fernet encryption';
COMMENT ON COLUMN payment_gateways.webhook_secret_encrypted IS 'Encrypted webhook secret for payment callbacks';
COMMENT ON COLUMN payment_gateways.supported_currencies IS 'JSON array of supported currency codes';
COMMENT ON COLUMN payment_gateways.supported_regions IS 'JSON array of supported regions/countries';
