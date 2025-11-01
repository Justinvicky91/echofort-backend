-- Mobile Caller ID Database System
-- Truecaller-like functionality for global caller identification

-- Caller ID Database
CREATE TABLE IF NOT EXISTS caller_id_database (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    country_code VARCHAR(5) NOT NULL,
    name VARCHAR(255),
    carrier VARCHAR(100),
    location VARCHAR(255),
    number_type VARCHAR(20), -- mobile, landline, voip, toll-free
    spam_score INTEGER DEFAULT 0 CHECK (spam_score >= 0 AND spam_score <= 100),
    total_reports INTEGER DEFAULT 0,
    spam_reports INTEGER DEFAULT 0,
    safe_reports INTEGER DEFAULT 0,
    business_name VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    tags TEXT[], -- Array of tags: spam, telemarketer, scam, safe, business, etc.
    first_reported_at TIMESTAMP,
    last_reported_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_caller_id_phone ON caller_id_database(phone_number);
CREATE INDEX IF NOT EXISTS idx_caller_id_country ON caller_id_database(country_code);
CREATE INDEX IF NOT EXISTS idx_caller_id_spam_score ON caller_id_database(spam_score DESC);

-- Spam Reports
CREATE TABLE IF NOT EXISTS caller_id_reports (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL,
    reported_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    report_type VARCHAR(50) NOT NULL, -- spam, scam, telemarketer, safe, wrong_number
    spam_category VARCHAR(100), -- loan_scam, tax_scam, tech_support, etc.
    description TEXT,
    confidence INTEGER CHECK (confidence >= 0 AND confidence <= 100),
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    device_info JSONB
);

CREATE INDEX IF NOT EXISTS idx_reports_phone ON caller_id_reports(phone_number);
CREATE INDEX IF NOT EXISTS idx_reports_user ON caller_id_reports(reported_by);
CREATE INDEX IF NOT EXISTS idx_reports_date ON caller_id_reports(reported_at DESC);

-- Blocked Numbers (User-specific)
CREATE TABLE IF NOT EXISTS blocked_numbers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    reason VARCHAR(255),
    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, phone_number)
);

CREATE INDEX IF NOT EXISTS idx_blocked_user ON blocked_numbers(user_id);
CREATE INDEX IF NOT EXISTS idx_blocked_phone ON blocked_numbers(phone_number);

-- Whitelisted Numbers (User-specific)
CREATE TABLE IF NOT EXISTS whitelisted_numbers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    name VARCHAR(255),
    whitelisted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, phone_number)
);

CREATE INDEX IF NOT EXISTS idx_whitelist_user ON whitelisted_numbers(user_id);

-- Call History (for spam detection patterns)
CREATE TABLE IF NOT EXISTS call_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    call_type VARCHAR(20) NOT NULL, -- incoming, outgoing, missed
    duration INTEGER, -- in seconds
    timestamp TIMESTAMP NOT NULL,
    was_blocked BOOLEAN DEFAULT FALSE,
    spam_score INTEGER,
    caller_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_call_history_user ON call_history(user_id);
CREATE INDEX IF NOT EXISTS idx_call_history_phone ON call_history(phone_number);
CREATE INDEX IF NOT EXISTS idx_call_history_timestamp ON call_history(timestamp DESC);

-- Global Scam Patterns (for AI detection)
CREATE TABLE IF NOT EXISTS scam_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(100) NOT NULL,
    language VARCHAR(10) NOT NULL,
    country_code VARCHAR(5),
    keywords TEXT[],
    phrases TEXT[],
    indicators JSONB,
    confidence_weight FLOAT DEFAULT 1.0,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scam_patterns_type ON scam_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_scam_patterns_lang ON scam_patterns(language);
CREATE INDEX IF NOT EXISTS idx_scam_patterns_country ON scam_patterns(country_code);

