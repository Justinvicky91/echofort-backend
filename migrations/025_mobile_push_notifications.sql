-- Mobile Push Notifications System
-- Real-time alerts and notifications for mobile devices

-- Device Tokens (for push notifications)
CREATE TABLE IF NOT EXISTS device_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_token TEXT NOT NULL UNIQUE,
    platform VARCHAR(20) NOT NULL, -- ios, android
    device_model VARCHAR(100),
    os_version VARCHAR(50),
    app_version VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_device_tokens_user ON device_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_device_tokens_token ON device_tokens(device_token);
CREATE INDEX IF NOT EXISTS idx_device_tokens_active ON device_tokens(is_active);

-- Push Notifications
CREATE TABLE IF NOT EXISTS push_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    device_token_id INTEGER REFERENCES device_tokens(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    notification_type VARCHAR(50) NOT NULL, -- scam_alert, family_alert, call_blocked, sms_threat, etc.
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    data JSONB, -- Additional data payload
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, delivered, failed
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_push_notif_user ON push_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_push_notif_status ON push_notifications(status);
CREATE INDEX IF NOT EXISTS idx_push_notif_type ON push_notifications(notification_type);
CREATE INDEX IF NOT EXISTS idx_push_notif_created ON push_notifications(created_at DESC);

-- Notification Settings (per user)
CREATE TABLE IF NOT EXISTS notification_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    enable_scam_alerts BOOLEAN DEFAULT TRUE,
    enable_family_alerts BOOLEAN DEFAULT TRUE,
    enable_call_alerts BOOLEAN DEFAULT TRUE,
    enable_sms_alerts BOOLEAN DEFAULT TRUE,
    enable_location_alerts BOOLEAN DEFAULT TRUE,
    enable_app_usage_alerts BOOLEAN DEFAULT TRUE,
    enable_emergency_alerts BOOLEAN DEFAULT TRUE,
    enable_marketing BOOLEAN DEFAULT FALSE,
    quiet_hours_enabled BOOLEAN DEFAULT FALSE,
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notification Templates
CREATE TABLE IF NOT EXISTS notification_templates (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL UNIQUE,
    notification_type VARCHAR(50) NOT NULL,
    title_template VARCHAR(255) NOT NULL,
    body_template TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    variables JSONB, -- List of variables that can be used
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notification Statistics
CREATE TABLE IF NOT EXISTS notification_statistics (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    total_sent INTEGER DEFAULT 0,
    total_delivered INTEGER DEFAULT 0,
    total_read INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    last_notification_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default notification templates
INSERT INTO notification_templates (template_name, notification_type, title_template, body_template, priority, variables) VALUES
('scam_call_blocked', 'scam_alert', 'Scam Call Blocked', 'Blocked call from {{phoneNumber}} with spam score {{spamScore}}', 'high', '{"phoneNumber": "string", "spamScore": "number"}'),
('sms_threat_detected', 'scam_alert', 'SMS Threat Detected', 'Suspicious SMS from {{sender}}: {{preview}}', 'high', '{"sender": "string", "preview": "string"}'),
('phishing_url_detected', 'scam_alert', 'Phishing URL Detected', 'Dangerous website detected: {{domain}}', 'high', '{"domain": "string"}'),
('child_location_alert', 'family_alert', 'Location Alert', '{{childName}} has left {{geofenceName}}', 'high', '{"childName": "string", "geofenceName": "string"}'),
('screen_time_limit', 'family_alert', 'Screen Time Limit Reached', '{{childName}} has reached daily screen time limit', 'normal', '{"childName": "string"}'),
('inappropriate_content', 'family_alert', 'Inappropriate Content Detected', 'Flagged content detected on {{childName}}\'s device', 'high', '{"childName": "string"}'),
('emergency_alert', 'emergency_alert', 'Emergency Alert', '{{contactName}} has triggered an emergency alert', 'urgent', '{"contactName": "string", "location": "string"}'),
('dark_web_breach', 'security_alert', 'Dark Web Alert', 'Your {{dataType}} was found on the dark web', 'urgent', '{"dataType": "string"}'),
('malware_detected', 'security_alert', 'Malware Detected', 'Malicious app detected: {{appName}}', 'urgent', '{"appName": "string"}'),
('subscription_expiring', 'account_alert', 'Subscription Expiring', 'Your subscription expires in {{days}} days', 'normal', '{"days": "number"}'),
('payment_successful', 'account_alert', 'Payment Successful', 'Payment of {{amount}} received successfully', 'normal', '{"amount": "string"}')
ON CONFLICT (template_name) DO NOTHING;

-- Function to send notification (marks as pending, actual sending done by background worker)
CREATE OR REPLACE FUNCTION queue_notification(
    p_user_id INTEGER,
    p_title VARCHAR(255),
    p_body TEXT,
    p_notification_type VARCHAR(50),
    p_priority VARCHAR(20) DEFAULT 'normal',
    p_data JSONB DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_notification_id INTEGER;
    v_settings RECORD;
BEGIN
    -- Check user's notification settings
    SELECT * INTO v_settings FROM notification_settings WHERE user_id = p_user_id;
    
    -- If no settings, create default
    IF v_settings IS NULL THEN
        INSERT INTO notification_settings (user_id) VALUES (p_user_id);
        SELECT * INTO v_settings FROM notification_settings WHERE user_id = p_user_id;
    END IF;
    
    -- Check if notification type is enabled
    IF (p_notification_type = 'scam_alert' AND NOT v_settings.enable_scam_alerts) OR
       (p_notification_type = 'family_alert' AND NOT v_settings.enable_family_alerts) OR
       (p_notification_type = 'call_alert' AND NOT v_settings.enable_call_alerts) OR
       (p_notification_type = 'sms_alert' AND NOT v_settings.enable_sms_alerts) THEN
        RETURN NULL; -- Don't send if disabled
    END IF;
    
    -- Check quiet hours
    IF v_settings.quiet_hours_enabled AND 
       CURRENT_TIME BETWEEN v_settings.quiet_hours_start AND v_settings.quiet_hours_end AND
       p_priority != 'urgent' THEN
        RETURN NULL; -- Don't send during quiet hours unless urgent
    END IF;
    
    -- Create notification
    INSERT INTO push_notifications (user_id, title, body, notification_type, priority, data, status)
    VALUES (p_user_id, p_title, p_body, p_notification_type, p_priority, p_data, 'pending')
    RETURNING id INTO v_notification_id;
    
    -- Update statistics
    INSERT INTO notification_statistics (user_id, total_sent, last_notification_at)
    VALUES (p_user_id, 1, CURRENT_TIMESTAMP)
    ON CONFLICT (user_id) DO UPDATE
    SET total_sent = notification_statistics.total_sent + 1,
        last_notification_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP;
    
    RETURN v_notification_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE device_tokens IS 'Device tokens for push notifications';
COMMENT ON TABLE push_notifications IS 'Push notification queue and history';
COMMENT ON TABLE notification_settings IS 'Per-user notification preferences';
COMMENT ON TABLE notification_templates IS 'Notification message templates';
COMMENT ON TABLE notification_statistics IS 'Notification delivery statistics';
