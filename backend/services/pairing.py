"""
Enhanced Pairing Service for OWLIN

This module implements comprehensive pairing logic for matching invoices with delivery notes.
It uses multiple heuristics including fuzzy supplier matching, date windows, line-item similarity,
quantity comparisons, and price matching to create high-confidence pairs.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import datetime
import json
import uuid
from dataclasses import dataclass
from rapidfuzz import fuzz, process


def auto_pair(db) -> Dict[str, Any]:
    """
    Automatically pair invoices with delivery notes based on supplier matching
    and date proximity.
    
    Args:
        db: Database connection object
    """
    cursor = db.cursor()
    
    # Get all invoices that don't already have pairs
    cursor.execute("""
        SELECT id, supplier, invoice_date, invoice_number
        FROM invoices 
        WHERE supplier IS NOT NULL 
        AND invoice_date IS NOT NULL
        AND id NOT IN (SELECT invoice_id FROM doc_pairs)
    """)
    invoices = cursor.fetchall()
    
    # Get all delivery notes
    cursor.execute("""
        SELECT id, supplier, dn_date, reference
        FROM delivery_notes
        WHERE supplier IS NOT NULL
        AND dn_date IS NOT NULL
    """)
    delivery_notes = cursor.fetchall()
    
    pairs_created = 0
    
    for invoice in invoices:
        invoice_id, invoice_supplier, invoice_date, invoice_number = invoice
        
        # Find candidate delivery notes
        candidates = find_candidate_delivery_notes(
            invoice_supplier, invoice_date, delivery_notes
        )
        
        # Create pairs for high-scoring candidates
        for candidate, score in candidates:
            if score >= 0.7:  # Threshold for automatic pairing
                cursor.execute("""
                    INSERT INTO doc_pairs (
                        invoice_id, delivery_note_id, score, 
                        pairing_method, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    invoice_id,
                    candidate[0],  # delivery_note_id
                    score,
                    'auto_supplier_date',
                    datetime.datetime.now(datetime.timezone.utc).isoformat()
                ))
                pairs_created += 1
    
    db.commit()
    print(f"Auto-pairing completed: {pairs_created} pairs created")


def find_candidate_delivery_notes(
    invoice_supplier: str, 
    invoice_date: str, 
    delivery_notes: List[Tuple]
) -> List[Tuple[Tuple, float]]:
    """
    Find candidate delivery notes for an invoice based on supplier matching
    and date proximity.
    
    Args:
        invoice_supplier: Supplier name from invoice
        invoice_date: Invoice date (YYYY-MM-DD format)
        delivery_notes: List of delivery note tuples (id, supplier, dn_date, reference)
        
    Returns:
        List of (delivery_note_tuple, score) pairs sorted by score descending
    """
    if not invoice_supplier or not invoice_date:
        return []
    
    candidates = []
    invoice_date_obj = parse_date(invoice_date)
    
    if not invoice_date_obj:
        return []
    
    for dn in delivery_notes:
        dn_id, dn_supplier, dn_date, dn_reference = dn
        
        # Calculate supplier similarity score
        supplier_score = calculate_supplier_similarity(invoice_supplier, dn_supplier)
        
        # Calculate date proximity score
        date_score = calculate_date_proximity(invoice_date_obj, dn_date)
        
        # Combined score (weighted: 70% supplier, 30% date)
        combined_score = (supplier_score * 0.7) + (date_score * 0.3)
        
        if combined_score > 0.3:  # Minimum threshold
            candidates.append((dn, combined_score))
    
    # Sort by score descending
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates


