-- database/03_production_hardening_migration.sql
-- Migration to support Deduplication, Rich Match Data, and Company Intel

-- 1. Add columns for deduplication and structured LLM data
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS source_message_id TEXT,
ADD COLUMN IF NOT EXISTS matched_skills JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS missing_skills JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS company_intel JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS reasoning_trace TEXT;

-- 2. Create an index for faster deduplication checks
-- This is critical as the table grows to prevent slow ingestions
CREATE INDEX IF NOT EXISTS idx_jobs_source_message_id ON jobs (source_message_id);

-- 3. Update RLS (Row Level Security) to allow the service role to insert these fields
-- Note: Ensure your existing RLS policies allow for these new columns if you use strict selection.
