-- Backup & Support Pack Migration
-- Creates tables for backup index and support pack index

-- Check if tables already exist
CREATE TABLE IF NOT EXISTS backup_index(
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  path TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  mode TEXT NOT NULL,
  app_version TEXT NOT NULL,
  db_schema_version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS support_pack_index(
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  path TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  notes TEXT,
  has_checksum INTEGER NOT NULL DEFAULT 1,
  app_version TEXT NOT NULL
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_backup_created ON backup_index(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backup_mode ON backup_index(mode);
CREATE INDEX IF NOT EXISTS idx_support_pack_created ON support_pack_index(created_at DESC);

-- Add any missing columns (idempotent)
PRAGMA table_info(backup_index);
PRAGMA table_info(support_pack_index);
