# backend/services/pairing_service.py
"""
Document pairing service for matching invoices with delivery notes
"""

import re
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from db_manager_unified import get_db_manager
from backend.normalization.units import canonical_quantities

logger = logging.getLogger(__name__)

# Get unified database manager
db_manager = get_db_manager()

class PairingService:
    """Service for pairing invoices with delivery notes"""
    
    # Deterministic scoring weights (committed in code)
    SCORING_WEIGHTS = {
        'supplier_match': 0.6,
        'date_proximity': 0.2,
        'amount_proximity': 0.2
    }
    
    # Line-level scoring weights
    LINE_SCORING_WEIGHTS = {
        'quantity_match': 0.4,
        'description_similarity': 0.3,
        'price_proximity': 0.2,
        'sku_match': 0.1
    }
    
    # Auto-confirm threshold
    AUTO_CONFIRM_THRESHOLD = 85.0
    SUGGESTION_THRESHOLD = 55.0
    
    # Line matching thresholds
    QUANTITY_TOLERANCE = 0.05  # 5% tolerance for quantity matching
    PRICE_TOLERANCE = 0.10     # 10% tolerance for price matching
    
    @staticmethod
    def normalize_supplier_name(name: str) -> str:
        """Normalize supplier name for comparison"""
        if not name:
            return ""
        
        # Remove common suffixes and prefixes
        name = re.sub(r'\b(ltd|limited|inc|corp|corporation|co|company|plc)\b', '', name.lower())
        name = re.sub(r'[^\w\s]', '', name)  # Remove punctuation
        name = re.sub(r'\s+', ' ', name).strip()  # Normalize whitespace
        
        return name
    
    @staticmethod
    def calculate_supplier_score(invoice_supplier: str, dn_supplier: str) -> float:
        """Calculate supplier name similarity score (0-1)"""
        if not invoice_supplier or not dn_supplier:
            return 0.0
        
        norm_inv = PairingService.normalize_supplier_name(invoice_supplier)
        norm_dn = PairingService.normalize_supplier_name(dn_supplier)
        
        if norm_inv == norm_dn:
            return 1.0
        
        # Use sequence matcher for fuzzy matching
        similarity = SequenceMatcher(None, norm_inv, norm_dn).ratio()
        
        # Boost exact matches and high similarity
        if similarity > 0.8:
            return min(1.0, similarity + 0.1)
        
        return similarity
    
    @staticmethod
    def calculate_date_score(invoice_date: str, dn_date: str) -> float:
        """Calculate date proximity score (0-1)"""
        if not invoice_date or not dn_date:
            return 0.0
        
        try:
            # Parse dates (assuming YYYY-MM-DD format)
            inv_date = datetime.strptime(invoice_date, '%Y-%m-%d')
            dn_date = datetime.strptime(dn_date, '%Y-%m-%d')
            
            # Calculate days difference
            days_diff = abs((inv_date - dn_date).days)
            
            # Score based on proximity (±3 days = 1.0, ±7 days = 0.5, >7 days = 0.0)
            if days_diff <= 3:
                return 1.0
            elif days_diff <= 7:
                return 0.5
            else:
                return max(0.0, 1.0 - (days_diff - 7) * 0.1)
                
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def calculate_amount_score(invoice_amount: float, dn_amount: float) -> float:
        """Calculate amount proximity score (0-1)"""
        if not invoice_amount or not dn_amount or invoice_amount == 0:
            return 0.0
        
        # Calculate percentage difference
        diff_pct = abs(invoice_amount - dn_amount) / invoice_amount
        
        # Score based on percentage difference (±2.5% = 1.0, ±5% = 0.5, >5% = 0.0)
        if diff_pct <= 0.025:
            return 1.0
        elif diff_pct <= 0.05:
            return 0.5
        else:
            return max(0.0, 1.0 - (diff_pct - 0.05) * 10)
    
    @staticmethod
    def calculate_overall_score(supplier_score: float, date_score: float, amount_score: float) -> float:
        """Calculate overall pairing score (0-100) using deterministic weights"""
        weights = PairingService.SCORING_WEIGHTS
        
        overall_score = (
            supplier_score * weights['supplier_match'] +
            date_score * weights['date_proximity'] +
            amount_score * weights['amount_proximity']
        )
        
        return min(100.0, overall_score * 100)
    
    @staticmethod
    def get_pairing_suggestions(limit: int = 10, db_conn=None):
        """Get all pairing suggestions with scores"""
        try:
            if db_conn is None:
                with db_manager.get_connection() as conn:
                    return PairingService._get_pairing_suggestions_internal(conn, limit)
            else:
                return PairingService._get_pairing_suggestions_internal(db_conn, limit)
                
        except Exception as e:
            logger.error(f"Error getting pairing suggestions: {e}")
            return []
    
    @staticmethod
    def _get_pairing_suggestions_internal(conn, limit: int = 10):
        """Internal method for getting pairing suggestions"""
        # Get unmatched invoices and delivery notes
        invoices = conn.execute("""
            SELECT id, supplier_name, invoice_date, total_amount_pennies
            FROM invoices 
            WHERE paired = 0
            ORDER BY created_at DESC
        """).fetchall()
        
        delivery_notes = conn.execute("""
            SELECT id, supplier_name, delivery_date, total_items
            FROM delivery_notes 
            WHERE matched_invoice_id IS NULL
            ORDER BY created_at DESC
        """).fetchall()
        
        suggestions = []
        
        for inv in invoices:
            for dn in delivery_notes:
                # Calculate individual scores
                supplier_score = PairingService.calculate_supplier_score(
                    inv['supplier_name'], dn['supplier_name']
                )
                
                date_score = PairingService.calculate_date_score(
                    inv['invoice_date'], dn['delivery_date']
                )
                
                amount_score = PairingService.calculate_amount_score(
                    inv['total_amount_pennies'] / 100 if inv['total_amount_pennies'] else 0,
                    dn['total_items'] if dn['total_items'] else 0
                )
                
                # Calculate overall score
                overall_score = PairingService.calculate_overall_score(
                    supplier_score, date_score, amount_score
                )
                
                # Only include if score is above suggestion threshold
                if overall_score >= PairingService.SUGGESTION_THRESHOLD:
                    reasons = []
                    if supplier_score > 0.8:
                        reasons.append(f"Strong supplier match ({supplier_score:.2f})")
                    if date_score > 0.5:
                        reasons.append(f"Close delivery date ({date_score:.2f})")
                    if amount_score > 0.5:
                        reasons.append(f"Similar amount ({amount_score:.2f})")
                    
                    suggestions.append({
                        'delivery_note_id': dn['id'],
                        'invoice_id': inv['id'],
                        'score': int(overall_score),
                        'reasons': reasons
                    })
        
        # Sort by score and return top limit
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:limit]
    
    @staticmethod
    def confirm_pairing(delivery_note_id: str, invoice_id: str, db_conn=None):
        """Confirm pairing between delivery note and invoice"""
        try:
            if db_conn is None:
                with db_manager.get_connection() as conn:
                    return PairingService._confirm_pairing_internal(delivery_note_id, invoice_id, conn)
            else:
                return PairingService._confirm_pairing_internal(delivery_note_id, invoice_id, db_conn)
                
        except Exception as e:
            logger.error(f"Error confirming pairing: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _confirm_pairing_internal(delivery_note_id: str, invoice_id: str, conn):
        """Internal method for confirming pairing"""
        # Get the documents
        dn = conn.execute("""
            SELECT id, supplier_name, delivery_date, total_items
            FROM delivery_notes WHERE id = ?
        """, (delivery_note_id,)).fetchone()
        
        inv = conn.execute("""
            SELECT id, supplier_name, invoice_date, total_amount_pennies
            FROM invoices WHERE id = ?
        """, (invoice_id,)).fetchone()
        
        if not dn or not inv:
            return {"error": "Document not found"}
        
        # Calculate score
        supplier_score = PairingService.calculate_supplier_score(
            inv['supplier_name'], dn['supplier_name']
        )
        date_score = PairingService.calculate_date_score(
            inv['invoice_date'], dn['delivery_date']
        )
        amount_score = PairingService.calculate_amount_score(
            inv['total_amount_pennies'] / 100 if inv['total_amount_pennies'] else 0,
            dn['total_items'] if dn['total_items'] else 0
        )
        overall_score = PairingService.calculate_overall_score(
            supplier_score, date_score, amount_score
        )
        
        # Update both documents
        conn.execute("""
            UPDATE delivery_notes 
            SET matched_invoice_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (invoice_id, delivery_note_id))
        
        conn.execute("""
            UPDATE invoices 
            SET paired = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (invoice_id,))
        
        # Create audit log entry
        conn.execute("""
            INSERT INTO audit_log (timestamp, action, entity_type, entity_id, metadata_json)
            VALUES (CURRENT_TIMESTAMP, 'pairing_confirmed', 'delivery_note', ?, ?)
        """, (delivery_note_id, json.dumps({
            'invoice_id': invoice_id,
            'score': overall_score,
            'supplier_score': supplier_score,
            'date_score': date_score,
            'amount_score': amount_score
        })))
        
        conn.commit()
        
        logger.info(f"Confirmed pairing: {delivery_note_id} ↔ {invoice_id} (score: {overall_score})")
        
        return {
            "delivery_note_id": delivery_note_id,
            "invoice_id": invoice_id,
            "score": int(overall_score),
            "matched": True
        }
    
    @staticmethod
    def reject_pairing(suggestion_id: str, db_conn=None):
        """Reject a pairing suggestion"""
        try:
            if db_conn is None:
                with db_manager.get_connection() as conn:
                    return PairingService._reject_pairing_internal(suggestion_id, conn)
            else:
                return PairingService._reject_pairing_internal(suggestion_id, db_conn)
                
        except Exception as e:
            logger.error(f"Error rejecting pairing: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _reject_pairing_internal(suggestion_id: str, conn):
        """Internal method for rejecting pairing"""
        # Create audit log entry
        conn.execute("""
            INSERT INTO audit_log (timestamp, action, entity_type, entity_id, metadata_json)
            VALUES (CURRENT_TIMESTAMP, 'pairing_rejected', 'suggestion', ?, ?)
        """, (suggestion_id, json.dumps({'reason': 'manual_rejection'})))
        
        conn.commit()
        
        return {
            "suggestion_id": suggestion_id,
            "rejected": True
        }
    
    @staticmethod
    def auto_pair_high_confidence(db_conn=None):
        """Auto-pair documents with high confidence scores"""
        try:
            if db_conn is None:
                with db_manager.get_connection() as conn:
                    return PairingService._auto_pair_high_confidence_internal(conn)
            else:
                return PairingService._auto_pair_high_confidence_internal(db_conn)
                
        except Exception as e:
            logger.error(f"Error in auto-pairing: {e}")
            return []
    
    @staticmethod
    def _auto_pair_high_confidence_internal(conn):
        """Internal method for auto-pairing"""
        suggestions = PairingService._get_pairing_suggestions_internal(conn, limit=100)
        auto_paired = []
        
        for suggestion in suggestions:
            if suggestion['score'] >= PairingService.AUTO_CONFIRM_THRESHOLD:
                result = PairingService._confirm_pairing_internal(
                    suggestion['delivery_note_id'], 
                    suggestion['invoice_id'],
                    conn
                )
                if "error" not in result:
                    auto_paired.append(result)
        
        logger.info(f"Auto-paired {len(auto_paired)} documents")
        return auto_paired 

    def pair_line_items(self, invoice_lines: List[Dict[str, Any]], 
                       delivery_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Pair line items between invoice and delivery note using canonical quantities.
        
        Args:
            invoice_lines: List of invoice line items
            delivery_lines: List of delivery note line items
            
        Returns:
            List of pairing results with scores and reasons
        """
        try:
            pairings = []
            
            for inv_line in invoice_lines:
                best_match = None
                best_score = 0.0
                best_reasons = []
                
                for dn_line in delivery_lines:
                    score, reasons = self._calculate_line_match_score(inv_line, dn_line)
                    
                    if score > best_score:
                        best_score = score
                        best_match = dn_line
                        best_reasons = reasons
                
                if best_match and best_score > 0.3:  # Minimum threshold
                    pairings.append({
                        'invoice_line': inv_line,
                        'delivery_line': best_match,
                        'score': best_score,
                        'reasons': best_reasons
                    })
            
            return pairings
            
        except Exception as e:
            logger.error(f"❌ Line pairing failed: {e}")
            return []
    
    def _calculate_line_match_score(self, inv_line: Dict[str, Any], 
                                  dn_line: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Calculate match score between two line items"""
        try:
            reasons = []
            total_score = 0.0
            
            # Quantity matching using canonical quantities
            qty_score, qty_reasons = self._match_quantities(inv_line, dn_line)
            total_score += qty_score * self.LINE_SCORING_WEIGHTS['quantity_match']
            reasons.extend(qty_reasons)
            
            # Description similarity
            desc_score, desc_reasons = self._match_descriptions(inv_line, dn_line)
            total_score += desc_score * self.LINE_SCORING_WEIGHTS['description_similarity']
            reasons.extend(desc_reasons)
            
            # Price proximity
            price_score, price_reasons = self._match_prices(inv_line, dn_line)
            total_score += price_score * self.LINE_SCORING_WEIGHTS['price_proximity']
            reasons.extend(price_reasons)
            
            # SKU matching
            sku_score, sku_reasons = self._match_skus(inv_line, dn_line)
            total_score += sku_score * self.LINE_SCORING_WEIGHTS['sku_match']
            reasons.extend(sku_reasons)
            
            return total_score, reasons
            
        except Exception as e:
            logger.error(f"❌ Line match score calculation failed: {e}")
            return 0.0, []
    
    def _match_quantities(self, inv_line: Dict[str, Any], 
                         dn_line: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Match quantities using canonical units"""
        try:
            reasons = []
            
            # Get canonical quantities
            inv_qty = inv_line.get('quantity', 0)
            inv_desc = inv_line.get('description', '')
            inv_canonical = canonical_quantities(inv_qty, inv_desc)
            
            dn_qty = dn_line.get('quantity', 0)
            dn_desc = dn_line.get('description', '')
            dn_canonical = canonical_quantities(dn_qty, dn_desc)
            
            # Prefer quantity_ml for beverages, quantity_g for weights, else quantity_each
            inv_primary = (inv_canonical.get('quantity_ml') or 
                          inv_canonical.get('quantity_g') or 
                          inv_canonical.get('quantity_each', 0))
            dn_primary = (dn_canonical.get('quantity_ml') or 
                         dn_canonical.get('quantity_g') or 
                         dn_canonical.get('quantity_each', 0))
            
            if inv_primary == 0 or dn_primary == 0:
                return 0.0, ["No comparable quantities"]
            
            # Calculate difference
            diff_pct = abs(inv_primary - dn_primary) / max(inv_primary, dn_primary)
            
            if diff_pct <= self.QUANTITY_TOLERANCE:
                score = 1.0 - (diff_pct / self.QUANTITY_TOLERANCE)
                reasons.append(f"Quantity match: {diff_pct:.1%} difference")
                return score, reasons
            else:
                reasons.append(f"Quantity mismatch: {diff_pct:.1%} difference")
                return 0.0, reasons
                
        except Exception as e:
            logger.error(f"❌ Quantity matching failed: {e}")
            return 0.0, ["Quantity matching error"]
    
    def _match_descriptions(self, inv_line: Dict[str, Any], 
                           dn_line: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Match line descriptions"""
        try:
            inv_desc = inv_line.get('description', '').lower()
            dn_desc = dn_line.get('description', '').lower()
            
            if not inv_desc or not dn_desc:
                return 0.0, ["Missing descriptions"]
            
            # Use sequence matcher for similarity
            similarity = SequenceMatcher(None, inv_desc, dn_desc).ratio()
            
            if similarity > 0.7:
                reasons = [f"Description similarity: {similarity:.1%}"]
                return similarity, reasons
            else:
                return 0.0, [f"Description mismatch: {similarity:.1%} similarity"]
                
        except Exception as e:
            logger.error(f"❌ Description matching failed: {e}")
            return 0.0, ["Description matching error"]
    
    def _match_prices(self, inv_line: Dict[str, Any], 
                     dn_line: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Match unit prices"""
        try:
            inv_price = inv_line.get('unit_price', 0)
            dn_price = dn_line.get('unit_price', 0)
            
            if inv_price == 0 or dn_price == 0:
                return 0.0, ["Missing prices"]
            
            # Calculate price difference
            diff_pct = abs(inv_price - dn_price) / max(inv_price, dn_price)
            
            if diff_pct <= self.PRICE_TOLERANCE:
                score = 1.0 - (diff_pct / self.PRICE_TOLERANCE)
                reasons = [f"Price match: {diff_pct:.1%} difference"]
                return score, reasons
            else:
                return 0.0, [f"Price mismatch: {diff_pct:.1%} difference"]
                
        except Exception as e:
            logger.error(f"❌ Price matching failed: {e}")
            return 0.0, ["Price matching error"]
    
    def _match_skus(self, inv_line: Dict[str, Any], 
                   dn_line: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Match SKUs"""
        try:
            inv_sku = inv_line.get('sku', '').upper()
            dn_sku = dn_line.get('sku', '').upper()
            
            if not inv_sku or not dn_sku:
                return 0.0, ["Missing SKUs"]
            
            if inv_sku == dn_sku:
                return 1.0, ["SKU exact match"]
            else:
                # Fuzzy SKU matching
                similarity = SequenceMatcher(None, inv_sku, dn_sku).ratio()
                if similarity > 0.8:
                    return similarity, [f"SKU similarity: {similarity:.1%}"]
                else:
                    return 0.0, ["SKU mismatch"]
                    
        except Exception as e:
            logger.error(f"❌ SKU matching failed: {e}")
            return 0.0, ["SKU matching error"]
    
    def persist_line_pairing(self, match_id: int, pairings: List[Dict[str, Any]]) -> bool:
        """Persist line pairing results to database"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                for pairing in pairings:
                    inv_line = pairing['invoice_line']
                    dn_line = pairing['delivery_line']
                    score = pairing['score']
                    reasons = pairing['reasons']
                    
                    cursor.execute("""
                        INSERT INTO match_link_items 
                        (match_id, invoice_line_id, delivery_line_id, reason, weight, score_contribution)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        match_id,
                        inv_line.get('id'),
                        dn_line.get('id'),
                        json.dumps(reasons),
                        score,
                        score
                    ))
                
                conn.commit()
                logger.info(f"✅ Persisted {len(pairings)} line pairings for match {match_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to persist line pairing: {e}")
            return False 