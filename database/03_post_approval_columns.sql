-- agentic-core/database/03_post_approval_columns.sql
-- Migration: Add columns for Tailor, Ghostwriter, and Interviewer outputs.
-- Run this in Supabase SQL Editor.

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS tailored_cv_md TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS tailored_cv_path TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS tailored_cv_diff JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS draft_email TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS email_subject TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS technical_questions JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS behavioral_questions JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS questions_to_ask JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS skill_gap_answers JSONB;
