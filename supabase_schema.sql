-- ============================================================
-- RAAPID Sales Intelligence Agent -- Supabase Schema
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- ============================================================

CREATE TABLE runs (
  id                     UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  run_id                 TEXT        UNIQUE NOT NULL,
  started_at             TIMESTAMPTZ,
  input_type             TEXT,                        -- 'audio' or 'text'

  -- Prospect metadata
  prospect_company       TEXT,
  call_date              TEXT,
  duration_minutes       INTEGER,

  -- BANT (scalar fields for easy filtering)
  budget                 TEXT,
  budget_confidence      FLOAT,
  authority              TEXT,
  authority_confidence   FLOAT,
  need                   TEXT,
  need_confidence        FLOAT,
  timeline               TEXT,
  timeline_confidence    FLOAT,
  avg_confidence         FLOAT,

  -- Competitive intel
  current_vendor         TEXT,
  contract_renewal       TEXT,

  -- Review status
  human_review_required  BOOLEAN,
  human_review_outcome   TEXT,
  flags_count            INTEGER DEFAULT 0,
  pain_points_count      INTEGER DEFAULT 0,

  -- LLM outputs
  deal_summary           TEXT,
  email_draft            TEXT,
  transcript             TEXT,

  -- Nested arrays stored as JSONB
  stakeholders           JSONB DEFAULT '[]',
  pain_points            JSONB DEFAULT '[]',
  objections             JSONB DEFAULT '[]',
  next_steps             JSONB DEFAULT '[]',
  flags                  JSONB DEFAULT '[]',

  created_at             TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups by company and date
CREATE INDEX idx_runs_company    ON runs (prospect_company);
CREATE INDEX idx_runs_started_at ON runs (started_at DESC);
CREATE INDEX idx_runs_confidence ON runs (avg_confidence);

-- Enable Row Level Security (good practice)
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;

-- Allow all operations via service role key (used in backend)
CREATE POLICY "service role full access"
  ON runs FOR ALL
  USING (true)
  WITH CHECK (true);
