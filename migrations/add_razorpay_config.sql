-- Add Razorpay configuration to payment_gateways table
-- This will be automatically applied on next backend restart

INSERT INTO payment_gateways (
    gateway_name,
    api_key,
    secret_key,
    webhook_secret,
    enabled,
    test_mode,
    supported_currencies,
    supported_regions,
    priority,
    created_at,
    updated_at
) VALUES (
    'razorpay',
    'rzp_live_RaVY92nlBc6XrE',
    'Byz4CcXbUnustnAKgU3EprCy',
    'https://api.echofort.ai/webhooks/razorpay',
    TRUE,
    FALSE,  -- Set to FALSE since using live keys
    ARRAY['INR'],
    ARRAY['India'],
    1,
    NOW(),
    NOW()
)
ON CONFLICT (gateway_name) 
DO UPDATE SET
    api_key = EXCLUDED.api_key,
    secret_key = EXCLUDED.secret_key,
    enabled = EXCLUDED.enabled,
    test_mode = EXCLUDED.test_mode,
    updated_at = NOW();

-- Disable other gateways to make Razorpay the primary
UPDATE payment_gateways 
SET enabled = FALSE 
WHERE gateway_name != 'razorpay';
