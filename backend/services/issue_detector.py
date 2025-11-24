# -*- coding: utf-8 -*-
"""
Issue Detector Module

This module detects mismatches and missing items between invoices and delivery notes,
as specified in the System Bible Section 2.1 (line 129).

Detects:
- Price mismatches
- Short deliveries (quantity discrepancies)
- Missing items
"""

from __future__ import annotations
import logging
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

LOGGER = logging.getLogger("owlin.services.issue_detector")
LOGGER.setLevel(logging.INFO)

DB_PATH = "data/owlin.db"


@dataclass
class Issue:
    """Represents a detected issue."""
    id: Optional[int]
    invoice_id: str
    delivery_id: Optional[str]
    type: str  # "price_mismatch", "quantity_discrepancy", "short_delivery", "missing_item"
    severity: str  # "high", "medium", "low"
    status: str  # "open", "resolved", "ignored"
    value_delta: float
    description: str
    created_at: str


def _get_db_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def detect_price_mismatch(invoice_id: str, delivery_id: Optional[str] = None) -> Optional[Issue]:
    """
    Detect price mismatch between invoice and delivery note.
    
    As per System Bible Section 2.6: Total difference ≤ 1% or ≤ £2 absolute
    
    Args:
        invoice_id: Invoice ID
        delivery_id: Optional delivery note ID (if None, will try to find paired delivery note)
    
    Returns:
        Issue object if mismatch detected, None otherwise
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get invoice total
        cursor.execute("""
            SELECT value, supplier, date
            FROM invoices
            WHERE id = ?
        """, (invoice_id,))
        
        inv_row = cursor.fetchone()
        if not inv_row:
            LOGGER.warning(f"Invoice {invoice_id} not found")
            return None
        
        invoice_total = inv_row[0] or 0.0
        supplier = inv_row[1]
        invoice_date = inv_row[2]
        
        # If no delivery_id provided, try to find paired delivery note
        if not delivery_id:
            cursor.execute("""
                SELECT delivery_id
                FROM pairs
                WHERE invoice_id = ? AND status = 'confirmed'
                LIMIT 1
            """, (invoice_id,))
            
            pair_row = cursor.fetchone()
            if pair_row:
                delivery_id = pair_row[0]
            else:
                LOGGER.debug(f"No paired delivery note found for invoice {invoice_id}")
                return None
        
        # Get delivery note total
        cursor.execute("""
            SELECT total
            FROM documents
            WHERE id = ? AND doc_type = 'delivery_note'
        """, (delivery_id,))
        
        del_row = cursor.fetchone()
        if not del_row:
            LOGGER.warning(f"Delivery note {delivery_id} not found")
            return None
        
        delivery_total = del_row[0] or 0.0
        
        # Calculate difference
        total_diff = abs(invoice_total - delivery_total)
        max_total = max(abs(invoice_total), abs(delivery_total))
        
        # Check if mismatch exceeds threshold (1% or £2 absolute)
        threshold_percent = 0.01  # 1%
        threshold_absolute = 2.0  # £2
        
        is_mismatch = False
        if max_total > 0:
            percent_diff = total_diff / max_total
            is_mismatch = (percent_diff > threshold_percent) and (total_diff > threshold_absolute)
        else:
            is_mismatch = total_diff > threshold_absolute
        
        if is_mismatch:
            severity = "high" if total_diff > 10.0 else "medium"
            
            issue = Issue(
                id=None,
                invoice_id=invoice_id,
                delivery_id=delivery_id,
                type="price_mismatch",
                severity=severity,
                status="open",
                value_delta=invoice_total - delivery_total,
                description=f"Invoice total ({invoice_total:.2f}) differs from delivery note ({delivery_total:.2f}) by {total_diff:.2f}",
                created_at=datetime.now().isoformat()
            )
            
            LOGGER.info(f"Price mismatch detected: invoice={invoice_id}, delta={total_diff:.2f}")
            return issue
        
        return None
        
    except Exception as e:
        LOGGER.error(f"Error detecting price mismatch: {e}")
        return None
    finally:
        conn.close()


def detect_short_delivery(invoice_id: str, delivery_id: Optional[str] = None) -> Optional[Issue]:
    """
    Detect short delivery (quantity discrepancies between invoice and delivery note).
    
    Args:
        invoice_id: Invoice ID
        delivery_id: Optional delivery note ID
    
    Returns:
        Issue object if short delivery detected, None otherwise
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get invoice line items
        cursor.execute("""
            SELECT description, qty, total
            FROM invoice_line_items
            WHERE invoice_id = ?
            ORDER BY line_number
        """, (invoice_id,))
        
        invoice_lines = cursor.fetchall()
        
        if not invoice_lines:
            LOGGER.debug(f"No line items found for invoice {invoice_id}")
            return None
        
        # If no delivery_id provided, try to find paired delivery note
        if not delivery_id:
            cursor.execute("""
                SELECT delivery_id
                FROM pairs
                WHERE invoice_id = ? AND status = 'confirmed'
                LIMIT 1
            """, (invoice_id,))
            
            pair_row = cursor.fetchone()
            if pair_row:
                delivery_id = pair_row[0]
            else:
                LOGGER.debug(f"No paired delivery note found for invoice {invoice_id}")
                return None
        
        # Get delivery note line items (assuming same structure)
        # Note: This assumes delivery notes have line items in a similar table
        # If delivery notes use documents table, we may need to parse from OCR
        cursor.execute("""
            SELECT description, qty, total
            FROM invoice_line_items
            WHERE doc_id = ?
            ORDER BY line_number
        """, (delivery_id,))
        
        delivery_lines = cursor.fetchall()
        
        if not delivery_lines:
            LOGGER.debug(f"No line items found for delivery note {delivery_id}")
            return None
        
        # Compare quantities
        short_items = []
        total_short_value = 0.0
        
        # Create lookup by description
        delivery_lookup = {}
        for desc, qty, total in delivery_lines:
            desc_key = (desc or "").lower().strip()
            delivery_lookup[desc_key] = {"qty": qty or 0.0, "total": total or 0.0}
        
        for inv_desc, inv_qty, inv_total in invoice_lines:
            desc_key = (inv_desc or "").lower().strip()
            inv_qty = inv_qty or 0.0
            inv_total = inv_total or 0.0
            
            if desc_key in delivery_lookup:
                del_qty = delivery_lookup[desc_key]["qty"]
                qty_diff = inv_qty - del_qty
                
                if qty_diff > 0.01:  # Short delivery detected
                    short_items.append({
                        "description": inv_desc,
                        "invoice_qty": inv_qty,
                        "delivery_qty": del_qty,
                        "shortage": qty_diff
                    })
                    total_short_value += (qty_diff * (inv_total / inv_qty if inv_qty > 0 else 0))
            else:
                # Item missing entirely
                short_items.append({
                    "description": inv_desc,
                    "invoice_qty": inv_qty,
                    "delivery_qty": 0.0,
                    "shortage": inv_qty
                })
                total_short_value += inv_total
        
        if short_items:
            severity = "high" if total_short_value > 50.0 else "medium" if total_short_value > 10.0 else "low"
            
            issue = Issue(
                id=None,
                invoice_id=invoice_id,
                delivery_id=delivery_id,
                type="short_delivery",
                severity=severity,
                status="open",
                value_delta=-total_short_value,
                description=f"Short delivery detected: {len(short_items)} item(s) with quantity discrepancies totaling {total_short_value:.2f}",
                created_at=datetime.now().isoformat()
            )
            
            LOGGER.info(f"Short delivery detected: invoice={invoice_id}, items={len(short_items)}, value={total_short_value:.2f}")
            return issue
        
        return None
        
    except Exception as e:
        LOGGER.error(f"Error detecting short delivery: {e}")
        return None
    finally:
        conn.close()


