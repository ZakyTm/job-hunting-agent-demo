-- 02_security_rls_and_traces.sql
-- Run this in your Supabase SQL Editor to harden the database and add the reasoning trace

-- 1. Add user_id column
ALTER TABLE jobs ADD COLUMN user_id UUID REFERENCES auth.users(id);

-- 2. Add reasoning_trace column (from 25-04 research log)
ALTER TABLE jobs ADD COLUMN reasoning_trace TEXT;

-- 3. Enable RLS
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- 4. Policy: authenticated users see only their own rows (for dashboard)
CREATE POLICY "Users see own jobs" ON jobs
  FOR SELECT USING (auth.uid() = user_id);

-- 5. Policy: allow inserts from service_role (backend uses service_role key)
CREATE POLICY "Service role inserts" ON jobs
  FOR INSERT WITH CHECK (true);
