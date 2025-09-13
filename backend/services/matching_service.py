"""
Matching Service

Core matching engine for pairing invoices with delivery notes.
Implements deterministic algorithm with confidence scoring and explainability.
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import uuid4
import difflib

from contracts import MatchingPair, LineDiff, MatchReason, MatchingSummary
from services.matching_config import get_matching_config, normalize_uom, convert_quantity

DB_PATH = os.path.join("data", "owlin.db")

def get_conn() -> sqlite3.Connection:
    """Get database connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def _parse_line_items(line_items_json: str) -> List[Dict[str, Any]]:
    """Parse line items from JSON string."""
    if not line_items_json:
        return []
    try:
        return json.loads(line_items_json)
    except (json.JSONDecodeError, TypeError):
        return []

def _normalize_sku(sku: str) -> str:
    """Normalize SKU code."""
    if not sku:
        return ""
    return sku.upper().replace(" ", "").replace("-", "")

def _normalize_description(desc: str) -> str:
    """Normalize description for fuzzy matching."""
    if not desc:
        return ""
    # Remove punctuation, lowercase, collapse whitespace
    import re
    desc = re.sub(r'[^\w\s]', ' ', desc.lower())
    desc = ' '.join(desc.split())
    return desc

def _fuzzy_similarity(str1: str, str2: str) -> float:
    """Calculate fuzzy similarity using Jaro-Winkler."""
    if not str1 or not str2:
        return 0.0
    return difflib.SequenceMatcher(None, str1, str2).ratio()

def _calculate_document_score(reasons: List[MatchReason]) -> float:
    """Calculate document-level confidence score."""
    base_score = 50.0
    for reason in reasons:
        base_score += reason.weight
    return max(0.0, min(100.0, base_score))

def _find_candidate_dns(invoice_id: str, config: Any) -> List[Dict[str, Any]]:
    """Find candidate delivery notes for an invoice."""
    conn = get_conn()
    cursor = conn.cursor()
    
    # Get invoice details
    cursor.execute("""
        SELECT supplier_name, invoice_date, total_amount, line_items
        FROM invoices WHERE id = ?
    """, (invoice_id,))
    invoice_row = cursor.fetchone()
    if not invoice_row:
        conn.close()
        return []
    
    supplier_name, invoice_date, invoice_total, line_items_json = invoice_row
    
    # Find DNs within date window and same supplier
    date_window = config.date_window_days
    cursor.execute("""
        SELECT id, delivery_date, total_amount
        FROM delivery_notes 
        WHERE supplier_name = ? 
        AND delivery_date BETWEEN DATE(?, '-{} days') AND DATE(?, '+{} days')
        ORDER BY delivery_date
    """.format(date_window, date_window), (supplier_name, invoice_date, invoice_date))
    
    candidates = []
    for row in cursor.fetchall():
        dn_id, dn_date, dn_total = row
        
        # Calculate provisional score
        reasons = []
        score = 0.0
        
        # Date window match
        if dn_date:
            try:
                inv_date = datetime.strptime(invoice_date, "%Y-%m-%d")
                dn_date_obj = datetime.strptime(dn_date, "%Y-%m-%d")
                days_diff = abs((inv_date - dn_date_obj).days)
                if days_diff <= config.date_window_days:
                    reasons.append(MatchReason(
                        code="DATE_WINDOW_MATCH",
                        detail=f"DN {dn_date} is within {days_diff} days of INV {invoice_date}",
                        weight=10.0
                    ))
                    score += 10.0
            except (ValueError, TypeError):
                pass
        
        # Supplier match
        reasons.append(MatchReason(
            code="SUPPLIER_MATCH",
            detail=f"Both documents from {supplier_name}",
            weight=15.0
        ))
        score += 15.0
        
        # Amount proximity
        if invoice_total and dn_total and invoice_total > 0:
            amount_diff_pct = abs(dn_total - invoice_total) / invoice_total
            if amount_diff_pct <= config.amount_proximity_pct:
                reasons.append(MatchReason(
                    code="AMOUNT_PROXIMITY_<=10PCT",
                    detail=f"Amount difference {amount_diff_pct:.1%} within tolerance",
                    weight=10.0
                ))
                score += 10.0
        
        # SKU overlap - simplified since we don't have line_items in delivery_notes
        # For now, we'll skip this check and rely on other factors
        candidates.append({
            'id': dn_id,
            'score': score,
            'reasons': reasons,
            'date': dn_date,
            'total': dn_total,
            'line_items': '[]'  # Empty JSON array since we don't have line_items
        })
    
    conn.close()
    return sorted(candidates, key=lambda x: x['score'], reverse=True)

