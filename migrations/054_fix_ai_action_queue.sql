ALTER TABLE ai_action_queue
ADD COLUMN IF NOT EXISTS reason TEXT,
ADD COLUMN IF NOT EXISTS risk_level VARCHAR(50) DEFAULT 'medium';

-- Add other missing columns if any
ALTER TABLE ai_action_queue
ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER,
ADD COLUMN IF NOT EXISTS source VARCHAR(255) DEFAULT 'EchoFort AI';

-- Add foreign key constraint if users table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        ALTER TABLE ai_action_queue
        ADD CONSTRAINT fk_created_by_user
        FOREIGN KEY (created_by_user_id)
        REFERENCES users(id)
        ON DELETE SET NULL;
    END IF;
END $$;
