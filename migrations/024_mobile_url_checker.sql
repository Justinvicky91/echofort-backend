-- Mobile Website/URL Checker System
-- ScamAdviser-like functionality for URL and email verification

-- URL Check Results
CREATE TABLE IF NOT EXISTS url_check_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    url TEXT NOT NULL,
    domain VARCHAR(255) NOT NULL,
    trust_score INTEGER DEFAULT 50 CHECK (trust_score >= 0 AND trust_score <= 100),
    is_phishing BOOLEAN DEFAULT FALSE,
    is_malware BOOLEAN DEFAULT FALSE,
    is_scam BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(20), -- safe, low, medium, high, critical
    risk_factors JSONB,
    domain_age_days INTEGER,
    ssl_valid BOOLEAN,
    ssl_issuer VARCHAR(255),
    whois_data JSONB,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_url_checks_user ON url_check_results(user_id);
CREATE INDEX IF NOT EXISTS idx_url_checks_domain ON url_check_results(domain);
CREATE INDEX IF NOT EXISTS idx_url_checks_date ON url_check_results(checked_at DESC);

-- Email Verification Results
CREATE TABLE IF NOT EXISTS email_check_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    email VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    is_valid BOOLEAN DEFAULT TRUE,
    is_disposable BOOLEAN DEFAULT FALSE,
    is_role_based BOOLEAN DEFAULT FALSE,
    risk_score INTEGER DEFAULT 0 CHECK (risk_score >= 0 AND risk_score <= 100),
    mx_records_valid BOOLEAN,
    smtp_valid BOOLEAN,
    reputation_score INTEGER,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_checks_user ON email_check_results(user_id);
CREATE INDEX IF NOT EXISTS idx_email_checks_email ON email_check_results(email);

-- Known Phishing Domains
CREATE TABLE IF NOT EXISTS phishing_domains (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) NOT NULL UNIQUE,
    reported_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    phishing_type VARCHAR(100), -- banking, ecommerce, social_media, etc.
    target_brand VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active', -- active, taken_down, disputed
    verified BOOLEAN DEFAULT FALSE,
    report_count INTEGER DEFAULT 1,
    first_reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    takedown_requested_at TIMESTAMP,
    taken_down_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_phishing_domains_domain ON phishing_domains(domain);
CREATE INDEX IF NOT EXISTS idx_phishing_domains_status ON phishing_domains(status);

-- Malicious URL Patterns
CREATE TABLE IF NOT EXISTS malicious_url_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(100) NOT NULL,
    pattern_regex TEXT NOT NULL,
    description TEXT,
    severity VARCHAR(20), -- low, medium, high, critical
    confidence_weight FLOAT DEFAULT 1.0,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Disposable Email Domains