def _match_line_items(inv_items: List[Dict], dn_items: List[Dict], config: Any) -> List[LineDiff]:
    """Match line items between invoice and delivery note."""
    line_diffs = []
    
    # Normalize items
    inv_normalized = []
    for i, item in enumerate(inv_items):
        inv_normalized.append({
            'index': i,
            'sku': _normalize_sku(item.get('sku', '')),
            'description': _normalize_description(item.get('description', '')),
            'qty': float(item.get('quantity', 0)),
            'uom': normalize_uom(item.get('unit', 'each')),
            'price': float(item.get('unit_price', 0)),
            'original': item
        })
    
    dn_normalized = []
    for i, item in enumerate(dn_items):
        dn_normalized.append({
            'index': i,
            'sku': _normalize_sku(item.get('sku', '')),
            'description': _normalize_description(item.get('description', '')),
            'qty': float(item.get('quantity', 0)),
            'uom': normalize_uom(item.get('unit', 'each')),
            'price': float(item.get('unit_price', 0)),
            'original': item
        })
    
    # First pass: exact SKU + UOM match
    matched_inv = set()
    matched_dn = set()
    
    for inv_item in inv_normalized:
        for dn_item in dn_normalized:
            if (inv_item['index'] not in matched_inv and 
                dn_item['index'] not in matched_dn and
                inv_item['sku'] and dn_item['sku'] and
                inv_item['sku'] == dn_item['sku'] and
                inv_item['uom'] == dn_item['uom']):
                
                # Check quantity and price tolerances
                qty_diff = abs(inv_item['qty'] - dn_item['qty'])
                qty_tol = max(config.qty_tol_abs, inv_item['qty'] * config.qty_tol_rel)
                
                price_diff = abs(inv_item['price'] - dn_item['price'])
                price_tol = inv_item['price'] * config.price_tol_rel
                
                reasons = [MatchReason(
                    code="SKU_EXACT_MATCH",
                    detail=f"Exact SKU match: {inv_item['sku']}",
                    weight=20.0
                )]
                
                status = "ok"
                confidence = 90.0
                
                if qty_diff > qty_tol:
                    status = "qty_mismatch"
                    confidence -= 15.0
                    reasons.append(MatchReason(
                        code="QTY_OUT_OF_TOL",
                        detail=f"Quantity difference {qty_diff:.2f} exceeds tolerance {qty_tol:.2f}",
                        weight=-10.0
                    ))
                
                if price_diff > price_tol:
                    status = "price_mismatch"
                    confidence -= 15.0
                    reasons.append(MatchReason(
                        code="PRICE_OUT_OF_TOL",
                        detail=f"Price difference {price_diff:.2f} exceeds tolerance {price_tol:.2f}",
                        weight=-10.0
                    ))
                
                line_diffs.append(LineDiff(
                    id=f"line_{uuid4().hex[:8]}",
                    invoice_line_id=inv_item['index'],
                    delivery_line_id=dn_item['index'],
                    status=status,
                    confidence=confidence,
                    qty_invoice=inv_item['qty'],
                    qty_dn=dn_item['qty'],
                    qty_uom=inv_item['uom'],
                    price_invoice=inv_item['price'],
                    price_dn=dn_item['price'],
                    reasons=reasons
                ))
                
                matched_inv.add(inv_item['index'])
                matched_dn.add(dn_item['index'])
                break
    
    # Second pass: same SKU, different UOM but convertible
    for inv_item in inv_normalized:
        if inv_item['index'] in matched_inv:
            continue
            
        for dn_item in dn_normalized:
            if dn_item['index'] in matched_dn:
                continue
                
            if (inv_item['sku'] and dn_item['sku'] and
                inv_item['sku'] == dn_item['sku'] and
                inv_item['uom'] != dn_item['uom']):
                
                # Try conversion
                converted_qty = convert_quantity(dn_item['qty'], dn_item['uom'], inv_item['uom'])
                if converted_qty != dn_item['qty']:  # Conversion was possible
                    qty_diff = abs(inv_item['qty'] - converted_qty)
                    qty_tol = max(config.qty_tol_abs, inv_item['qty'] * config.qty_tol_rel)
                    
                    status = "ok" if qty_diff <= qty_tol else "qty_mismatch"
                    confidence = 85.0 if qty_diff <= qty_tol else 70.0
                    
                    reasons = [
                        MatchReason(
                            code="SKU_EXACT_MATCH",
                            detail=f"Exact SKU match: {inv_item['sku']}",
                            weight=20.0
                        ),
                        MatchReason(
                            code="UOM_CONVERTED",
                            detail=f"Converted {dn_item['uom']}→{inv_item['uom']}",
                            weight=6.0
                        )
                    ]
                    
                    if qty_diff > qty_tol:
                        reasons.append(MatchReason(
                            code="QTY_OUT_OF_TOL",
                            detail=f"Quantity difference {qty_diff:.2f} exceeds tolerance {qty_tol:.2f}",
                            weight=-10.0
                        ))
                    
                    line_diffs.append(LineDiff(
                        id=f"line_{uuid4().hex[:8]}",
                        invoice_line_id=inv_item['index'],
                        delivery_line_id=dn_item['index'],
                        status=status,
                        confidence=confidence,
                        qty_invoice=inv_item['qty'],
                        qty_dn=converted_qty,
                        qty_uom=inv_item['uom'],
                        price_invoice=inv_item['price'],
                        price_dn=dn_item['price'],
                        reasons=reasons
                    ))
                    
                    matched_inv.add(inv_item['index'])
                    matched_dn.add(dn_item['index'])
                    break
    
    # Third pass: fuzzy description match
    for inv_item in inv_normalized:
        if inv_item['index'] in matched_inv:
            continue
            
        best_match = None
        best_similarity = 0.0
        
        for dn_item in dn_normalized:
            if dn_item['index'] in matched_dn:
                continue
                
            if inv_item['description'] and dn_item['description']:
                similarity = _fuzzy_similarity(inv_item['description'], dn_item['description'])
                if similarity >= config.fuzzy_desc_threshold and similarity > best_similarity:
                    best_match = dn_item
                    best_similarity = similarity
        
        if best_match:
            # Check price proximity
            price_diff_pct = abs(inv_item['price'] - best_match['price']) / inv_item['price']
            if price_diff_pct <= config.price_tol_rel:
                reasons = [
                    MatchReason(
                        code="DESC_FUZZY_≥0.90",
                        detail=f"Description similarity {best_similarity:.2f}",
                        weight=6.0
                    )
                ]
                
                line_diffs.append(LineDiff(
                    id=f"line_{uuid4().hex[:8]}",
                    invoice_line_id=inv_item['index'],
                    delivery_line_id=best_match['index'],
                    status="ok",
                    confidence=75.0,
                    qty_invoice=inv_item['qty'],
                    qty_dn=best_match['qty'],
                    qty_uom=inv_item['uom'],
                    price_invoice=inv_item['price'],
                    price_dn=best_match['price'],
                    reasons=reasons
                ))
                
                matched_inv.add(inv_item['index'])
                matched_dn.add(best_match['index'])
    
    # Add unmatched items
    for inv_item in inv_normalized:
        if inv_item['index'] not in matched_inv:
            line_diffs.append(LineDiff(
                id=f"line_{uuid4().hex[:8]}",
                invoice_line_id=inv_item['index'],
                delivery_line_id=None,
                status="missing_on_dn",
                confidence=0.0,
                qty_invoice=inv_item['qty'],
                qty_dn=None,
                qty_uom=inv_item['uom'],
                price_invoice=inv_item['price'],
                price_dn=None,
                reasons=[MatchReason(
                    code="MISSING_ON_DN",
                    detail="Item not found on delivery note",
                    weight=-20.0
                )]
            ))
    
    for dn_item in dn_normalized:
        if dn_item['index'] not in matched_dn:
            line_diffs.append(LineDiff(
                id=f"line_{uuid4().hex[:8]}",
                invoice_line_id=None,
                delivery_line_id=dn_item['index'],
                status="missing_on_inv",
                confidence=0.0,
                qty_invoice=None,
                qty_dn=dn_item['qty'],
                qty_uom=dn_item['uom'],
                price_invoice=None,
                price_dn=dn_item['price'],
                reasons=[MatchReason(
                    code="MISSING_ON_INV",
                    detail="Item not found on invoice",
                    weight=-20.0
                )]
            ))
    
    return line_diffs

