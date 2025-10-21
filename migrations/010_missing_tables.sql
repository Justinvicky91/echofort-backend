-- Migration 010: Missing Critical Tables
-- Created: October 21, 2025
-- Purpose: Add tables referenced in code but not created in previous migrations

-- 1. Subscriptions Table (referenced in ai_assistant.py, subscription.py)
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(20) NOT NULL CHECK (plan IN ('basic', 'personal', 'family')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired', 'trial')),
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ends_at TIMESTAMP,
    trial_ends_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT TRUE,
    payment_method VARCHAR(50),
    razorpay_subscription_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, plan)
);

-- 2. Digital Arrest Alerts Table (referenced in digital_arrest.py)
CREATE TABLE IF NOT EXISTS digital_arrest_alerts (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    caller_claimed_identity VARCHAR(100),
    keywords_detected TEXT[],
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0 AND 1),
    is_scam BOOLEAN DEFAULT FALSE,
    action_taken VARCHAR(20) CHECK (action_taken IN ('blocked', 'warned', 'monitored', 'recorded')),
    detected_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Call Recordings Table (referenced in call_recordings.py)
CREATE TABLE IF NOT EXISTS call_recordings (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    caller_name VARCHAR(100),
    duration INTEGER, -- in seconds
    recording_url TEXT,
    trust_factor INTEGER CHECK (trust_factor BETWEEN 0 AND 10),
    scam_type VARCHAR(50),
    is_scam BOOLEAN DEFAULT FALSE,
    is_harassment BOOLEAN DEFAULT FALSE,
    is_threatening BOOLEAN DEFAULT FALSE,
    recorded_at TIMESTAMP DEFAULT NOW(),
    plan_type VARCHAR(20) CHECK (plan_type IN ('basic', 'personal', 'family')),
    storage_expires_at TIMESTAMP, -- 90 days retention
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. Scam Cases Table (referenced in scam_cases.py)
CREATE TABLE IF NOT EXISTS scam_cases (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    amount_lost DECIMAL(15,2),
    scam_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    location VARCHAR(100),
    reported_at TIMESTAMP DEFAULT NOW(),
    source_url TEXT,
    source_name VARCHAR(100),
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. User Scam Reports Table (referenced in scam_cases.py)
CREATE TABLE IF NOT EXISTS user_scam_reports (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    scam_type VARCHAR(50) NOT NULL,
    amount_lost DECIMAL(15,2),
    description TEXT NOT NULL,
    evidence_urls TEXT[],
    reported_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'rejected')),
    admin_notes TEXT,
    verified_by BIGINT REFERENCES employees(id),
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6. Auto Alerts Table (for auto_alert.py - to be created)
CREATE TABLE IF NOT EXISTS auto_alerts (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL CHECK (alert_type IN ('bank', 'police', 'cybercrime', 'rbi', 'consumer_forum')),
    scam_incident_id BIGINT,
    recipient_email VARCHAR(255),
    recipient_name VARCHAR(100),
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'failed')),
    user_confirmed BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 7. KYC Verifications Table (for kyc_verification.py - to be created)
CREATE TABLE IF NOT EXISTS kyc_verifications (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    id_type VARCHAR(50) NOT NULL CHECK (id_type IN ('aadhaar', 'pan', 'passport', 'driving_license', 'voter_id')),
    id_number VARCHAR(50) NOT NULL,
    id_proof_url TEXT,
    verification_status VARCHAR(20) DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'rejected', 'expired')),
    verified_by BIGINT REFERENCES employees(id),
    verified_at TIMESTAMP,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 8. Live Scam Alerts Table (for WebSocket live updates)
CREATE TABLE IF NOT EXISTS live_scam_alerts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    scam_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    amount_involved DECIMAL(15,2),
    location VARCHAR(100),
    source_url TEXT,
    source_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    published_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 9. Voice Biometrics Table (for voice authentication)
CREATE TABLE IF NOT EXISTS voice_biometrics (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    voice_signature BYTEA NOT NULL, -- Encrypted voice fingerprint
    enrollment_audio_url TEXT,
    enrollment_date TIMESTAMP DEFAULT NOW(),
    last_verified_at TIMESTAMP,
    verification_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 10. Scam Predictions Table (ML-based scam prediction)
CREATE TABLE IF NOT EXISTS scam_predictions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    prediction_score DECIMAL(3,2) CHECK (prediction_score BETWEEN 0 AND 1),
    scam_type_predicted VARCHAR(50),
    confidence_level VARCHAR(20) CHECK (confidence_level IN ('very_high', 'high', 'medium', 'low')),
    features_analyzed JSONB, -- Store ML features
    model_version VARCHAR(20),
    is_correct BOOLEAN, -- Feedback for model improvement
    predicted_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 11. Community Reports Table (user-generated scam reports)
CREATE TABLE IF NOT EXISTS community_reports (
    id SERIAL PRIMARY KEY,
    reporter_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    phone_number VARCHAR(20) NOT NULL,
    report_type VARCHAR(50) NOT NULL CHECK (report_type IN ('scam_call', 'scam_sms', 'phishing', 'fraud', 'harassment')),
    description TEXT NOT NULL,
    evidence_urls TEXT[],
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    verified_by BIGINT REFERENCES employees(id),
    verified_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'rejected', 'spam')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 12. Scam Map Data Table (geographic scam visualization)
CREATE TABLE IF NOT EXISTS scam_map_data (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    scam_type VARCHAR(50) NOT NULL,
    incident_count INTEGER DEFAULT 1,
    total_amount_lost DECIMAL(15,2),
    severity VARCHAR(20) CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    last_incident_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_digital_arrest_user_id ON digital_arrest_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_digital_arrest_detected_at ON digital_arrest_alerts(detected_at);
CREATE INDEX IF NOT EXISTS idx_call_recordings_user_id ON call_recordings(user_id);
CREATE INDEX IF NOT EXISTS idx_call_recordings_recorded_at ON call_recordings(recorded_at);
CREATE INDEX IF NOT EXISTS idx_scam_cases_scam_type ON scam_cases(scam_type);
CREATE INDEX IF NOT EXISTS idx_scam_cases_severity ON scam_cases(severity);
CREATE INDEX IF NOT EXISTS idx_user_scam_reports_user_id ON user_scam_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_user_scam_reports_status ON user_scam_reports(status);
CREATE INDEX IF NOT EXISTS idx_auto_alerts_user_id ON auto_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_verifications_user_id ON kyc_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_verifications_status ON kyc_verifications(verification_status);
CREATE INDEX IF NOT EXISTS idx_live_scam_alerts_active ON live_scam_alerts(is_active);
CREATE INDEX IF NOT EXISTS idx_voice_biometrics_user_id ON voice_biometrics(user_id);
CREATE INDEX IF NOT EXISTS idx_scam_predictions_phone ON scam_predictions(phone_number);
CREATE INDEX IF NOT EXISTS idx_community_reports_phone ON community_reports(phone_number);
CREATE INDEX IF NOT EXISTS idx_community_reports_status ON community_reports(status);
CREATE INDEX IF NOT EXISTS idx_scam_map_location ON scam_map_data(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_scam_map_scam_type ON scam_map_data(scam_type);

