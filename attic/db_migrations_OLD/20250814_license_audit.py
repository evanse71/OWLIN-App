-- Migration: Add license audit table
-- Date: 2025-08-14
-- Description: Creates license_audit table for tracking license events

-- Create license_audit table
CREATE TABLE IF NOT EXISTS license_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    state TEXT NOT NULL,
    reason TEXT,
    timestamp TEXT NOT NULL
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_license_audit_timestamp ON license_audit(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_license_audit_action ON license_audit(action); 