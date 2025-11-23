-- Migration 045: Add Extremism & AI Attack Detection Fields to Evidence Vault
-- Created: 2025-11-23
-- Purpose: Extend evidence_vault to support Block 5 harmful content detection
-- Legal: All fields are AI predictions, not legal labels

-- Add new columns to evidence_vault (idempotent, backward-compatible)
ALTER TABLE evidence_vault 
ADD COLUMN IF NOT EXISTS content_category VARCHAR(100) DEFAULT 'benign',
ADD COLUMN IF NOT EXISTS violence_or_extremism_risk INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;

-- Add indexes for performance on new fields
CREATE INDEX IF NOT EXISTS idx_evidence_vault_content_category ON evidence_vault(content_category);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_extremism_risk ON evidence_vault(violence_or_extremism_risk DESC);
CREATE INDEX IF NOT EXISTS idx_evidence_vault_tags ON evidence_vault USING GIN(tags);

-- Add comments for legal clarity
COMMENT ON COLUMN evidence_vault.content_category IS 'AI-predicted content category: benign, scam_fraud, harmful_extremism, hate_speech, self_harm_risk, etc. NOT a legal determination.';
COMMENT ON COLUMN evidence_vault.violence_or_extremism_risk IS 'AI-predicted risk score 0-10 for violent or extremist content. NOT a legal determination.';
COMMENT ON COLUMN evidence_vault.tags IS 'Array of AI-generated tags for detailed classification. NOT legal labels.';