def compute_matching_pair(invoice_id: str, delivery_note_id: str) -> MatchingPair:
    """Compute matching pair between invoice and delivery note."""
    config = get_matching_config()
    conn = get_conn()
    cursor = conn.cursor()
    
    # Get invoice details
    cursor.execute("""
        SELECT supplier_name, invoice_date, total_amount, line_items
        FROM invoices WHERE id = ?
    """, (invoice_id,))
    invoice_row = cursor.fetchone()
    
    # Get delivery note details
    cursor.execute("""
        SELECT supplier_name, delivery_date, total_amount, line_items
        FROM delivery_notes WHERE id = ?
    """, (delivery_note_id,))
    dn_row = cursor.fetchone()
    
    if not invoice_row or not dn_row:
        conn.close()
        raise ValueError("Invoice or delivery note not found")
    
    inv_supplier, inv_date, inv_total, inv_line_items_json = invoice_row
    dn_supplier, dn_date, dn_total, dn_line_items_json = dn_row
    
    # Parse line items
    inv_items = _parse_line_items(inv_line_items_json)
    dn_items = _parse_line_items(dn_line_items_json)
    
    # Match line items
    line_diffs = _match_line_items(inv_items, dn_items, config)
    
    # Calculate document-level confidence and status
    all_reasons = []
    line_coverage = 0
    mismatch_lines = 0
    
    for line_diff in line_diffs:
        all_reasons.extend(line_diff.reasons)
        if line_diff.invoice_line_id is not None:
            line_coverage += 1
        if line_diff.status in ["qty_mismatch", "price_mismatch"]:
            mismatch_lines += 1
    
    # Add document-level reasons
    if inv_supplier == dn_supplier:
        all_reasons.append(MatchReason(
            code="SUPPLIER_MATCH",
            detail=f"Both documents from {inv_supplier}",
            weight=15.0
        ))
    
    if inv_date and dn_date:
        try:
            inv_date_obj = datetime.strptime(inv_date, "%Y-%m-%d")
            dn_date_obj = datetime.strptime(dn_date, "%Y-%m-%d")
            days_diff = abs((inv_date_obj - dn_date_obj).days)
            if days_diff <= config.date_window_days:
                all_reasons.append(MatchReason(
                    code="DATE_WINDOW_MATCH",
                    detail=f"DN {dn_date} is within {days_diff} days of INV {inv_date}",
                    weight=10.0
                ))
        except (ValueError, TypeError):
            pass
    
    if inv_total and dn_total and inv_total > 0:
        amount_diff_pct = abs(dn_total - inv_total) / inv_total
        if amount_diff_pct <= config.amount_proximity_pct:
            all_reasons.append(MatchReason(
                code="AMOUNT_PROXIMITY_<=10PCT",
                detail=f"Amount difference {amount_diff_pct:.1%} within tolerance",
                weight=10.0
            ))
    
    # Calculate coverage percentages
    total_inv_lines = len([d for d in line_diffs if d.invoice_line_id is not None])
    coverage_pct = line_coverage / total_inv_lines if total_inv_lines > 0 else 0
    mismatch_pct = mismatch_lines / total_inv_lines if total_inv_lines > 0 else 0
    
    # Add coverage-based reasons
    if coverage_pct < 0.7:
        all_reasons.append(MatchReason(
            code="LOW_LINE_COVERAGE_<70PCT",
            detail=f"Only {coverage_pct:.0%} of invoice lines matched",
            weight=-20.0
        ))
    
    if mismatch_pct > 0.3:
        all_reasons.append(MatchReason(
            code="MANY_MISMATCHES_>30PCT",
            detail=f"{mismatch_pct:.0%} of matched lines have discrepancies",
            weight=-20.0
        ))
    
    # Calculate overall confidence
    confidence = _calculate_document_score(all_reasons)
    
    # Determine status
    if coverage_pct >= 0.9 and mismatch_pct <= 0.05 and confidence >= 75:
        status = "matched"
    elif coverage_pct >= 0.6 or confidence >= 60:
        status = "partial"
    else:
        status = "unmatched"
    
    conn.close()
    
    return MatchingPair(
        id=f"pair_{uuid4().hex[:8]}",
        invoice_id=int(invoice_id),
        delivery_note_id=int(delivery_note_id),
        status=status,
        confidence=confidence,
        reasons=all_reasons,
        line_diffs=line_diffs
    )

