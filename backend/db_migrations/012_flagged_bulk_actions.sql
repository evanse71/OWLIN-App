-- Migration 012: Flagged Issues Bulk Actions
-- Adds missing columns and tables for bulk actions functionality

-- Add missing columns to flagged_issues table
ALTER TABLE flagged_issues ADD COLUMN severity TEXT DEFAULT 'medium';
ALTER TABLE flagged_issues ADD COLUMN assignee_id TEXT;
ALTER TABLE flagged_issues ADD COLUMN resolved_by TEXT;
ALTER TABLE flagged_issues ADD COLUMN resolved_at TEXT;
ALTER TABLE flagged_issues ADD COLUMN last_comment_at TEXT;

-- Create issue_comments table
CREATE TABLE IF NOT EXISTS issue_comments (
    id TEXT PRIMARY KEY,
    issue_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (issue_id) REFERENCES flagged_issues(id) ON DELETE CASCADE
);

-- Create escalations table
CREATE TABLE IF NOT EXISTS escalations (
    id TEXT PRIMARY KEY,
    issue_id TEXT NOT NULL,
    escalated_by TEXT NOT NULL,
    to_role TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (issue_id) REFERENCES flagged_issues(id) ON DELETE CASCADE
);

-- Create audit_log table if it doesn't exist
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_flagged_issues_assignee ON flagged_issues(assignee_id);
CREATE INDEX IF NOT EXISTS idx_flagged_issues_resolved_by ON flagged_issues(resolved_by);
CREATE INDEX IF NOT EXISTS idx_flagged_issues_severity ON flagged_issues(severity);
CREATE INDEX IF NOT EXISTS idx_issue_comments_issue_id ON issue_comments(issue_id);
CREATE INDEX IF NOT EXISTS idx_issue_comments_author_id ON issue_comments(author_id);
CREATE INDEX IF NOT EXISTS idx_escalations_issue_id ON escalations(issue_id);
CREATE INDEX IF NOT EXISTS idx_escalations_escalated_by ON escalations(escalated_by);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at); 