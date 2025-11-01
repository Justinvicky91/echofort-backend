-- Answer Bots System (RoboKiller-like)
-- Automated call answering and scammer engagement

-- Answer Bot Types
CREATE TABLE IF NOT EXISTS answer_bot_types (
    id SERIAL PRIMARY KEY,
    bot_name VARCHAR(100) NOT NULL UNIQUE,
    bot_type VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Answer Bot Sessions
CREATE TABLE IF NOT EXISTS answer_bot_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bot_type_id INTEGER REFERENCES answer_bot_types(id),
    phone_number VARCHAR(20) NOT NULL,
    session_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_ended_at TIMESTAMP,
    session_duration_seconds INTEGER,
    recording_url TEXT,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE INDEX IF NOT EXISTS idx_bot_sessions_user ON answer_bot_sessions(user_id);

-- Answer Bot Settings
CREATE TABLE IF NOT EXISTS answer_bot_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    auto_answer_enabled BOOLEAN DEFAULT FALSE,
    min_spam_score INTEGER DEFAULT 70,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default bot types
INSERT INTO answer_bot_types (bot_name, bot_type, description) VALUES
('Time Waster Pro', 'time_waster', 'Keeps scammers on the line as long as possible'),
('Confusion Master', 'confusion', 'Confuses scammers with nonsensical responses'),
('Professional Assistant', 'professional', 'Pretends to be a helpful assistant'),
('Comedy Bot', 'funny', 'Entertains with jokes and funny responses')
ON CONFLICT (bot_name) DO NOTHING;