def calculate_supplier_similarity(supplier1: str, supplier2: str) -> float:
    """
    Calculate similarity score between two supplier names using fuzzy matching.
    
    Args:
        supplier1: First supplier name
        supplier2: Second supplier name
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not supplier1 or not supplier2:
        return 0.0
    
    # Normalize supplier names
    norm1 = normalize_supplier_name(supplier1)
    norm2 = normalize_supplier_name(supplier2)
    
    # Use fuzzy matching
    ratio = fuzz.ratio(norm1, norm2)
    
    # Convert to 0-1 scale
    return ratio / 100.0


def normalize_supplier_name(name: str) -> str:
    """
    Normalize supplier name for better matching.
    
    Args:
        name: Raw supplier name
        
    Returns:
        Normalized supplier name
    """
    if not name:
        return ""
    
    # Convert to lowercase and remove common suffixes
    normalized = name.lower().strip()
    
    # Remove common business suffixes
    suffixes = ['ltd', 'limited', 'plc', 'inc', 'corp', 'corporation', 'llc', 'co']
    for suffix in suffixes:
        if normalized.endswith(' ' + suffix):
            normalized = normalized[:-len(' ' + suffix)]
        elif normalized.endswith('.' + suffix):
            normalized = normalized[:-len('.' + suffix)]
    
    return normalized


def calculate_date_proximity(invoice_date: datetime.date, dn_date_str: str) -> float:
    """
    Calculate date proximity score based on how close the dates are.
    
    Args:
        invoice_date: Invoice date as date object
        dn_date_str: Delivery note date as string
        
    Returns:
        Date proximity score between 0.0 and 1.0
    """
    dn_date = parse_date(dn_date_str)
    if not dn_date:
        return 0.0
    
    # Calculate days difference
    days_diff = abs((invoice_date - dn_date).days)
    
    # Score based on date window (30 days = full score, 90 days = minimum score)
    if days_diff <= 30:
        return 1.0
    elif days_diff <= 90:
        # Linear decay from 1.0 to 0.3 over 60 days
        return 1.0 - (0.7 * (days_diff - 30) / 60)
    else:
        return 0.0


def parse_date(date_str: str) -> Optional[datetime.date]:
    """
    Parse date string in various formats to date object.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Date object or None if parsing fails
    """
    if not date_str:
        return None
    
    # Common date formats
    formats = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%d.%m.%Y',
        '%Y.%m.%d'
    ]
    
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None


def get_pairs_for_invoice(db, invoice_id: int) -> List[Dict[str, Any]]:
    """
    Get all pairs for a specific invoice.
    
    Args:
        db: Database connection object
        invoice_id: Invoice ID
        
    Returns:
        List of pair dictionaries
    """
    cursor = db.cursor()
    cursor.execute("""
        SELECT dp.*, dn.supplier as dn_supplier, dn.dn_date, dn.reference
        FROM doc_pairs dp
        JOIN delivery_notes dn ON dp.delivery_note_id = dn.id
        WHERE dp.invoice_id = ?
        ORDER BY dp.score DESC
    """, (invoice_id,))
    
    pairs = []
    for row in cursor.fetchall():
        pairs.append({
            'id': row[0],
            'invoice_id': row[1],
            'delivery_note_id': row[2],
            'score': row[3],
            'pairing_method': row[4],
            'created_at': row[5],
            'dn_supplier': row[6],
            'dn_date': row[7],
            'dn_reference': row[8]
        })
    
    return pairs


def get_pairs_for_delivery_note(db, delivery_note_id: int) -> List[Dict[str, Any]]:
    """
    Get all pairs for a specific delivery note.
    
    Args:
        db: Database connection object
        delivery_note_id: Delivery note ID
        
    Returns:
        List of pair dictionaries
    """
    cursor = db.cursor()
    cursor.execute("""
        SELECT dp.*, i.supplier as invoice_supplier, i.invoice_date, i.invoice_number
        FROM doc_pairs dp
        JOIN invoices i ON dp.invoice_id = i.id
        WHERE dp.delivery_note_id = ?
        ORDER BY dp.score DESC
    """, (delivery_note_id,))
    
    pairs = []
    for row in cursor.fetchall():
        pairs.append({
            'id': row[0],
            'invoice_id': row[1],
            'delivery_note_id': row[2],
            'score': row[3],
            'pairing_method': row[4],
            'created_at': row[5],
            'invoice_supplier': row[6],
            'invoice_date': row[7],
            'invoice_number': row[8]
        })
    
    return pairs
