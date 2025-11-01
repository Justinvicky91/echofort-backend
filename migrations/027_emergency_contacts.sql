-- Emergency Contacts System
-- Emergency contacts and SOS alert functionality

-- Emergency Contacts
CREATE TABLE IF NOT EXISTS emergency_contacts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    relationship VARCHAR(100),
    email VARCHAR(255),
    is_primary BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 1 CHECK (priority >= 1 AND priority <= 10),
    notify_on_emergency BOOLEAN DEFAULT TRUE,
    notify_on_location_alert BOOLEAN DEFAULT FALSE,
    notify_on_scam_alert BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_emergency_contacts_user ON emergency_contacts(user_id);
CREATE INDEX IF NOT EXISTS idx_emergency_contacts_priority ON emergency_contacts(user_id, priority);

-- Emergency Alerts
CREATE TABLE IF NOT EXISTS emergency_alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL, -- sos, panic, location_alert, scam_alert, etc.
    severity VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    message TEXT,
    location_lat DECIMAL(10, 8),
    location_lng DECIMAL(11, 8),
    location_accuracy FLOAT,
    location_address TEXT,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active', -- active, resolved, false_alarm
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_emergency_alerts_user ON emergency_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_emergency_alerts_status ON emergency_alerts(status);
CREATE INDEX IF NOT EXISTS idx_emergency_alerts_triggered ON emergency_alerts(triggered_at DESC);

-- Emergency Alert Notifications (tracking who was notified)
CREATE TABLE IF NOT EXISTS emergency_alert_notifications (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER NOT NULL REFERENCES emergency_alerts(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES emergency_contacts(id) ON DELETE SET NULL,
    contact_phone VARCHAR(20) NOT NULL,
    contact_name VARCHAR(255),
    notification_method VARCHAR(20) NOT NULL, -- sms, call, push, email
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, delivered, failed
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alert_notifications_alert ON emergency_alert_notifications(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_notifications_contact ON emergency_alert_notifications(contact_id);

-- SOS Settings
CREATE TABLE IF NOT EXISTS sos_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    sos_enabled BOOLEAN DEFAULT TRUE,
    auto_call_emergency BOOLEAN DEFAULT FALSE,
    emergency_number VARCHAR(20) DEFAULT '112', -- Default emergency number
    countdown_seconds INTEGER DEFAULT 5 CHECK (countdown_seconds >= 0 AND countdown_seconds <= 30),
    share_location BOOLEAN DEFAULT TRUE,
    share_audio BOOLEAN DEFAULT FALSE,
    share_video BOOLEAN DEFAULT FALSE,
    auto_record_audio BOOLEAN DEFAULT TRUE,
    auto_record_video BOOLEAN DEFAULT FALSE,
    silent_mode BOOLEAN DEFAULT FALSE, -- No sound/vibration during SOS
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Emergency Response Log
CREATE TABLE IF NOT EXISTS emergency_response_log (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER NOT NULL REFERENCES emergency_alerts(id) ON DELETE CASCADE,
    responder_type VARCHAR(50), -- contact, emergency_services, admin
    responder_id INTEGER,
    responder_name VARCHAR(255),
    response_type VARCHAR(50), -- acknowledged, en_route, arrived, resolved
    response_message TEXT,
    response_location_lat DECIMAL(10, 8),
    response_location_lng DECIMAL(11, 8),
    responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_response_log_alert ON emergency_response_log(alert_id);

-- Function to trigger emergency alert
CREATE OR REPLACE FUNCTION trigger_emergency_alert(
    p_user_id INTEGER,
    p_alert_type VARCHAR(50),
    p_severity VARCHAR(20),
    p_message TEXT,
    p_location_lat DECIMAL(10, 8) DEFAULT NULL,
    p_location_lng DECIMAL(11, 8) DEFAULT NULL,
    p_location_accuracy FLOAT DEFAULT NULL,
    p_location_address TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_alert_id INTEGER;
    v_contact RECORD;
    v_settings RECORD;
BEGIN
    -- Create emergency alert
    INSERT INTO emergency_alerts 
    (user_id, alert_type, severity, message, location_lat, location_lng, 
     location_accuracy, location_address, metadata, status)
    VALUES (p_user_id, p_alert_type, p_severity, p_message, p_location_lat, p_location_lng,
            p_location_accuracy, p_location_address, p_metadata, 'active')
    RETURNING id INTO v_alert_id;
    
    -- Get SOS settings
    SELECT * INTO v_settings FROM sos_settings WHERE user_id = p_user_id;
    
    -- If no settings, use defaults
    IF v_settings IS NULL THEN
        INSERT INTO sos_settings (user_id) VALUES (p_user_id);
        SELECT * INTO v_settings FROM sos_settings WHERE user_id = p_user_id;
    END IF;
    
    -- Notify all emergency contacts
    FOR v_contact IN 
        SELECT * FROM emergency_contacts 
        WHERE user_id = p_user_id AND notify_on_emergency = TRUE
        ORDER BY priority ASC
    LOOP
        -- Queue SMS notification
        INSERT INTO emergency_alert_notifications 
        (alert_id, contact_id, contact_phone, contact_name, notification_method, status)
        VALUES (v_alert_id, v_contact.id, v_contact.phone, v_contact.name, 'sms', 'pending');
        
        -- Queue push notification if contact is also a user
        INSERT INTO emergency_alert_notifications 
        (alert_id, contact_id, contact_phone, contact_name, notification_method, status)
        VALUES (v_alert_id, v_contact.id, v_contact.phone, v_contact.name, 'push', 'pending');
    END LOOP;
    
    -- Send push notification to user
    PERFORM queue_notification(
        p_user_id,
        'Emergency Alert Triggered',
        'Your emergency alert has been sent to your contacts',
        'emergency_alert',
        'urgent',
        jsonb_build_object('alertId', v_alert_id, 'alertType', p_alert_type)
    );
    
    RETURN v_alert_id;
END;
$$ LANGUAGE plpgsql;

-- Function to resolve emergency alert
CREATE OR REPLACE FUNCTION resolve_emergency_alert(
    p_alert_id INTEGER,
    p_resolved_by INTEGER DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE emergency_alerts
    SET status = 'resolved',
        resolved_at = CURRENT_TIMESTAMP
    WHERE id = p_alert_id AND status = 'active';
    
    IF FOUND THEN
        -- Log resolution
        INSERT INTO emergency_response_log 
        (alert_id, responder_id, response_type, response_message)
        VALUES (p_alert_id, p_resolved_by, 'resolved', 'Emergency alert resolved');
        
        RETURN TRUE;
    ELSE
        RETURN FALSE;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE emergency_contacts IS 'User emergency contacts';
COMMENT ON TABLE emergency_alerts IS 'Emergency SOS alerts';
COMMENT ON TABLE emergency_alert_notifications IS 'Tracking of emergency notifications sent';
COMMENT ON TABLE sos_settings IS 'User SOS settings';
COMMENT ON TABLE emergency_response_log IS 'Emergency response tracking';
