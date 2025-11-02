-- Mobile Device Permissions Tracking
-- Tracks user mobile app permissions for Super Admin monitoring

CREATE TABLE IF NOT EXISTS user_device_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL,
    platform VARCHAR(20) NOT NULL, -- ios, android
    
    -- Permission statuses (granted, denied, not_requested, restricted)
    camera_permission VARCHAR(20) DEFAULT 'not_requested',
    microphone_permission VARCHAR(20) DEFAULT 'not_requested',
    location_permission VARCHAR(20) DEFAULT 'not_requested',
    sms_permission VARCHAR(20) DEFAULT 'not_requested',
    contacts_permission VARCHAR(20) DEFAULT 'not_requested',
    phone_permission VARCHAR(20) DEFAULT 'not_requested',
    storage_permission VARCHAR(20) DEFAULT 'not_requested',
    notification_permission VARCHAR(20) DEFAULT 'not_requested',
    
    -- Location-specific details
    location_accuracy VARCHAR(20), -- precise, approximate
    location_background BOOLEAN DEFAULT FALSE,
    location_always BOOLEAN DEFAULT FALSE,
    
    -- Permission request tracking
    camera_first_requested_at TIMESTAMP,
    camera_last_updated_at TIMESTAMP,
    microphone_first_requested_at TIMESTAMP,
    microphone_last_updated_at TIMESTAMP,
    location_first_requested_at TIMESTAMP,
    location_last_updated_at TIMESTAMP,
    sms_first_requested_at TIMESTAMP,
    sms_last_updated_at TIMESTAMP,
    contacts_first_requested_at TIMESTAMP,
    contacts_last_updated_at TIMESTAMP,
    phone_first_requested_at TIMESTAMP,
    phone_last_updated_at TIMESTAMP,
    storage_first_requested_at TIMESTAMP,
    storage_last_updated_at TIMESTAMP,
    notification_first_requested_at TIMESTAMP,
    notification_last_updated_at TIMESTAMP,
    
    -- Metadata
    app_version VARCHAR(50),
    os_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_device_permissions_user ON user_device_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_device_permissions_device ON user_device_permissions(device_id);
CREATE INDEX IF NOT EXISTS idx_device_permissions_platform ON user_device_permissions(platform);

-- Permission change history
CREATE TABLE IF NOT EXISTS permission_change_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(255),
    permission_type VARCHAR(50) NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_permission_history_user ON permission_change_history(user_id);
CREATE INDEX IF NOT EXISTS idx_permission_history_type ON permission_change_history(permission_type);

COMMENT ON TABLE user_device_permissions IS 'Mobile app device permissions tracking for Super Admin monitoring';
COMMENT ON TABLE permission_change_history IS 'History of permission status changes';
