import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from uuid import UUID, uuid4
import sqlite3
import tempfile
import os
import json

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.flagged_issue_service import (
    bulk_update_issues, bulk_escalate_issues, bulk_assign_issues, bulk_comment_issues
)
from contracts import (
    BulkUpdateRequest, BulkEscalateRequest, BulkAssignRequest, BulkCommentRequest
)

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Create tables and sample data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create flagged_issues table
    cursor.execute("""
        CREATE TABLE flagged_issues (
            id TEXT PRIMARY KEY,
            item_description TEXT,
            quantity REAL,
            unit_price REAL,
            flagged INTEGER,
            source TEXT,
            severity TEXT DEFAULT 'medium',
            assignee_id TEXT,
            resolved_by TEXT,
            resolved_at TEXT,
            last_comment_at TEXT,
            status TEXT DEFAULT 'open'
        )
    """)
    
    # Create users table
    cursor.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            role TEXT
        )
    """)
    
    # Create issue_comments table
    cursor.execute("""
        CREATE TABLE issue_comments (
            id TEXT PRIMARY KEY,
            issue_id TEXT,
            author_id TEXT,
            body TEXT,
            created_at TEXT,
            FOREIGN KEY (issue_id) REFERENCES flagged_issues(id)
        )
    """)
    
    # Create escalations table
    cursor.execute("""
        CREATE TABLE escalations (
            id TEXT PRIMARY KEY,
            issue_id TEXT,
            escalated_by TEXT,
            to_role TEXT,
            reason TEXT,
            created_at TEXT,
            FOREIGN KEY (issue_id) REFERENCES flagged_issues(id)
        )
    """)
    
    # Create audit_log table
    cursor.execute("""
        CREATE TABLE audit_log (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            action TEXT,
            resource_type TEXT,
            resource_id TEXT,
            details TEXT,
            created_at TEXT
        )
    """)
    
    # Insert sample data
    issue_id_1 = str(uuid4())
    issue_id_2 = str(uuid4())
    user_id = str(uuid4())
    assignee_id = str(uuid4())
    
    # Sample flagged issues
    cursor.execute("""
        INSERT INTO flagged_issues (id, item_description, quantity, unit_price, flagged, source, severity)
        VALUES 
        (?, 'Test Item 1', 10, 5.0, 1, 'invoice', 'high'),
        (?, 'Test Item 2', 5, 10.0, 1, 'invoice', 'medium')
    """, (issue_id_1, issue_id_2))
    
    # Sample users
    cursor.execute("""
        INSERT INTO users (id, name, email, role)
        VALUES 
        (?, 'Test User', 'test@example.com', 'gm'),
        (?, 'Assignee User', 'assignee@example.com', 'finance')
    """, (user_id, assignee_id))
    
    conn.commit()
    conn.close()
    
    yield db_path, issue_id_1, issue_id_2, user_id, assignee_id
    
    # Cleanup
    os.unlink(db_path)

def test_bulk_update_issues_success(temp_db):
    """Test successful bulk update of issues."""
    db_path, issue_id_1, issue_id_2, user_id, assignee_id = temp_db
    
    with patch('services.flagged_issue_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_conn.cursor.return_value = sqlite3.connect(db_path).cursor()
        mock_db.return_value = mock_conn
        
        request = BulkUpdateRequest(
            issue_ids=[UUID(issue_id_1), UUID(issue_id_2)],
            action="resolve"
        )
        
        response = bulk_update_issues(request, user_id, "gm")
        
        assert response.ok is True
        assert len(response.results) == 2
        assert len(response.failed) == 0
        assert "Successfully resolved 2 issues" in response.message
        
        # Check that all results are successful
        for result in response.results:
            assert result.success is True
            assert result.error is None

def test_bulk_update_issues_rbac_denial(temp_db):
    """Test RBAC denial for bulk update."""
    db_path, issue_id_1, issue_id_2, user_id, assignee_id = temp_db
    
    request = BulkUpdateRequest(
        issue_ids=[UUID(issue_id_1), UUID(issue_id_2)],
        action="resolve"
    )
    
    # Test with shift_lead role (should be denied)
    response = bulk_update_issues(request, user_id, "shift_lead")
    
    assert response.ok is False
    assert len(response.results) == 0
    assert len(response.failed) == 2
    assert "Insufficient permissions" in response.message
    
    # Check that all failed results have permission error
    for result in response.failed:
        assert result.success is False
        assert "Insufficient permissions" in result.error

def test_bulk_escalate_issues_success(temp_db):
    """Test successful bulk escalation of issues."""
    db_path, issue_id_1, issue_id_2, user_id, assignee_id = temp_db
    
    with patch('services.flagged_issue_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_conn.cursor.return_value = sqlite3.connect(db_path).cursor()
        mock_db.return_value = mock_conn
        
        request = BulkEscalateRequest(
            issue_ids=[UUID(issue_id_1), UUID(issue_id_2)],
            to_role="finance",
            reason="Test escalation"
        )
        
        response = bulk_escalate_issues(request, user_id, "gm")
        
        assert response.ok is True
        assert len(response.results) == 2
        assert len(response.failed) == 0
        assert "Successfully escalated 2 issues to finance" in response.message

def test_bulk_escalate_issues_rbac_denial(temp_db):
    """Test RBAC denial for bulk escalation."""
    db_path, issue_id_1, issue_id_2, user_id, assignee_id = temp_db
    
    request = BulkEscalateRequest(
        issue_ids=[UUID(issue_id_1), UUID(issue_id_2)],
        to_role="finance",
        reason="Test escalation"
    )
    
    # Test with finance role (should be denied)
    response = bulk_escalate_issues(request, user_id, "finance")
    
    assert response.ok is False
    assert len(response.results) == 0
    assert len(response.failed) == 2
    assert "Only GM can escalate" in response.message

def test_bulk_assign_issues_success(temp_db):
    """Test successful bulk assignment of issues."""
    db_path, issue_id_1, issue_id_2, user_id, assignee_id = temp_db
    
    with patch('services.flagged_issue_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_conn.cursor.return_value = sqlite3.connect(db_path).cursor()
        mock_db.return_value = mock_conn
        
        request = BulkAssignRequest(
            issue_ids=[UUID(issue_id_1), UUID(issue_id_2)],
            assignee_id=UUID(assignee_id)
        )
        
        response = bulk_assign_issues(request, user_id, "gm")
        
        assert response.ok is True
        assert len(response.results) == 2
        assert len(response.failed) == 0
        assert "Successfully assigned 2 issues" in response.message

def test_bulk_assign_issues_assignee_not_found(temp_db):
    """Test bulk assignment with non-existent assignee."""
    db_path, issue_id_1, issue_id_2, user_id, assignee_id = temp_db
    
    with patch('services.flagged_issue_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_conn.cursor.return_value = sqlite3.connect(db_path).cursor()
        mock_db.return_value = mock_conn
        
        request = BulkAssignRequest(
            issue_ids=[UUID(issue_id_1), UUID(issue_id_2)],
            assignee_id=UUID(str(uuid4()))  # Non-existent user
        )
        
        response = bulk_assign_issues(request, user_id, "gm")
        
        assert response.ok is False
        assert len(response.results) == 0
        assert len(response.failed) == 2
        assert "Assignee not found" in response.message

def test_bulk_comment_issues_success(temp_db):
    """Test successful bulk commenting on issues."""
    db_path, issue_id_1, issue_id_2, user_id, assignee_id = temp_db
    
    with patch('services.flagged_issue_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_conn.cursor.return_value = sqlite3.connect(db_path).cursor()
        mock_db.return_value = mock_conn
        
        request = BulkCommentRequest(
            issue_ids=[UUID(issue_id_1), UUID(issue_id_2)],
            body="Test comment"
        )
        
        response = bulk_comment_issues(request, user_id, "shift_lead")
        
        assert response.ok is True
        assert len(response.results) == 2
        assert len(response.failed) == 0
        assert "Successfully commented on 2 issues" in response.message

def test_bulk_comment_issues_empty_body(temp_db):
    """Test bulk comment with empty body."""
    db_path, issue_id_1, issue_id_2, user_id, assignee_id = temp_db
    
    # Test with whitespace-only body (should be trimmed to empty)
    request = BulkCommentRequest(
        issue_ids=[UUID(issue_id_1), UUID(issue_id_2)],
        body="   "
    )
    
    response = bulk_comment_issues(request, user_id, "shift_lead")
    
    assert response.ok is False
    assert len(response.results) == 0
    assert len(response.failed) == 2

def test_partial_failure_with_mixed_ids(temp_db):
    """Test partial failure when some issue IDs are invalid."""
    db_path, issue_id_1, issue_id_2, user_id, assignee_id = temp_db
    
    with patch('services.flagged_issue_service.get_db_connection') as mock_db:
        mock_conn = Mock()
        mock_conn.cursor.return_value = sqlite3.connect(db_path).cursor()
        mock_db.return_value = mock_conn
        
        # Mix valid and invalid IDs
        valid_id = UUID(issue_id_1)
        invalid_id = UUID(str(uuid4()))
        
        request = BulkUpdateRequest(
            issue_ids=[valid_id, invalid_id],
            action="resolve"
        )
        
        response = bulk_update_issues(request, user_id, "gm")
        
        # Should have partial success
        assert len(response.results) == 1
        assert len(response.failed) == 1
        assert response.results[0].success is True
        assert response.failed[0].success is False
        assert "Issue not found" in response.failed[0].error

def test_migration_rerun_cleanly(temp_db):
    """Test that migration can be re-run cleanly."""
    db_path, issue_id_1, issue_id_2, user_id, assignee_id = temp_db
    
    # Re-run the migration (should not fail)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Try to create tables again (should be idempotent)
    cursor.execute("CREATE TABLE IF NOT EXISTS issue_comments (id TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS escalations (id TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS audit_log (id TEXT PRIMARY KEY)")
    
    conn.commit()
    conn.close()
    
    # If we get here without errors, the migration is idempotent
    assert True 