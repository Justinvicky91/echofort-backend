-- Migration 015: YouTube Videos and Live Scam Alerts
-- Created: 2025-10-22
-- Purpose: Store YouTube demo videos and live scam alerts for homepage

-- YouTube Videos Table
CREATE TABLE IF NOT EXISTS youtube_videos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    video_id VARCHAR(50) NOT NULL UNIQUE,
    thumbnail_url TEXT,
    duration VARCHAR(20),
    category VARCHAR(50) DEFAULT 'demo',
    active BOOLEAN DEFAULT true,
    view_count INTEGER DEFAULT 0,
    rotation_priority INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Live Scam Alerts Table
CREATE TABLE IF NOT EXISTS scam_alerts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    amount VARCHAR(50),
    severity VARCHAR(20) DEFAULT 'medium',
    source VARCHAR(100),
    link TEXT,
    location VARCHAR(100),
    reported_at TIMESTAMP DEFAULT NOW(),
    active BOOLEAN DEFAULT true,
    verified BOOLEAN DEFAULT false,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default YouTube videos
INSERT INTO youtube_videos (title, description, video_id, category, rotation_priority) VALUES
('EchoFort Demo - AI Call Screening', 'See how EchoFort AI screens incoming calls in real-time', 'dQw4w9WgXcQ', 'demo', 1),
('Protect Your Family from Digital Arrest Scams', 'Learn about the latest digital arrest scam tactics', 'dQw4w9WgXcQ', 'education', 2),
('EchoFort GPS Tracking Feature', 'Keep your family safe with real-time location tracking', 'dQw4w9WgXcQ', 'feature', 3),
('How EchoFort Detects Scam Calls', 'Behind the scenes: Our AI scam detection technology', 'dQw4w9WgXcQ', 'tech', 4),
('Customer Success Story - Saved ₹5 Lakhs', 'Real customer shares how EchoFort saved them from fraud', 'dQw4w9WgXcQ', 'testimonial', 5)
ON CONFLICT (video_id) DO NOTHING;

-- Insert default scam alerts (from real news)
INSERT INTO scam_alerts (title, description, amount, severity, source, link, location) VALUES
('Digital Arrest Scam Alert', 'Mumbai cyber police arrest seven in ₹58 crore digital arrest fraud.', '₹58 Cr', 'critical', 'Times of India', 'https://timesofindia.indiatimes.com/city/mumbai/mumbai-cyber-police-arrest-seven-in-digital-arrest-scam-involving-rs-58cr-fraud/articleshow/124609701.cms', 'Mumbai'),
('Doctor Loses Money in Digital Arrest', 'Maharashtra doctor loses over ₹7 crore in digital arrest scam.', '₹7 Cr', 'high', 'NDTV', 'https://www.ndtv.com/india-news/maharashtra-doctor-loses-over-rs-7-crore-in-digital-arrest-scam-9460583', 'Maharashtra'),
('Online Trading Scam Busted', 'Man held for ₹3 crore online trading scam in Telangana.', '₹3 Cr', 'high', 'New Indian Express', 'https://www.newindianexpress.com/states/telangana/2025/Oct/20/man-held-for-rs-3-crore-online-trading-scam-in-telangana', 'Telangana'),
('Deep Fake Investment Scam', 'Four arrested in cyber frauds using deep fake of analysts.', 'Multiple victims', 'medium', 'Hindustan Times', 'https://www.hindustantimes.com/cities/mumbai-news/four-arrested-in-cyber-frauds-using-deep-fake-of-analysts-101760813870071.html', 'Mumbai'),
('Digital Diwali Scam Wave', 'Police issue urgent warning over Digital Diwali scam wave.', 'Widespread', 'high', 'BW Security World', 'https://bwsecurityworld.com/technology/police-issue-urgent-warning-over-digital-diwali-scam-wave/', 'India')
ON CONFLICT DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_youtube_videos_active ON youtube_videos(active);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_priority ON youtube_videos(rotation_priority);
CREATE INDEX IF NOT EXISTS idx_scam_alerts_active ON scam_alerts(active);
CREATE INDEX IF NOT EXISTS idx_scam_alerts_reported ON scam_alerts(reported_at DESC);
CREATE INDEX IF NOT EXISTS idx_scam_alerts_severity ON scam_alerts(severity);

-- Create view for latest scam alerts
CREATE OR REPLACE VIEW latest_scam_alerts AS
SELECT * FROM scam_alerts
WHERE active = true
ORDER BY reported_at DESC
LIMIT 10;

-- Create view for active videos
CREATE OR REPLACE VIEW active_videos AS
SELECT * FROM youtube_videos
WHERE active = true
ORDER BY rotation_priority ASC;

COMMENT ON TABLE youtube_videos IS 'Stores YouTube demo videos for homepage rotation (every 30 minutes)';
COMMENT ON TABLE scam_alerts IS 'Stores live scam alerts for homepage sidebar (updates every 12 hours)';

