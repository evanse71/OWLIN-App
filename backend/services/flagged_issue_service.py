from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID, uuid4
import sqlite3
import os
import json

from contracts import (
    BulkUpdateRequest, BulkEscalateRequest, BulkAssignRequest, BulkCommentRequest,
    BulkActionResult, BulkActionResponse
)

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

def bulk_update_issues(request: BulkUpdateRequest, user_id: str, user_role: str) -> BulkActionResponse:
    """Bulk resolve or dismiss flagged issues."""
    # RBAC check
    if user_role not in ["gm", "finance"]:
        return BulkActionResponse(
            ok=False,
            results=[],
            failed=[BulkActionResult(issue_id=issue_id, success=False, error="Insufficient permissions") 
                   for issue_id in request.issue_ids],
            message="Insufficient permissions for this action"
        )
    
    conn = get_db_connection()
    cursor = conn.cursor()
    results = []
    failed = []
    
    try:
        for issue_id in request.issue_ids:
            try:
                # Check if issue exists
                cursor.execute("SELECT id FROM flagged_issues WHERE id = ?", (str(issue_id),))
                if not cursor.fetchone():
                    failed.append(BulkActionResult(issue_id=issue_id, success=False, error="Issue not found"))
                    continue
                
                # Update issue
                now = datetime.utcnow().isoformat()
                cursor.execute("""
                    UPDATE flagged_issues 
                    SET resolved_by = ?, resolved_at = ?, status = ?
                    WHERE id = ?
                """, (user_id, now, request.action, str(issue_id)))
                
                # Log to audit
                audit_id = str(uuid4())
                cursor.execute("""
                    INSERT INTO audit_log (id, user_id, action, resource_type, resource_id, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (audit_id, user_id, f"bulk_{request.action}", "flagged_issue", str(issue_id), 
                     json.dumps({"action": request.action}), now))
                
                results.append(BulkActionResult(issue_id=issue_id, success=True))
                
            except Exception as e:
                failed.append(BulkActionResult(issue_id=issue_id, success=False, error=str(e)))
        
        conn.commit()
        
        return BulkActionResponse(
            ok=len(failed) == 0,
            results=results,
            failed=failed,
            message=f"Successfully {request.action}d {len(results)} issues"
        )
        
    except Exception as e:
        conn.rollback()
        return BulkActionResponse(
            ok=False,
            results=[],
            failed=[BulkActionResult(issue_id=issue_id, success=False, error=str(e)) 
                   for issue_id in request.issue_ids],
            message=f"Database error: {str(e)}"
        )
    finally:
        conn.close()

def bulk_escalate_issues(request: BulkEscalateRequest, user_id: str, user_role: str) -> BulkActionResponse:
    """Bulk escalate flagged issues."""
    # RBAC check
    if user_role != "gm":
        return BulkActionResponse(
            ok=False,
            results=[],
            failed=[BulkActionResult(issue_id=issue_id, success=False, error="Only GM can escalate") 
                   for issue_id in request.issue_ids],
            message="Only GM can escalate issues"
        )
    
    conn = get_db_connection()
    cursor = conn.cursor()
    results = []
    failed = []
    
    try:
        for issue_id in request.issue_ids:
            try:
                # Check if issue exists
                cursor.execute("SELECT id FROM flagged_issues WHERE id = ?", (str(issue_id),))
                if not cursor.fetchone():
                    failed.append(BulkActionResult(issue_id=issue_id, success=False, error="Issue not found"))
                    continue
                
                # Create escalation record
                escalation_id = str(uuid4())
                now = datetime.utcnow().isoformat()
                cursor.execute("""
                    INSERT INTO escalations (id, issue_id, escalated_by, to_role, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (escalation_id, str(issue_id), user_id, request.to_role, request.reason, now))
                
                # Update issue status
                cursor.execute("""
                    UPDATE flagged_issues 
                    SET status = 'escalated'
                    WHERE id = ?
                """, (str(issue_id),))
                
                # Log to audit
                audit_id = str(uuid4())
                cursor.execute("""
                    INSERT INTO audit_log (id, user_id, action, resource_type, resource_id, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (audit_id, user_id, "bulk_escalate", "flagged_issue", str(issue_id), 
                     json.dumps({"to_role": request.to_role, "reason": request.reason}), now))
                
                results.append(BulkActionResult(issue_id=issue_id, success=True))
                
            except Exception as e:
                failed.append(BulkActionResult(issue_id=issue_id, success=False, error=str(e)))
        
        conn.commit()
        
        return BulkActionResponse(
            ok=len(failed) == 0,
            results=results,
            failed=failed,
            message=f"Successfully escalated {len(results)} issues to {request.to_role}"
        )
        
    except Exception as e:
        conn.rollback()
        return BulkActionResponse(
            ok=False,
            results=[],
            failed=[BulkActionResult(issue_id=issue_id, success=False, error=str(e)) 
                   for issue_id in request.issue_ids],
            message=f"Database error: {str(e)}"
        )
    finally:
        conn.close()

def bulk_assign_issues(request: BulkAssignRequest, user_id: str, user_role: str) -> BulkActionResponse:
    """Bulk assign flagged issues."""
    # RBAC check
    if user_role not in ["gm", "finance"]:
        return BulkActionResponse(
            ok=False,
            results=[],
            failed=[BulkActionResult(issue_id=issue_id, success=False, error="Insufficient permissions") 
                   for issue_id in request.issue_ids],
            message="Insufficient permissions for this action"
        )
    
    conn = get_db_connection()
    cursor = conn.cursor()
    results = []
    failed = []
    
    try:
        # Verify assignee exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (str(request.assignee_id),))
        if not cursor.fetchone():
            return BulkActionResponse(
                ok=False,
                results=[],
                failed=[BulkActionResult(issue_id=issue_id, success=False, error="Assignee not found") 
                       for issue_id in request.issue_ids],
                message="Assignee not found"
            )
        
        for issue_id in request.issue_ids:
            try:
                # Check if issue exists
                cursor.execute("SELECT id FROM flagged_issues WHERE id = ?", (str(issue_id),))
                if not cursor.fetchone():
                    failed.append(BulkActionResult(issue_id=issue_id, success=False, error="Issue not found"))
                    continue
                
                # Update issue assignment
                cursor.execute("""
                    UPDATE flagged_issues 
                    SET assignee_id = ?
                    WHERE id = ?
                """, (str(request.assignee_id), str(issue_id)))
                
                # Log to audit
                audit_id = str(uuid4())
                now = datetime.utcnow().isoformat()
                cursor.execute("""
                    INSERT INTO audit_log (id, user_id, action, resource_type, resource_id, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (audit_id, user_id, "bulk_assign", "flagged_issue", str(issue_id), 
                     json.dumps({"assignee_id": str(request.assignee_id)}), now))
                
                results.append(BulkActionResult(issue_id=issue_id, success=True))
                
            except Exception as e:
                failed.append(BulkActionResult(issue_id=issue_id, success=False, error=str(e)))
        
        conn.commit()
        
        return BulkActionResponse(
            ok=len(failed) == 0,
            results=results,
            failed=failed,
            message=f"Successfully assigned {len(results)} issues"
        )
        
    except Exception as e:
        conn.rollback()
        return BulkActionResponse(
            ok=False,
            results=[],
            failed=[BulkActionResult(issue_id=issue_id, success=False, error=str(e)) 
                   for issue_id in request.issue_ids],
            message=f"Database error: {str(e)}"
        )
    finally:
        conn.close()

def bulk_comment_issues(request: BulkCommentRequest, user_id: str, user_role: str) -> BulkActionResponse:
    """Bulk comment on flagged issues."""
    # RBAC check
    if user_role not in ["gm", "finance", "shift_lead"]:
        return BulkActionResponse(
            ok=False,
            results=[],
            failed=[BulkActionResult(issue_id=issue_id, success=False, error="Insufficient permissions") 
                   for issue_id in request.issue_ids],
            message="Insufficient permissions for this action"
        )
    
    conn = get_db_connection()
    cursor = conn.cursor()
    results = []
    failed = []
    
    try:
        for issue_id in request.issue_ids:
            try:
                # Check if issue exists
                cursor.execute("SELECT id FROM flagged_issues WHERE id = ?", (str(issue_id),))
                if not cursor.fetchone():
                    failed.append(BulkActionResult(issue_id=issue_id, success=False, error="Issue not found"))
                    continue
                
                # Create comment
                comment_id = str(uuid4())
                now = datetime.utcnow().isoformat()
                cursor.execute("""
                    INSERT INTO issue_comments (id, issue_id, author_id, body, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (comment_id, str(issue_id), user_id, request.body, now))
                
                # Update issue last_comment_at
                cursor.execute("""
                    UPDATE flagged_issues 
                    SET last_comment_at = ?
                    WHERE id = ?
                """, (now, str(issue_id)))
                
                # Log to audit
                audit_id = str(uuid4())
                cursor.execute("""
                    INSERT INTO audit_log (id, user_id, action, resource_type, resource_id, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (audit_id, user_id, "bulk_comment", "flagged_issue", str(issue_id), 
                     json.dumps({"comment_length": len(request.body)}), now))
                
                results.append(BulkActionResult(issue_id=issue_id, success=True))
                
            except Exception as e:
                failed.append(BulkActionResult(issue_id=issue_id, success=False, error=str(e)))
        
        conn.commit()
        
        return BulkActionResponse(
            ok=len(failed) == 0,
            results=results,
            failed=failed,
            message=f"Successfully commented on {len(results)} issues"
        )
        
    except Exception as e:
        conn.rollback()
        return BulkActionResponse(
            ok=False,
            results=[],
            failed=[BulkActionResult(issue_id=issue_id, success=False, error=str(e)) 
                   for issue_id in request.issue_ids],
            message=f"Database error: {str(e)}"
        )
    finally:
        conn.close() 