-- migrations/006_refresh_scam_timestamps.sql
-- Fix scam timestamps to show in dashboard (discovered in last 7 days)
-- Created: Oct 19, 2025 - 11:53 PM IST

-- ============================================================================
-- REFRESH SCAM DATA WITH CURRENT TIMESTAMPS
-- ============================================================================

-- Delete existing scam data (to ensure fresh timestamps)
DELETE FROM scam_intelligence;

-- Re-insert sample scam data with CURRENT_TIMESTAMP
-- This ensures scams show up in dashboard queries that filter by discovered_at
INSERT INTO scam_intelligence 
    (scam_type, description, severity, defense_method, source, discovered_at, last_seen)
VALUES 
    (
        'AI Voice Clone Scam',
        'Scammers use AI to clone family member voices and request emergency money transfers',
        'critical',
        'Always verify by calling back on a known number. Use a family code word that only real family members know.',
        'cybercrime.gov.in',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ),
    (
        'UPI Refund Scam',
        'Fake customer service representatives asking for UPI PIN to process refunds',
        'high',
        'Never share your UPI PIN with anyone. Banks and payment apps never ask for PIN.',
        'rbi.org.in',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ),
    (
        'Deepfake Video Call Scam',
        'Video calls using deepfake technology to impersonate CEO or family members requesting money',
        'critical',
        'Ask questions that only the real person would know. Verify through another communication channel.',
        'fbi.gov',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    );

-- Verify scams were inserted
SELECT 
    scam_type,
    severity,
    discovered_at,
    last_seen
FROM scam_intelligence
ORDER BY 
    CASE severity 
        WHEN 'critical' THEN 1 
        WHEN 'high' THEN 2 
        ELSE 3 
    END,
    discovered_at DESC;

-- Confirm count
SELECT COUNT(*) as total_scams FROM scam_intelligence;
