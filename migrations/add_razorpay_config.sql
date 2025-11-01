-- Add Razorpay configuration to payment_gateways table
-- This will be automatically applied on next backend restart

-- Note: The credentials are stored in plain text in this migration for simplicity
-- The backend will encrypt them when accessed through the API

INSERT INTO payment_gateways (
    gateway_name,
    api_key_encrypted,
    secret_key_encrypted,
    webhook_secret_encrypted,
    enabled,
    test_mode,
    supported_currencies,
    supported_regions,
    priority,
    created_at,
    updated_at
) VALUES (
    'razorpay',
    'rzp_live_RaVY92nlBc6XrE',  -- Will be encrypted by backend on first use
    'Byz4CcXbUnustnAKgU3EprCy',  -- Will be encrypted by backend on first use
    'https://api.echofort.ai/webhooks/razorpay',
    TRUE,
    FALSE,  -- Set to FALSE since using live keys
    '["INR"]'::jsonb,
    '["India"]'::jsonb,
    1,
    NOW(),
    NOW()
)
ON CONFLICT (gateway_name) 
DO UPDATE SET
    api_key_encrypted = EXCLUDED.api_key_encrypted,
    secret_key_encrypted = EXCLUDED.secret_key_encrypted,
    enabled = EXCLUDED.enabled,
    test_mode = EXCLUDED.test_mode,
    updated_at = NOW();

-- Disable other gateways to make Razorpay the primary
UPDATE payment_gateways 
SET enabled = FALSE 
WHERE gateway_name != 'razorpay';