CREATE TABLE IF NOT EXISTS disposable_email_domains (
    domain VARCHAR(255) PRIMARY KEY,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- URL/Email Check Statistics
CREATE TABLE IF NOT EXISTS url_check_statistics (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    urls_checked INTEGER DEFAULT 0,
    phishing_detected INTEGER DEFAULT 0,
    emails_verified INTEGER DEFAULT 0,
    disposable_emails_found INTEGER DEFAULT 0,
    last_check_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert common malicious URL patterns
INSERT INTO malicious_url_patterns (pattern_type, pattern_regex, description, severity, confidence_weight) VALUES
('Suspicious TLD', '.*\.(tk|ml|ga|cf|gq)$', 'Free TLD often used for phishing', 'medium', 0.7),
('IP Address URL', '^https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'Direct IP address instead of domain', 'high', 0.8),
('Suspicious Port', '.*:\d{4,5}(/|$)', 'Non-standard port usage', 'medium', 0.6),
('URL Shortener', '.*(bit\.ly|tinyurl|goo\.gl|short\.link|t\.co).*', 'URL shortener (potential hiding)', 'low', 0.4),
('Homograph Attack', '.*[а-яА-Я].*', 'Cyrillic characters in domain', 'high', 0.9),
('Excessive Subdomains', '^[^/]*\..*\..*\..*\.', 'Too many subdomains', 'medium', 0.7),
('Suspicious Keywords', '.*(verify|secure|account|update|confirm|login|signin).*', 'Phishing keywords in URL', 'medium', 0.6),
('Misspelled Brands', '.*(paypa1|amaz0n|g00gle|micros0ft|app1e).*', 'Common brand misspellings', 'high', 0.9)
ON CONFLICT DO NOTHING;

-- Insert common disposable email domains
INSERT INTO disposable_email_domains (domain) VALUES
('tempmail.com'), ('guerrillamail.com'), ('10minutemail.com'), ('throwaway.email'),
('mailinator.com'), ('maildrop.cc'), ('temp-mail.org'), ('getnada.com'),
('trashmail.com'), ('yopmail.com'), ('fakeinbox.com'), ('sharklasers.com')
ON CONFLICT DO NOTHING;

-- Function to calculate URL trust score
CREATE OR REPLACE FUNCTION calculate_url_trust_score(
    p_url TEXT,
    p_domain VARCHAR(255)
) RETURNS TABLE (
    trust_score INTEGER,
    risk_level VARCHAR(20),
    risk_factors JSONB
) AS $$
DECLARE
    v_score INTEGER := 100;
    v_risk_level VARCHAR(20) := 'safe';
    v_factors JSONB := '[]'::JSONB;
    v_pattern RECORD;
BEGIN
    -- Check against malicious patterns
    FOR v_pattern IN 
        SELECT * FROM malicious_url_patterns WHERE active = TRUE
    LOOP
        IF p_url ~ v_pattern.pattern_regex THEN
            v_score := v_score - (20 * v_pattern.confidence_weight)::INTEGER;
            v_factors := v_factors || jsonb_build_object(
                'type', v_pattern.pattern_type,
                'severity', v_pattern.severity,
                'description', v_pattern.description
            );
        END IF;
    END LOOP;
    
    -- Check if domain is in phishing database
    IF EXISTS (SELECT 1 FROM phishing_domains WHERE domain = p_domain AND status = 'active') THEN
        v_score := 0;
        v_factors := v_factors || jsonb_build_object(
            'type', 'Known Phishing Domain',
            'severity', 'critical',
            'description', 'This domain is reported as phishing'
        );
    END IF;
    
    -- Check for HTTPS
    IF p_url !~ '^https://' THEN
        v_score := v_score - 10;
        v_factors := v_factors || jsonb_build_object(
            'type', 'No HTTPS',
            'severity', 'low',
            'description', 'Website does not use secure connection'
        );
    END IF;
    
    -- Ensure score is within bounds
    v_score := GREATEST(0, LEAST(100, v_score));
    
    -- Determine risk level
    IF v_score >= 80 THEN
        v_risk_level := 'safe';
    ELSIF v_score >= 60 THEN
        v_risk_level := 'low';
    ELSIF v_score >= 40 THEN
        v_risk_level := 'medium';
    ELSIF v_score >= 20 THEN
        v_risk_level := 'high';
    ELSE
        v_risk_level := 'critical';
    END IF;
    
    RETURN QUERY SELECT v_score, v_risk_level, v_factors;
END;
$$ LANGUAGE plpgsql;

-- Function to check if email is disposable
CREATE OR REPLACE FUNCTION is_disposable_email(p_email VARCHAR(255))
RETURNS BOOLEAN AS $$
DECLARE
    v_domain VARCHAR(255);
BEGIN
    v_domain := SPLIT_PART(p_email, '@', 2);
    RETURN EXISTS (SELECT 1 FROM disposable_email_domains WHERE domain = v_domain);
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE url_check_results IS 'URL safety check results';
COMMENT ON TABLE email_check_results IS 'Email verification results';
COMMENT ON TABLE phishing_domains IS 'Known phishing domains database';
COMMENT ON TABLE malicious_url_patterns IS 'Patterns for detecting malicious URLs';
COMMENT ON TABLE disposable_email_domains IS 'List of disposable email domains';
