-- Migration 053: Config Management System
-- Allows EchoFort AI to read and propose changes to platform configuration

CREATE TABLE IF NOT EXISTS app_config (
    id SERIAL PRIMARY KEY,
    scope VARCHAR(50) NOT NULL,  -- 'web', 'backend', 'mobile'
    key VARCHAR(255) NOT NULL,
    value_json JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(scope, key)
);

CREATE TABLE IF NOT EXISTS feature_flags (
    id SERIAL PRIMARY KEY,
    scope VARCHAR(50) NOT NULL,  -- 'web', 'backend', 'mobile'
    flag_name VARCHAR(255) NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT false,
    rollout_percent INTEGER DEFAULT 100 CHECK (rollout_percent >= 0 AND rollout_percent <= 100),
    notes TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(scope, flag_name)
);

CREATE TABLE IF NOT EXISTS config_change_log (
    id SERIAL PRIMARY KEY,
    scope VARCHAR(50) NOT NULL,
    key VARCHAR(255) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    changed_by INTEGER REFERENCES users(id),
    change_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_app_config_scope ON app_config(scope);
CREATE INDEX idx_feature_flags_scope ON feature_flags(scope);
CREATE INDEX idx_feature_flags_enabled ON feature_flags(is_enabled);
CREATE INDEX idx_config_change_log_created_at ON config_change_log(created_at DESC);

COMMENT ON TABLE app_config IS 'Platform configuration key-value store';
COMMENT ON TABLE feature_flags IS 'Feature flags for gradual rollouts';
COMMENT ON TABLE config_change_log IS 'Audit log for configuration changes';

-- Insert default config entries
INSERT INTO app_config (scope, key, value_json, description) VALUES
('web', 'hero_text', '{"title": "India''s Most Advanced AI-Powered Scam Protection", "subtitle": "Protect your family from scams, fraud, and online threats with real-time AI monitoring"}', 'Homepage hero section text'),
('web', 'features_enabled', '{"call_screening": true, "digital_arrest": true, "gps_tracking": true, "screen_time": true}', 'Feature visibility on website'),
('backend', 'risk_thresholds', '{"scam_score": 0.7, "harassment_score": 0.6, "extremism_score": 0.8}', 'AI risk detection thresholds'),
('mobile', 'safe_mode_default', '{"enabled": false, "teen_threshold": 0.5}', 'Safe mode configuration for mobile app')
ON CONFLICT (scope, key) DO NOTHING;

-- Insert default feature flags
INSERT INTO feature_flags (scope, flag_name, is_enabled, notes) VALUES
('web', 'show_pricing_page', true, 'Display pricing page on website'),
('web', 'show_download_page', true, 'Display download page on website'),
('backend', 'enable_threat_intel_scans', true, 'Enable 12-hour threat intelligence scans'),
('backend', 'enable_ai_investigation', true, 'Enable AI investigation features'),
('mobile', 'enable_call_recording', true, 'Enable call recording feature in mobile app'),
('mobile', 'enable_gps_tracking', true, 'Enable GPS family tracking in mobile app')
ON CONFLICT (scope, flag_name) DO NOTHING;