def rebuild_matching(days: int = 14) -> Dict[str, Any]:
    """Rebuild matching for all invoices in the specified date window."""
    config = get_matching_config()
    conn = get_conn()
    cursor = conn.cursor()
    
    # Clear existing matches
    cursor.execute("DELETE FROM match_links")
    cursor.execute("DELETE FROM match_line_links")
    
    # Get invoices in date window
    cursor.execute("""
        SELECT id, supplier_name, invoice_date, total_amount, line_items
        FROM invoices 
        WHERE invoice_date >= DATE('now', '-{} days')
        ORDER BY invoice_date DESC
    """.format(days))
    
    invoices = cursor.fetchall()
    pairs_created = 0
    
    for invoice_row in invoices:
        invoice_id, supplier_name, invoice_date, total_amount, line_items_json = invoice_row
        
        # Find candidate DNs
        candidates = _find_candidate_dns(invoice_id, config)
        
        if not candidates:
            continue
        
        # Check for ties
        if len(candidates) > 1 and candidates[0]['score'] - candidates[1]['score'] <= 5:
            # Tie - mark as conflict
            best_candidate = candidates[0]
            best_candidate['reasons'].append(MatchReason(
                code="MULTI_CANDIDATE_TIE",
                detail=f"Multiple candidates within 5 points: {candidates[0]['score']} vs {candidates[1]['score']}",
                weight=-15.0
            ))
        
        # Use best candidate
        best_candidate = candidates[0]
        
        # Compute full matching pair
        try:
            pair = compute_matching_pair(invoice_id, best_candidate['id'])
            
            # Store in database
            pair_id = pair.id
            cursor.execute("""
                INSERT INTO match_links (id, invoice_id, delivery_note_id, confidence, status, reasons_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                pair_id,
                invoice_id,
                best_candidate['id'],
                pair.confidence,
                pair.status,
                json.dumps([r.dict() for r in pair.reasons])
            ))
            
            # Store line diffs
            for line_diff in pair.line_diffs:
                cursor.execute("""
                    INSERT INTO match_line_links (id, match_link_id, invoice_line_id, delivery_line_id, 
                                                qty_delta, price_delta, confidence, status, reasons_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    line_diff.id,
                    pair_id,
                    line_diff.invoice_line_id,
                    line_diff.delivery_line_id,
                    line_diff.qty_invoice - line_diff.qty_dn if line_diff.qty_invoice and line_diff.qty_dn else None,
                    line_diff.price_invoice - line_diff.price_dn if line_diff.price_invoice and line_diff.price_dn else None,
                    line_diff.confidence,
                    line_diff.status,
                    json.dumps([r.dict() for r in line_diff.reasons])
                ))
            
            pairs_created += 1
            
        except Exception as e:
            print(f"Error matching invoice {invoice_id}: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    return {
        "pairs_created": pairs_created,
        "invoices_processed": len(invoices),
        "date_window_days": days
    }

