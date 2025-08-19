-- Update Progress Journal Migration
-- Creates table for tracking update progress with durable journal

-- Check if table already exists
CREATE TABLE IF NOT EXISTS update_progress_journal (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  bundle_id TEXT NOT NULL,
  step TEXT NOT NULL,
  percent INTEGER NOT NULL,
  message TEXT,
  occurred_at TEXT NOT NULL
);

-- Create index for efficient querying
CREATE INDEX IF NOT EXISTS idx_upj_job ON update_progress_journal(job_id, occurred_at);

-- Add any missing columns (idempotent)
PRAGMA table_info(update_progress_journal);
