-- Mobile SMS Scam Detection System
-- Real-time SMS scanning and threat detection

-- SMS Threats Database
CREATE TABLE IF NOT EXISTS sms_threats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sender VARCHAR(50) NOT NULL,
    message_text TEXT NOT NULL,
    received_at TIMESTAMP NOT NULL,
    is_scam BOOLEAN DEFAULT FALSE,
    scam_score INTEGER DEFAULT 0 CHECK (scam_score >= 0 AND scam_score <= 100),
    scam_type VARCHAR(100), -- phishing, financial, delivery, otp_theft, lottery, etc.
    indicators JSONB, -- Array of detected indicators
    action_taken VARCHAR(50), -- blocked, quarantined, allowed, reported
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sms_threats_user ON sms_threats(user_id);
CREATE INDEX IF NOT EXISTS idx_sms_threats_sender ON sms_threats(sender);
CREATE INDEX IF NOT EXISTS idx_sms_threats_date ON sms_threats(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_sms_threats_scam ON sms_threats(is_scam, scam_score DESC);

-- SMS Scam Reports (Community)
CREATE TABLE IF NOT EXISTS sms_scam_reports (
    id SERIAL PRIMARY KEY,
    sender VARCHAR(50) NOT NULL,
    message_text TEXT NOT NULL,
    reported_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    scam_type VARCHAR(100) NOT NULL,
    description TEXT,
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified BOOLEAN DEFAULT FALSE,
    verification_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sms_reports_sender ON sms_scam_reports(sender);
CREATE INDEX IF NOT EXISTS idx_sms_reports_user ON sms_scam_reports(reported_by);

-- SMS Scam Patterns (for detection)
CREATE TABLE IF NOT EXISTS sms_scam_patterns (
    id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(255) NOT NULL,
    scam_type VARCHAR(100) NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    country_code VARCHAR(5),
    keywords TEXT[], -- Array of keywords
    regex_patterns TEXT[], -- Array of regex patterns
    url_patterns TEXT[], -- Suspicious URL patterns
    sender_patterns TEXT[], -- Suspicious sender patterns
    confidence_weight FLOAT DEFAULT 1.0,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sms_patterns_type ON sms_scam_patterns(scam_type);
CREATE INDEX IF NOT EXISTS idx_sms_patterns_lang ON sms_scam_patterns(language);

-- SMS Statistics
CREATE TABLE IF NOT EXISTS sms_statistics (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    total_sms_scanned INTEGER DEFAULT 0,
    threats_detected INTEGER DEFAULT 0,
    threats_blocked INTEGER DEFAULT 0,
    reports_submitted INTEGER DEFAULT 0,
    last_scan_at TIMESTAMP,
    last_threat_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert common SMS scam patterns
INSERT INTO sms_scam_patterns (pattern_name, scam_type, language, country_code, keywords, regex_patterns, sender_patterns, confidence_weight) VALUES
-- Phishing patterns
('Bank OTP Phishing', 'phishing', 'en', 'IN', 
 ARRAY['OTP', 'verification', 'expire', 'update', 'blocked', 'suspended'],
 ARRAY['OTP.*\d{4,6}', 'verify.*account', 'click.*link'],
 ARRAY['%BANK%', '%PAY%'],
 0.9),

('Delivery Scam', 'delivery', 'en', 'IN',
 ARRAY['parcel', 'delivery', 'courier', 'pending', 'customs', 'fee'],
 ARRAY['parcel.*pending', 'delivery.*failed', 'customs.*fee'],
 ARRAY['%DELIVERY%', '%COURIER%'],
 0.85),

('KYC Update Scam', 'financial', 'en', 'IN',
 ARRAY['KYC', 'update', 'Aadhaar', 'PAN', 'blocked', 'expire'],
 ARRAY['KYC.*update', 'Aadhaar.*blocked', 'PAN.*expire'],
 ARRAY['%BANK%', '%KYC%'],
 0.9),

('Lottery/Prize Scam', 'lottery', 'en', 'IN',
 ARRAY['congratulations', 'won', 'prize', 'lottery', 'claim', 'winner'],
 ARRAY['won.*prize', 'lottery.*winner', 'claim.*reward'],
 ARRAY['%LOTTERY%', '%PRIZE%'],
 0.95),

('Loan Approval Scam', 'financial', 'en', 'IN',
 ARRAY['loan', 'approved', 'instant', 'credit', 'apply', 'eligible'],
 ARRAY['loan.*approved', 'instant.*credit', 'apply.*now'],
 ARRAY['%LOAN%', '%FINANCE%'],
 0.8),

-- Hindi patterns
('Digital Arrest Hindi', 'scam', 'hi', 'IN',
 ARRAY['पुलिस', 'गिरफ्तारी', 'वारंट', 'कोर्ट', 'केस'],
 ARRAY['डिजिटल.*गिरफ्तारी', 'वारंट.*जारी'],
 ARRAY[],
 0.95),

('KYC Scam Hindi', 'financial', 'hi', 'IN',
 ARRAY['केवाईसी', 'आधार', 'पैन', 'ब्लॉक', 'अपडेट'],
 ARRAY['केवाईसी.*अपडेट', 'आधार.*ब्लॉक'],
 ARRAY[],
 0.9),

-- International patterns
('IRS Tax Scam', 'tax_scam', 'en', 'US',
 ARRAY['IRS', 'tax', 'refund', 'owe', 'payment', 'lawsuit'],
 ARRAY['IRS.*refund', 'tax.*owe', 'lawsuit.*filed'],
 ARRAY['%IRS%', '%TAX%'],
 0.9),

('Social Security Scam', 'government', 'en', 'US',
 ARRAY['Social Security', 'SSN', 'suspended', 'verify', 'fraud'],
 ARRAY['Social Security.*suspended', 'SSN.*compromised'],
 ARRAY['%SSA%', '%SOCIAL%'],
 0.95),

('Parcel Scam UK', 'delivery', 'en', 'GB',
 ARRAY['Royal Mail', 'parcel', 'redelivery', 'fee', 'customs'],
 ARRAY['Royal Mail.*parcel', 'redelivery.*fee'],
 ARRAY['%ROYALMAIL%', '%PARCEL%'],
 0.85),

-- URL-based patterns
('Phishing URL', 'phishing', 'en', NULL,
 ARRAY['click', 'verify', 'update', 'confirm', 'login'],
 ARRAY['bit\.ly', 'tinyurl', 'goo\.gl', 'short\.link'],
 ARRAY[],
 0.8),

-- OTP theft patterns
('OTP Theft', 'otp_theft', 'en', 'IN',
 ARRAY['OTP', 'share', 'verify', 'code', 'PIN'],
 ARRAY['share.*OTP', 'send.*code', 'verify.*PIN'],
 ARRAY[],
 0.9)

ON CONFLICT DO NOTHING;

-- Function to calculate SMS scam score
CREATE OR REPLACE FUNCTION calculate_sms_scam_score(
    p_message TEXT,
    p_sender VARCHAR(50)
) RETURNS TABLE (
    scam_score INTEGER,
    scam_type VARCHAR(100),
    indicators JSONB
) AS $$
DECLARE
    v_score INTEGER := 0;
    v_type VARCHAR(100) := 'unknown';
    v_indicators JSONB := '[]'::JSONB;
    v_pattern RECORD;
    v_keyword TEXT;
    v_regex TEXT;
BEGIN
    -- Check against all active patterns
    FOR v_pattern IN 
        SELECT * FROM sms_scam_patterns WHERE active = TRUE
    LOOP
        -- Check keywords
        FOREACH v_keyword IN ARRAY v_pattern.keywords
        LOOP
            IF LOWER(p_message) LIKE '%' || LOWER(v_keyword) || '%' THEN
                v_score := v_score + (10 * v_pattern.confidence_weight)::INTEGER;
                v_indicators := v_indicators || jsonb_build_object(
                    'type', 'keyword',
                    'value', v_keyword,
                    'pattern', v_pattern.pattern_name
                );
            END IF;
        END LOOP;
        
        -- Check sender patterns
        IF v_pattern.sender_patterns IS NOT NULL THEN
            FOREACH v_regex IN ARRAY v_pattern.sender_patterns
            LOOP
                IF p_sender SIMILAR TO REPLACE(v_regex, '%', '.*') THEN
                    v_score := v_score + (15 * v_pattern.confidence_weight)::INTEGER;
                    v_indicators := v_indicators || jsonb_build_object(
                        'type', 'sender',
                        'value', p_sender,
                        'pattern', v_pattern.pattern_name
                    );
                END IF;
            END LOOP;
        END IF;
        
        -- If score increased, update type
        IF v_score > 0 AND v_type = 'unknown' THEN
            v_type := v_pattern.scam_type;
        END IF;
    END LOOP;
    
    -- Check for suspicious URLs
    IF p_message ~ 'https?://[^\s]+' THEN
        v_score := v_score + 10;
        v_indicators := v_indicators || jsonb_build_object(
            'type', 'url',
            'value', 'Contains URL',
            'pattern', 'URL Detection'
        );
    END IF;
    
    -- Cap score at 100
    v_score := LEAST(v_score, 100);
    
    RETURN QUERY SELECT v_score, v_type, v_indicators;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE sms_threats IS 'Detected SMS threats for users';
COMMENT ON TABLE sms_scam_reports IS 'Community-reported SMS scams';
COMMENT ON TABLE sms_scam_patterns IS 'SMS scam detection patterns';
COMMENT ON TABLE sms_statistics IS 'Per-user SMS protection statistics';