def get_matching_summary(state: str = "all", limit: int = 50, offset: int = 0) -> MatchingSummary:
    """Get matching summary with optional filtering."""
    conn = get_conn()
    cursor = conn.cursor()
    
    # Build query
    where_clause = ""
    if state != "all":
        where_clause = f"WHERE status = '{state}'"
    
    # Get totals
    cursor.execute(f"SELECT status, COUNT(*) FROM match_links {where_clause} GROUP BY status")
    totals = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Get pairs
    cursor.execute(f"""
        SELECT id, invoice_id, delivery_note_id, confidence, status, reasons_json
        FROM match_links {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    pairs = []
    for row in cursor.fetchall():
        pair_id, invoice_id, dn_id, confidence, status, reasons_json = row
        
        # Get line diffs
        cursor.execute("""
            SELECT id, invoice_line_id, delivery_line_id, qty_delta, price_delta, 
                   confidence, status, reasons_json
            FROM match_line_links WHERE match_link_id = ?
        """, (pair_id,))
        
        line_diffs = []
        for line_row in cursor.fetchall():
            line_id, inv_line_id, dn_line_id, qty_delta, price_delta, line_conf, line_status, line_reasons_json = line_row
            
            line_diffs.append(LineDiff(
                id=line_id,
                invoice_line_id=inv_line_id,
                delivery_line_id=dn_line_id,
                status=line_status,
                confidence=line_conf,
                qty_invoice=None,  # Would need to fetch from line items
                qty_dn=None,
                qty_uom=None,
                price_invoice=None,
                price_dn=None,
                reasons=[MatchReason(**r) for r in json.loads(line_reasons_json)]
            ))
        
        pairs.append(MatchingPair(
            id=pair_id,
            invoice_id=int(invoice_id),
            delivery_note_id=int(dn_id),
            status=status,
            confidence=confidence,
            reasons=[MatchReason(**r) for r in json.loads(reasons_json)],
            line_diffs=line_diffs
        ))
    
    conn.close()
    
    return MatchingSummary(totals=totals, pairs=pairs) 