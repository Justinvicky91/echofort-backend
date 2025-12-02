-- Migration 024: Password Reset Tokens Table
-- Block 24F - Forgot Password Flow

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    UNIQUE(token_hash)
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_employee_id ON password_reset_tokens(employee_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token_hash ON password_reset_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);

-- Add comments
COMMENT ON TABLE password_reset_tokens IS 'Password reset tokens for forgot password flow';
COMMENT ON COLUMN password_reset_tokens.token_hash IS 'SHA-256 hash of the reset token (never store raw tokens)';
COMMENT ON COLUMN password_reset_tokens.expires_at IS 'Token expiration time (typically 30 minutes from creation)';
COMMENT ON COLUMN password_reset_tokens.used_at IS 'Timestamp when token was used (NULL if unused)';
