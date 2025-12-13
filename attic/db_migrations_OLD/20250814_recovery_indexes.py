-- Migration: Add recovery mode indexes
-- Date: 2025-08-14
-- Description: Creates indexes for recovery mode performance

-- Create index for audit log recovery events
CREATE INDEX IF NOT EXISTS idx_audit_recovery_events ON audit_log(action, timestamp) 
WHERE action LIKE 'recovery.%';

-- Create index for backup metadata
CREATE INDEX IF NOT EXISTS idx_backups_meta_created ON backups_meta(created_at DESC);

-- Create index for support pack index
CREATE INDEX IF NOT EXISTS idx_support_pack_created ON support_pack_index(created_at DESC);

-- Create index for license audit
CREATE INDEX IF NOT EXISTS idx_license_audit_timestamp ON license_audit(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_license_audit_action ON license_audit(action); 