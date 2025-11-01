-- Migration: Add WhatsApp Chat Settings
-- Description: Add settings table to control WhatsApp chat widget visibility on website

-- Create settings table if not exists
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(255) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(50) DEFAULT 'string',
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER
);

-- Insert WhatsApp chat setting
INSERT INTO system_settings (setting_key, setting_value, setting_type, description)
VALUES ('whatsapp_chat_enabled', 'true', 'boolean', 'Enable/disable WhatsApp chat widget on website')
ON CONFLICT (setting_key) DO NOTHING;

-- Insert WhatsApp number setting
INSERT INTO system_settings (setting_key, setting_value, setting_type, description)
VALUES ('whatsapp_chat_number', '+919361440568', 'string', 'WhatsApp number for chat widget')
ON CONFLICT (setting_key) DO NOTHING;

-- Insert WhatsApp welcome message setting
INSERT INTO system_settings (setting_key, setting_value, setting_type, description)
VALUES ('whatsapp_chat_message', 'Hello! How can we help you today?', 'string', 'Default WhatsApp chat message')
ON CONFLICT (setting_key) DO NOTHING;