def detect_quantity_discrepancy(invoice_id: str, delivery_id: Optional[str] = None) -> Optional[Issue]:
    """
    Detect quantity discrepancies (similar to short_delivery but focuses on quantity mismatches).
    
    Args:
        invoice_id: Invoice ID
        delivery_id: Optional delivery note ID
    
    Returns:
        Issue object if quantity discrepancy detected, None otherwise
    """
    # This is similar to short_delivery but may have different thresholds
    # For now, we'll use the same logic
    return detect_short_delivery(invoice_id, delivery_id)


def save_issue(issue: Issue) -> int:
    """
    Save issue to database.
    
    Args:
        issue: Issue object to save
    
    Returns:
        Issue ID
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Ensure issues table exists (will be created by migration)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT NOT NULL,
                delivery_id TEXT,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                value_delta REAL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id)
            )
        """)
        
        cursor.execute("""
            INSERT INTO issues (invoice_id, delivery_id, type, severity, status, value_delta, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            issue.invoice_id,
            issue.delivery_id,
            issue.type,
            issue.severity,
            issue.status,
            issue.value_delta,
            issue.description,
            issue.created_at
        ))
        
        issue_id = cursor.lastrowid
        
        # Update invoice issues_count
        cursor.execute("""
            UPDATE invoices
            SET issues_count = (
                SELECT COUNT(*) FROM issues
                WHERE invoice_id = ? AND status = 'open'
            )
            WHERE id = ?
        """, (issue.invoice_id, issue.invoice_id))
        
        conn.commit()
        LOGGER.info(f"Issue saved: id={issue_id}, type={issue.type}, invoice={issue.invoice_id}")
        return issue_id
        
    except Exception as e:
        LOGGER.error(f"Error saving issue: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_issues_for_invoice(invoice_id: str, status: Optional[str] = None) -> List[Issue]:
    """
    Get all issues for an invoice.
    
    Args:
        invoice_id: Invoice ID
        status: Optional status filter ('open', 'resolved', 'ignored')
    
    Returns:
        List of Issue objects
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT id, invoice_id, delivery_id, type, severity, status, value_delta, description, created_at
            FROM issues
            WHERE invoice_id = ?
        """
        params = [invoice_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        issues = []
        for row in rows:
            issues.append(Issue(
                id=row[0],
                invoice_id=row[1],
                delivery_id=row[2],
                type=row[3],
                severity=row[4],
                status=row[5],
                value_delta=row[6] or 0.0,
                description=row[7] or "",
                created_at=row[8] or ""
            ))
        
        return issues
        
    except Exception as e:
        LOGGER.error(f"Error getting issues: {e}")
        return []
    finally:
        conn.close()


def resolve_issue(issue_id: int) -> bool:
    """
    Mark an issue as resolved.
    
    Args:
        issue_id: Issue ID
    
    Returns:
        True if successful, False otherwise
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE issues
            SET status = 'resolved'
            WHERE id = ?
        """, (issue_id,))
        
        if cursor.rowcount > 0:
            # Update invoice issues_count
            cursor.execute("""
                SELECT invoice_id FROM issues WHERE id = ?
            """, (issue_id,))
            
            row = cursor.fetchone()
            if row:
                invoice_id = row[0]
                cursor.execute("""
                    UPDATE invoices
                    SET issues_count = (
                        SELECT COUNT(*) FROM issues
                        WHERE invoice_id = ? AND status = 'open'
                    )
                    WHERE id = ?
                """, (invoice_id, invoice_id))
            
            conn.commit()
            LOGGER.info(f"Issue resolved: id={issue_id}")
            return True
        
        return False
        
    except Exception as e:
        LOGGER.error(f"Error resolving issue: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