-- Community Trust Scores
CREATE TABLE IF NOT EXISTS user_trust_scores (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    reports_submitted INTEGER DEFAULT 0,
    reports_verified INTEGER DEFAULT 0,
    reports_rejected INTEGER DEFAULT 0,
    trust_score INTEGER DEFAULT 50 CHECK (trust_score >= 0 AND trust_score <= 100),
    reputation_level VARCHAR(20) DEFAULT 'new', -- new, trusted, expert, moderator
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Function to update spam score based on reports
CREATE OR REPLACE FUNCTION update_caller_spam_score()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE caller_id_database
    SET 
        total_reports = (SELECT COUNT(*) FROM caller_id_reports WHERE phone_number = NEW.phone_number),
        spam_reports = (SELECT COUNT(*) FROM caller_id_reports WHERE phone_number = NEW.phone_number AND report_type IN ('spam', 'scam', 'telemarketer')),
        safe_reports = (SELECT COUNT(*) FROM caller_id_reports WHERE phone_number = NEW.phone_number AND report_type = 'safe'),
        spam_score = LEAST(100, GREATEST(0, 
            (SELECT COUNT(*) FROM caller_id_reports WHERE phone_number = NEW.phone_number AND report_type IN ('spam', 'scam', 'telemarketer')) * 10 -
            (SELECT COUNT(*) FROM caller_id_reports WHERE phone_number = NEW.phone_number AND report_type = 'safe') * 5
        )),
        last_reported_at = NEW.reported_at,
        updated_at = CURRENT_TIMESTAMP
    WHERE phone_number = NEW.phone_number;
    
    -- Create entry if doesn't exist
    IF NOT FOUND THEN
        INSERT INTO caller_id_database (phone_number, country_code, spam_score, total_reports, spam_reports, first_reported_at, last_reported_at)
        VALUES (
            NEW.phone_number,
            SUBSTRING(NEW.phone_number FROM 1 FOR 3),
            CASE WHEN NEW.report_type IN ('spam', 'scam', 'telemarketer') THEN 10 ELSE 0 END,
            1,
            CASE WHEN NEW.report_type IN ('spam', 'scam', 'telemarketer') THEN 1 ELSE 0 END,
            NEW.reported_at,
            NEW.reported_at
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update spam scores
DROP TRIGGER IF EXISTS trigger_update_spam_score ON caller_id_reports;
CREATE TRIGGER trigger_update_spam_score
    AFTER INSERT ON caller_id_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_caller_spam_score();

-- Insert some sample global scam patterns
INSERT INTO scam_patterns (pattern_type, language, country_code, keywords, phrases, confidence_weight) VALUES
('tax_scam', 'en', 'US', ARRAY['IRS', 'tax', 'lawsuit', 'arrest warrant', 'owe'], ARRAY['IRS has filed a lawsuit', 'tax fraud case', 'arrest warrant issued'], 0.9),
('tax_scam', 'en', 'IN', ARRAY['income tax', 'refund', 'verification', 'PAN', 'Aadhaar'], ARRAY['tax refund pending', 'verify your PAN', 'Aadhaar blocked'], 0.9),
('bank_scam', 'en', 'US', ARRAY['bank', 'account', 'suspended', 'verify', 'fraud'], ARRAY['account has been suspended', 'unusual activity', 'verify your identity'], 0.85),
('tech_support', 'en', 'US', ARRAY['Microsoft', 'Windows', 'virus', 'computer', 'tech support'], ARRAY['your computer has a virus', 'Microsoft tech support', 'Windows license expired'], 0.9),
('digital_arrest', 'hi', 'IN', ARRAY['पुलिस', 'गिरफ्तारी', 'वारंट', 'कोर्ट'], ARRAY['डिजिटल गिरफ्तारी', 'गिरफ्तारी वारंट जारी'], 0.95),
('loan_scam', 'en', 'IN', ARRAY['loan', 'approved', 'instant', 'credit'], ARRAY['loan approved instantly', 'no documents required'], 0.8),
('parcel_scam', 'en', 'GB', ARRAY['parcel', 'delivery', 'Royal Mail', 'customs'], ARRAY['parcel awaiting delivery', 'customs fee required'], 0.85)
ON CONFLICT DO NOTHING;

COMMENT ON TABLE caller_id_database IS 'Global caller ID database with spam scores';
COMMENT ON TABLE caller_id_reports IS 'User-submitted spam reports for phone numbers';
COMMENT ON TABLE blocked_numbers IS 'User-specific blocked phone numbers';
COMMENT ON TABLE whitelisted_numbers IS 'User-specific trusted phone numbers';
COMMENT ON TABLE call_history IS 'User call history for pattern detection';
COMMENT ON TABLE scam_patterns IS 'Global scam detection patterns by language and country';
