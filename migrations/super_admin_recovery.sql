-- Super Admin Recovery Codes Table

CREATE TABLE IF NOT EXISTS super_admin_recovery (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    recovery_codes TEXT NOT NULL,  -- Comma-separated recovery codes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    CONSTRAINT fk_user_email FOREIGN KEY (email) REFERENCES users(email) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_super_admin_recovery_email ON super_admin_recovery(email);

-- Insert initial recovery codes for Super Admin (will be replaced when they generate new ones)
INSERT INTO super_admin_recovery (email, recovery_codes, created_at)
VALUES ('Vicky.Jvsap@gmail.com', '', NOW())
ON CONFLICT (email) DO NOTHING;

