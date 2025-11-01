-- Real-Time Call Analysis System
-- AI-powered real-time call monitoring and scam detection

-- Real-Time Call Sessions
CREATE TABLE IF NOT EXISTS realtime_call_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    caller_name VARCHAR(255),
    call_direction VARCHAR(10) NOT NULL, -- incoming, outgoing
    call_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    call_ended_at TIMESTAMP,
    call_duration_seconds INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    was_recorded BOOLEAN DEFAULT FALSE,
    recording_url TEXT,
    analysis_status VARCHAR(20) DEFAULT 'pending', -- pending, analyzing, completed, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rtc_sessions_user ON realtime_call_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_rtc_sessions_active ON realtime_call_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_rtc_sessions_started ON realtime_call_sessions(call_started_at DESC);

-- Real-Time Call Analysis Results
CREATE TABLE IF NOT EXISTS realtime_call_analysis (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES realtime_call_sessions(id) ON DELETE CASCADE,
    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scam_probability DECIMAL(5, 2) CHECK (scam_probability >= 0 AND scam_probability <= 100),
    threat_level VARCHAR(20), -- none, low, medium, high, critical
    detected_patterns JSONB, -- Array of detected scam patterns
    keywords_detected JSONB, -- Suspicious keywords found
    voice_analysis JSONB, -- Voice characteristics analysis
    sentiment_score DECIMAL(5, 2), -- -100 to 100
    confidence_score DECIMAL(5, 2), -- 0 to 100
    recommended_action VARCHAR(50), -- continue, warn, block, record
    ai_explanation TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_rtc_analysis_session ON realtime_call_analysis(session_id);
CREATE INDEX IF NOT EXISTS idx_rtc_analysis_timestamp ON realtime_call_analysis(analysis_timestamp DESC);

-- Call Transcription (Real-time)
CREATE TABLE IF NOT EXISTS realtime_call_transcription (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES realtime_call_sessions(id) ON DELETE CASCADE,
    speaker VARCHAR(20) NOT NULL, -- user, caller
    text TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    confidence DECIMAL(5, 2),
    timestamp_offset INTEGER, -- Milliseconds from call start
    is_suspicious BOOLEAN DEFAULT FALSE,
    flagged_keywords JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rtc_transcription_session ON realtime_call_transcription(session_id);
CREATE INDEX IF NOT EXISTS idx_rtc_transcription_suspicious ON realtime_call_transcription(is_suspicious);

-- Call Alerts (Real-time warnings during call)
CREATE TABLE IF NOT EXISTS realtime_call_alerts (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES realtime_call_sessions(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL, -- scam_detected, suspicious_keyword, voice_anomaly, etc.
    severity VARCHAR(20) NOT NULL, -- low, medium, high, critical
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    recommended_action VARCHAR(50),
    was_shown BOOLEAN DEFAULT FALSE,
    user_response VARCHAR(50), -- dismissed, blocked_call, reported, etc.
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rtc_alerts_session ON realtime_call_alerts(session_id);
CREATE INDEX IF NOT EXISTS idx_rtc_alerts_severity ON realtime_call_alerts(severity);

-- Scam Pattern Library
CREATE TABLE IF NOT EXISTS scam_pattern_library (
    id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(255) NOT NULL UNIQUE,
    pattern_type VARCHAR(50) NOT NULL, -- keyword, phrase, voice_pattern, behavior
    pattern_data JSONB NOT NULL,
    languages JSONB, -- Array of language codes
    severity VARCHAR(20) DEFAULT 'medium',
    confidence_weight DECIMAL(5, 2) DEFAULT 50.0,
    description TEXT,
    examples JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    detection_count INTEGER DEFAULT 0,
    accuracy_rate DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scam_patterns_type ON scam_pattern_library(pattern_type);
CREATE INDEX IF NOT EXISTS idx_scam_patterns_active ON scam_pattern_library(is_active);

-- Voice Biometric Profiles (for caller identification)
CREATE TABLE IF NOT EXISTS voice_biometric_profiles (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    voice_signature JSONB NOT NULL, -- Voice characteristics fingerprint
    known_scammer BOOLEAN DEFAULT FALSE,
    trust_score INTEGER DEFAULT 50 CHECK (trust_score >= 0 AND trust_score <= 100),
    call_count INTEGER DEFAULT 1,
    scam_reports INTEGER DEFAULT 0,
    last_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_voice_profiles_phone ON voice_biometric_profiles(phone_number);
CREATE INDEX IF NOT EXISTS idx_voice_profiles_scammer ON voice_biometric_profiles(known_scammer);

-- Call Analysis Statistics
CREATE TABLE IF NOT EXISTS call_analysis_statistics (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    total_calls_analyzed INTEGER DEFAULT 0,
    total_scams_detected INTEGER DEFAULT 0,
    total_warnings_shown INTEGER DEFAULT 0,
    total_calls_blocked INTEGER DEFAULT 0,
    average_scam_probability DECIMAL(5, 2),
    highest_threat_level VARCHAR(20),
    last_analysis_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default scam patterns
INSERT INTO scam_pattern_library (pattern_name, pattern_type, pattern_data, languages, severity, description) VALUES
('tax_authority_impersonation', 'keyword', '{"keywords": ["IRS", "tax authority", "tax department", "outstanding tax", "tax fraud", "arrest warrant", "tax evasion"]}', '["en"]', 'high', 'Impersonating tax authorities'),
('social_security_scam', 'keyword', '{"keywords": ["social security", "SSN suspended", "social security number", "benefits suspended"]}', '["en"]', 'high', 'Social Security scam patterns'),
('tech_support_scam', 'keyword', '{"keywords": ["computer virus", "windows support", "microsoft support", "apple support", "refund", "subscription"]}', '["en"]', 'medium', 'Tech support scam indicators'),
('bank_fraud', 'keyword', '{"keywords": ["bank account", "suspicious activity", "verify account", "card blocked", "unauthorized transaction"]}', '["en"]', 'high', 'Banking fraud patterns'),
('lottery_prize', 'keyword', '{"keywords": ["won lottery", "prize money", "claim prize", "lucky winner", "congratulations you won"]}', '["en"]', 'medium', 'Lottery/prize scam'),
('urgency_pressure', 'phrase', '{"phrases": ["act now", "limited time", "urgent action required", "within 24 hours", "immediately", "right now"]}', '["en"]', 'medium', 'Urgency and pressure tactics'),
('payment_request', 'phrase', '{"phrases": ["send money", "wire transfer", "gift card", "bitcoin", "cryptocurrency", "western union", "moneygram"]}', '["en"]', 'high', 'Payment request indicators'),
('personal_info_request', 'phrase', '{"phrases": ["social security number", "date of birth", "bank account number", "credit card", "PIN", "password", "OTP"]}', '["en"]', 'critical', 'Personal information phishing'),
('indian_tax_scam', 'keyword', '{"keywords": ["income tax", "GST", "PAN card", "Aadhaar", "tax refund", "IT department"]}', '["hi", "en"]', 'high', 'Indian tax authority scams'),
('digital_arrest', 'keyword', '{"keywords": ["digital arrest", "cyber crime", "police", "CBI", "ED", "court order", "legal notice"]}', '["hi", "en"]', 'critical', 'Digital arrest scam patterns')
ON CONFLICT (pattern_name) DO NOTHING;

-- Function to analyze call in real-time
CREATE OR REPLACE FUNCTION analyze_call_realtime(
    p_session_id INTEGER,
    p_transcription_text TEXT,
    p_speaker VARCHAR(20)
) RETURNS JSONB AS $$
DECLARE
    v_scam_probability DECIMAL(5, 2) := 0;
    v_threat_level VARCHAR(20) := 'none';
    v_detected_patterns JSONB := '[]'::jsonb;
    v_keywords_detected JSONB := '[]'::jsonb;
    v_pattern RECORD;
    v_keyword TEXT;
    v_pattern_match BOOLEAN;
BEGIN
    -- Check against scam patterns
    FOR v_pattern IN 
        SELECT * FROM scam_pattern_library WHERE is_active = TRUE
    LOOP
        v_pattern_match := FALSE;
        
        -- Check keywords
        IF v_pattern.pattern_type = 'keyword' THEN
            FOR v_keyword IN SELECT jsonb_array_elements_text(v_pattern.pattern_data->'keywords')
            LOOP
                IF LOWER(p_transcription_text) LIKE '%' || LOWER(v_keyword) || '%' THEN
                    v_pattern_match := TRUE;
                    v_keywords_detected := v_keywords_detected || jsonb_build_object('keyword', v_keyword, 'pattern', v_pattern.pattern_name);
                END IF;
            END LOOP;
        END IF;
        
        -- Check phrases
        IF v_pattern.pattern_type = 'phrase' THEN
            FOR v_keyword IN SELECT jsonb_array_elements_text(v_pattern.pattern_data->'phrases')
            LOOP
                IF LOWER(p_transcription_text) LIKE '%' || LOWER(v_keyword) || '%' THEN
                    v_pattern_match := TRUE;
                    v_keywords_detected := v_keywords_detected || jsonb_build_object('phrase', v_keyword, 'pattern', v_pattern.pattern_name);
                END IF;
            END LOOP;
        END IF;
        
        -- If pattern matched, add to detected patterns and increase scam probability
        IF v_pattern_match THEN
            v_detected_patterns := v_detected_patterns || jsonb_build_object(
                'patternName', v_pattern.pattern_name,
                'severity', v_pattern.severity,
                'weight', v_pattern.confidence_weight
            );
            v_scam_probability := v_scam_probability + v_pattern.confidence_weight;
            
            -- Update detection count
            UPDATE scam_pattern_library 
            SET detection_count = detection_count + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = v_pattern.id;
        END IF;
    END LOOP;
    
    -- Cap scam probability at 100
    IF v_scam_probability > 100 THEN
        v_scam_probability := 100;
    END IF;
    
    -- Determine threat level
    IF v_scam_probability >= 80 THEN
        v_threat_level := 'critical';
    ELSIF v_scam_probability >= 60 THEN
        v_threat_level := 'high';
    ELSIF v_scam_probability >= 40 THEN
        v_threat_level := 'medium';
    ELSIF v_scam_probability >= 20 THEN
        v_threat_level := 'low';
    ELSE
        v_threat_level := 'none';
    END IF;
    
    -- Insert analysis result
    INSERT INTO realtime_call_analysis 
    (session_id, scam_probability, threat_level, detected_patterns, keywords_detected, confidence_score)
    VALUES (p_session_id, v_scam_probability, v_threat_level, v_detected_patterns, v_keywords_detected, 85.0);
    
    -- Create alert if threat level is medium or higher
    IF v_threat_level IN ('medium', 'high', 'critical') THEN
        INSERT INTO realtime_call_alerts 
        (session_id, alert_type, severity, title, message, recommended_action)
        VALUES (
            p_session_id,
            'scam_detected',
            v_threat_level,
            'Potential Scam Detected',
            'This call shows signs of a scam. Be cautious and do not share personal information.',
            CASE 
                WHEN v_threat_level = 'critical' THEN 'block_call'
                WHEN v_threat_level = 'high' THEN 'warn_user'
                ELSE 'monitor'
            END
        );
    END IF;
    
    RETURN jsonb_build_object(
        'scamProbability', v_scam_probability,
        'threatLevel', v_threat_level,
        'detectedPatterns', v_detected_patterns,
        'keywordsDetected', v_keywords_detected
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE realtime_call_sessions IS 'Active and historical call sessions';
COMMENT ON TABLE realtime_call_analysis IS 'AI analysis results for calls';
COMMENT ON TABLE realtime_call_transcription IS 'Real-time call transcription';
COMMENT ON TABLE realtime_call_alerts IS 'Real-time alerts shown during calls';
COMMENT ON TABLE scam_pattern_library IS 'Library of scam detection patterns';
COMMENT ON TABLE voice_biometric_profiles IS 'Voice fingerprints for caller identification';
COMMENT ON TABLE call_analysis_statistics IS 'User call analysis statistics';
