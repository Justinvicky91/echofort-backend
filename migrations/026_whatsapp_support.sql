-- Migration: Add WhatsApp support columns
-- Date: 2025-10-26
-- Description: Add columns for WhatsApp ticket support

-- Add source column to support_tickets (email/whatsapp)
ALTER TABLE support_tickets 
ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'email' AFTER message;

-- Add customer_phone column
ALTER TABLE support_tickets 
ADD COLUMN IF NOT EXISTS customer_phone VARCHAR(20) AFTER customer_email;

-- Add index for phone number lookups
CREATE INDEX IF NOT EXISTS idx_customer_phone ON support_tickets(customer_phone);

-- Add index for source filtering
CREATE INDEX IF NOT EXISTS idx_source ON support_tickets(source);

-- Add whatsapp_message_sid to support_messages
ALTER TABLE support_messages 
ADD COLUMN IF NOT EXISTS whatsapp_message_sid VARCHAR(100) AFTER message;

-- Add index for WhatsApp message SID
CREATE INDEX IF NOT EXISTS idx_whatsapp_sid ON support_messages(whatsapp_message_sid);

-- Update existing tickets to have 'email' source
UPDATE support_tickets SET source = 'email' WHERE source IS NULL;

-- Add comment
ALTER TABLE support_tickets MODIFY COLUMN source VARCHAR(20) DEFAULT 'email' COMMENT 'Source of ticket: email, whatsapp, chat, phone';

-- Success message
SELECT 'WhatsApp support migration completed successfully' AS status;

