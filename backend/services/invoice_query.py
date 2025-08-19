"""
invoice_query.py
===============

Advanced invoice query service with filtering, sorting, and role-aware defaults.
Supports SQLite-backed queries with performance optimizations.
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class InvoiceFilter:
    """Filter parameters for invoice queries."""
    venue_id: Optional[str] = None
    supplier_name: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    status: Optional[List[str]] = None
    search_text: Optional[str] = None
    only_flagged: bool = False
    only_unmatched: bool = False
    only_with_credit: bool = False
    include_utilities: bool = True

@dataclass
class InvoiceSort:
    """Sort parameters for invoice queries."""
    sort_by: str = "date_desc"  # date_desc, date_asc, value_desc, value_asc, supplier_asc
    limit: Optional[int] = None
    offset: int = 0

@dataclass
class InvoiceQueryResult:
    """Result of an invoice query."""
    invoices: List[Dict[str, Any]]
    total_count: int
    filters_applied: Dict[str, Any]
    query_time_ms: float

class InvoiceQueryService:
    """Service for advanced invoice queries with filtering and sorting."""
    
    def __init__(self, db_path: str = "data/owlin.db"):
        self.db_path = db_path
    
    def get_db_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def get_role_defaults(self, role: str) -> InvoiceFilter:
        """Get role-aware filter defaults."""
        defaults = InvoiceFilter()
        
        if role == "finance":
            defaults.only_flagged = True
            defaults.sort_by = "date_desc"
        elif role == "GM":
            defaults.sort_by = "supplier_asc"
        elif role == "shift_lead":
            defaults.only_unmatched = True
            defaults.sort_by = "date_desc"
        
        # Default date range: last 90 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        defaults.date_start = start_date.strftime("%Y-%m-%d")
        defaults.date_end = end_date.strftime("%Y-%m-%d")
        
        return defaults
    
    def build_query(self, filters: InvoiceFilter, sort: InvoiceSort) -> Tuple[str, List[Any]]:
        """Build SQL query with filters and sorting."""
        query_parts = ["SELECT * FROM invoices WHERE 1=1"]
        params = []
        
        # Venue filter (if venue_id is implemented)
        if filters.venue_id:
            query_parts.append("AND venue_id = ?")
            params.append(filters.venue_id)
        
        # Supplier filter
        if filters.supplier_name:
            query_parts.append("AND supplier_name LIKE ?")
            params.append(f"%{filters.supplier_name}%")
        
        # Date range filter
        if filters.date_start:
            query_parts.append("AND invoice_date >= ?")
            params.append(filters.date_start)
        
        if filters.date_end:
            query_parts.append("AND invoice_date <= ?")
            params.append(filters.date_end)
        
        # Status filter
        if filters.status:
            placeholders = ",".join(["?" for _ in filters.status])
            query_parts.append(f"AND status IN ({placeholders})")
            params.extend(filters.status)
        
        # Search text filter (searches multiple fields)
        if filters.search_text:
            search_term = f"%{filters.search_text}%"
            query_parts.append("""
                AND (
                    supplier_name LIKE ? OR 
                    invoice_number LIKE ? OR 
                    invoice_date LIKE ?
                )
            """)
            params.extend([search_term, search_term, search_term])
        
        # Flagged filter
        if filters.only_flagged:
            query_parts.append("AND status = 'flagged'")
        
        # Unmatched filter
        if filters.only_unmatched:
            query_parts.append("AND status = 'unmatched'")
        
        # Credit filter (if credit field exists)
        if filters.only_with_credit:
            query_parts.append("AND credit_amount > 0")
        
        # Utilities filter
        if not filters.include_utilities:
            query_parts.append("AND doc_type != 'utility'")
        
        # Build ORDER BY clause
        order_clause = self._build_order_clause(sort.sort_by)
        query_parts.append(order_clause)
        
        # Add LIMIT and OFFSET
        if sort.limit:
            query_parts.append(f"LIMIT {sort.limit}")
        if sort.offset > 0:
            query_parts.append(f"OFFSET {sort.offset}")
        
        return " ".join(query_parts), params
    
    def _build_order_clause(self, sort_by: str) -> str:
        """Build ORDER BY clause based on sort parameter."""
        sort_mapping = {
            "date_desc": "ORDER BY invoice_date DESC, upload_timestamp DESC",
            "date_asc": "ORDER BY invoice_date ASC, upload_timestamp ASC",
            "value_desc": "ORDER BY total_amount DESC",
            "value_asc": "ORDER BY total_amount ASC",
            "supplier_asc": "ORDER BY supplier_name ASC",
            "supplier_desc": "ORDER BY supplier_name DESC",
            "confidence_desc": "ORDER BY confidence DESC",
            "confidence_asc": "ORDER BY confidence ASC"
        }
        
        return sort_mapping.get(sort_by, "ORDER BY upload_timestamp DESC")
    
    def get_distinct_suppliers(self) -> List[str]:
        """Get list of distinct suppliers for dropdown."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT supplier_name 
            FROM invoices 
            WHERE supplier_name IS NOT NULL AND supplier_name != ''
            ORDER BY supplier_name ASC
        """)
        
        suppliers = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return suppliers
    
    def get_distinct_venues(self) -> List[Dict[str, Any]]:
        """Get list of distinct venues for dropdown."""
        # For now, return a default venue since venue_id might not be implemented
        return [{"id": "all", "name": "All Venues"}]
    
    def query_invoices(
        self, 
        filters: Optional[InvoiceFilter] = None,
        sort: Optional[InvoiceSort] = None,
        role: str = "viewer"
    ) -> InvoiceQueryResult:
        """Execute invoice query with filters and sorting."""
        import time
        start_time = time.time()
        
        # Apply role defaults if no filters provided
        if filters is None:
            filters = self.get_role_defaults(role)
        
        if sort is None:
            sort = InvoiceSort()
        
        # Build and execute query
        query, params = self.build_query(filters, sort)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert rows to dictionaries
            invoices = []
            for row in rows:
                invoice = self._row_to_dict(row, cursor.description)
                invoices.append(invoice)
            
            # Get total count for pagination
            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            if "ORDER BY" in count_query:
                count_query = count_query.split("ORDER BY")[0]
            if "LIMIT" in count_query:
                count_query = count_query.split("LIMIT")[0]
            
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
        finally:
            conn.close()
        
        query_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return InvoiceQueryResult(
            invoices=invoices,
            total_count=total_count,
            filters_applied={
                "venue_id": filters.venue_id,
                "supplier_name": filters.supplier_name,
                "date_start": filters.date_start,
                "date_end": filters.date_end,
                "status": filters.status,
                "search_text": filters.search_text,
                "only_flagged": filters.only_flagged,
                "only_unmatched": filters.only_unmatched,
                "only_with_credit": filters.only_with_credit,
                "include_utilities": filters.include_utilities,
                "sort_by": sort.sort_by
            },
            query_time_ms=query_time
        )
    
    def _row_to_dict(self, row: Tuple, description: Tuple) -> Dict[str, Any]:
        """Convert database row to dictionary."""
        invoice = {}
        for i, column in enumerate(description):
            value = row[i]
            
            # Handle JSON fields
            if column[0] in ['line_items', 'addresses', 'signature_regions', 'field_confidence', 'warnings']:
                if value and isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        value = None
            
            # Handle page numbers
            elif column[0] == 'page_numbers' and value:
                try:
                    value = [int(x) for x in value.split(",")]
                except (ValueError, AttributeError):
                    value = []
            
            # Normalize confidence
            elif column[0] == 'confidence' and value is not None:
                try:
                    conf = float(value)
                    if conf <= 1.0:
                        conf = conf * 100.0
                    value = max(0.0, min(100.0, conf))
                except (ValueError, TypeError):
                    value = 0.0
            
            invoice[column[0]] = value
        
        return invoice

# Global instance
invoice_query_service = InvoiceQueryService() 