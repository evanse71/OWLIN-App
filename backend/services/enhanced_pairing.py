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


@dataclass
class PairingResult:
    """Result of pairing analysis"""
    invoice_id: str
    delivery_note_id: str
    total_score: float
    supplier_match_score: float
    date_proximity_score: float
    line_item_similarity_score: float
    quantity_match_score: float
    price_match_score: float
    pairing_method: str
    confidence: float
    reasoning: List[str]


class EnhancedPairingService:
    """
    Enhanced pairing service with comprehensive heuristics.
    
    Features:
    - Fuzzy supplier name matching
    - Configurable date windows
    - Line-item similarity analysis
    - Quantity and price matching
    - Confidence scoring
    - Rule-based pairing
    """
    
    def __init__(self, db):
        self.db = db
        self.pairing_rules = self._load_pairing_rules()
        self.supplier_aliases = self._load_supplier_aliases()
    
    def auto_pair(self) -> Dict[str, Any]:
        """
        Automatically pair invoices with delivery notes using comprehensive heuristics.
        
        Returns:
            Dictionary with pairing statistics
        """
        cursor = self.db.cursor()
        
        # Get all unpaired invoices
        cursor.execute("""
            SELECT i.id, i.supplier_name, i.invoice_date, i.invoice_number, i.total_amount_pennies
            FROM invoices i
            WHERE i.supplier_name IS NOT NULL 
            AND i.invoice_date IS NOT NULL
            AND i.id NOT IN (SELECT invoice_id FROM doc_pairs WHERE status = 'active')
            AND i.status = 'parsed'
        """)
        invoices = cursor.fetchall()
        
        # Get all delivery notes
        cursor.execute("""
            SELECT d.id, d.supplier_name, d.delivery_date, d.delivery_note_number, d.total_items
            FROM delivery_notes d
            WHERE d.supplier_name IS NOT NULL
            AND d.delivery_date IS NOT NULL
            AND d.status = 'parsed'
        """)
        delivery_notes = cursor.fetchall()
        
        pairs_created = 0
        high_confidence_pairs = 0
        medium_confidence_pairs = 0
        
        for invoice in invoices:
            invoice_id, invoice_supplier, invoice_date, invoice_number, invoice_total = invoice
            
            # Find candidate delivery notes
            candidates = self._find_candidate_delivery_notes(
                invoice_id, invoice_supplier, invoice_date, invoice_total, delivery_notes
            )
            
            # Create pairs for high-scoring candidates
            for result in candidates:
                if result.total_score >= 0.6:  # Configurable threshold
                    self._create_pair(result)
                    pairs_created += 1
                    
                    if result.confidence >= 0.8:
                        high_confidence_pairs += 1
                    elif result.confidence >= 0.6:
                        medium_confidence_pairs += 1
        
        self.db.commit()
        
        return {
            'pairs_created': pairs_created,
            'high_confidence_pairs': high_confidence_pairs,
            'medium_confidence_pairs': medium_confidence_pairs,
            'total_invoices_processed': len(invoices),
            'total_delivery_notes': len(delivery_notes)
        }
    
    def _find_candidate_delivery_notes(
        self, 
        invoice_id: str, 
        invoice_supplier: str, 
        invoice_date: str, 
        invoice_total: int,
        delivery_notes: List[Tuple]
    ) -> List[PairingResult]:
        """Find candidate delivery notes for an invoice"""
        candidates = []
        
        for dn in delivery_notes:
            dn_id, dn_supplier, dn_date, dn_number, dn_items = dn
            
            # Skip if already paired
            if self._is_already_paired(invoice_id, dn_id):
                continue
            
            # Calculate individual scores
            supplier_score = self._calculate_supplier_similarity(invoice_supplier, dn_supplier)
            date_score = self._calculate_date_proximity(invoice_date, dn_date)
            line_item_score = self._calculate_line_item_similarity(invoice_id, dn_id)
            quantity_score = self._calculate_quantity_match(invoice_id, dn_id)
            price_score = self._calculate_price_match(invoice_id, dn_id, invoice_total)
            
            # Calculate weighted total score
            total_score = (
                supplier_score * self.pairing_rules['supplier_match']['weight'] +
                date_score * self.pairing_rules['date_window']['weight'] +
                line_item_score * self.pairing_rules['line_item_similarity']['weight'] +
                quantity_score * self.pairing_rules['quantity_match']['weight'] +
                price_score * self.pairing_rules['price_match']['weight']
            )
            
            # Determine confidence and method
            confidence = self._calculate_confidence(
                supplier_score, date_score, line_item_score, quantity_score, price_score
            )
            
            pairing_method = self._determine_pairing_method(
                supplier_score, date_score, line_item_score
            )
            
            # Generate reasoning
            reasoning = self._generate_pairing_reasoning(
                supplier_score, date_score, line_item_score, quantity_score, price_score
            )
            
            if total_score >= 0.3:  # Minimum threshold
                candidates.append(PairingResult(
                    invoice_id=invoice_id,
                    delivery_note_id=dn_id,
                    total_score=total_score,
                    supplier_match_score=supplier_score,
                    date_proximity_score=date_score,
                    line_item_similarity_score=line_item_score,
                    quantity_match_score=quantity_score,
                    price_match_score=price_score,
                    pairing_method=pairing_method,
                    confidence=confidence,
                    reasoning=reasoning
                ))
        
        # Sort by total score descending
        candidates.sort(key=lambda x: x.total_score, reverse=True)
        return candidates
    
    def _calculate_supplier_similarity(self, supplier1: str, supplier2: str) -> float:
        """Calculate enhanced supplier similarity using fuzzy matching and aliases"""
        if not supplier1 or not supplier2:
            return 0.0
        
        # Normalize supplier names
        norm1 = self._normalize_supplier_name(supplier1)
        norm2 = self._normalize_supplier_name(supplier2)
        
        # Direct fuzzy matching
        direct_score = fuzz.ratio(norm1, norm2) / 100.0
        
        # Check for aliases
        alias_score = self._check_supplier_aliases(norm1, norm2)
        
        # Use the higher score
        return max(direct_score, alias_score)
    
    def _calculate_date_proximity(self, invoice_date: str, dn_date: str) -> float:
        """Calculate date proximity score with configurable window"""
        invoice_dt = self._parse_date(invoice_date)
        dn_dt = self._parse_date(dn_date)
        
        if not invoice_dt or not dn_dt:
            return 0.0
        
        days_diff = abs((invoice_dt - dn_dt).days)
        window_days = self.pairing_rules['date_window']['parameters']['window_days']
        
        if days_diff <= window_days:
            # Linear decay within window
            return 1.0 - (days_diff / window_days) * 0.5
        else:
            # Exponential decay outside window
            return 0.5 * (0.5 ** ((days_diff - window_days) / window_days))
    
    def _calculate_line_item_similarity(self, invoice_id: str, dn_id: str) -> float:
        """Calculate line item similarity between invoice and delivery note"""
        cursor = self.db.cursor()
        
        # Get invoice line items
        cursor.execute("""
            SELECT description, quantity, unit_price_pennies
            FROM invoice_line_items
            WHERE invoice_id = ?
        """, (invoice_id,))
        invoice_items = cursor.fetchall()
        
        # Get delivery note line items
        cursor.execute("""
            SELECT description, quantity, unit_price_pennies
            FROM delivery_line_items
            WHERE delivery_note_id = ?
        """, (dn_id,))
        dn_items = cursor.fetchall()
        
        if not invoice_items or not dn_items:
            return 0.0
        
        # Calculate similarity using description matching and quantity comparison
        total_similarity = 0.0
        matched_items = 0
        
        for inv_desc, inv_qty, inv_price in invoice_items:
            best_match_score = 0.0
            
            for dn_desc, dn_qty, dn_price in dn_items:
                # Description similarity
                desc_similarity = fuzz.ratio(
                    inv_desc.lower(), dn_desc.lower()
                ) / 100.0
                
                # Quantity similarity (allow some tolerance)
                qty_similarity = self._calculate_quantity_similarity(inv_qty, dn_qty)
                
                # Combined score
                item_score = (desc_similarity * 0.7) + (qty_similarity * 0.3)
                best_match_score = max(best_match_score, item_score)
            
            total_similarity += best_match_score
            if best_match_score > 0.5:
                matched_items += 1
        
        # Normalize by number of items
        avg_similarity = total_similarity / len(invoice_items)
        match_ratio = matched_items / len(invoice_items)
        
        return (avg_similarity * 0.7) + (match_ratio * 0.3)
    
    def _calculate_quantity_match(self, invoice_id: str, dn_id: str) -> float:
        """Calculate quantity matching score"""
        cursor = self.db.cursor()
        
        # Get total quantities
        cursor.execute("""
            SELECT SUM(quantity) FROM invoice_line_items WHERE invoice_id = ?
        """, (invoice_id,))
        inv_total = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT SUM(quantity) FROM delivery_line_items WHERE delivery_note_id = ?
        """, (dn_id,))
        dn_total = cursor.fetchone()[0] or 0
        
        if inv_total == 0 and dn_total == 0:
            return 1.0
        
        if inv_total == 0 or dn_total == 0:
            return 0.0
        
        # Calculate percentage difference
        diff = abs(inv_total - dn_total) / max(inv_total, dn_total)
        tolerance = self.pairing_rules['quantity_match']['parameters']['tolerance']
        
        if diff <= tolerance:
            return 1.0 - (diff / tolerance) * 0.5
        else:
            return 0.5 * (0.5 ** ((diff - tolerance) / tolerance))
    
    def _calculate_price_match(self, invoice_id: str, dn_id: str, invoice_total: int) -> float:
        """Calculate price matching score"""
        cursor = self.db.cursor()
        
        # Get delivery note total (if available)
        cursor.execute("""
            SELECT SUM(line_total_pennies) FROM delivery_line_items WHERE delivery_note_id = ?
        """, (dn_id,))
        dn_total = cursor.fetchone()[0] or 0
        
        if invoice_total == 0 and dn_total == 0:
            return 1.0
        
        if invoice_total == 0 or dn_total == 0:
            return 0.0
        
        # Calculate percentage difference
        diff = abs(invoice_total - dn_total) / max(invoice_total, dn_total)
        tolerance = self.pairing_rules['price_match']['parameters']['tolerance']
        
        if diff <= tolerance:
            return 1.0 - (diff / tolerance) * 0.5
        else:
            return 0.5 * (0.5 ** ((diff - tolerance) / tolerance))
    
    def _load_pairing_rules(self) -> Dict[str, Any]:
        """Load pairing rules from database"""
        cursor = self.db.cursor()
        cursor.execute("SELECT rule_name, rule_type, parameters, weight FROM pairing_rules WHERE enabled = 1")
        
        rules = {}
        for row in cursor.fetchall():
            rule_name, rule_type, params_json, weight = row
            rules[rule_type] = {
                'parameters': json.loads(params_json),
                'weight': weight
            }
        
        # Default rules if none found
        if not rules:
            rules = {
                'supplier_match': {'parameters': {'threshold': 0.8, 'fuzzy': True}, 'weight': 0.4},
                'date_window': {'parameters': {'window_days': 30, 'strict': False}, 'weight': 0.3},
                'line_item_similarity': {'parameters': {'threshold': 0.7}, 'weight': 0.2},
                'quantity_match': {'parameters': {'tolerance': 0.1}, 'weight': 0.05},
                'price_match': {'parameters': {'tolerance': 0.05}, 'weight': 0.05}
            }
        
        return rules
    
    def _load_supplier_aliases(self) -> Dict[str, List[str]]:
        """Load supplier aliases for better matching"""
        # This could be loaded from a database table or configuration file
        return {
            'brakes': ['brakes food', 'brakes foodservice', 'brakes ltd'],
            'bidfood': ['bidfood ltd', 'bidfood uk'],
            'booker': ['booker ltd', 'booker wholesale'],
            'tesco': ['tesco plc', 'tesco stores'],
            'makro': ['makro cash & carry', 'makro wholesale']
        }
    
    def _normalize_supplier_name(self, name: str) -> str:
        """Normalize supplier name for better matching"""
        if not name:
            return ""
        
        normalized = name.lower().strip()
        
        # Remove common business suffixes
        suffixes = ['ltd', 'limited', 'plc', 'inc', 'corp', 'corporation', 'llc', 'co', 'uk']
        for suffix in suffixes:
            if normalized.endswith(' ' + suffix):
                normalized = normalized[:-len(' ' + suffix)]
            elif normalized.endswith('.' + suffix):
                normalized = normalized[:-len('.' + suffix)]
        
        return normalized
    
    def _check_supplier_aliases(self, name1: str, name2: str) -> float:
        """Check if supplier names are aliases"""
        for supplier, aliases in self.supplier_aliases.items():
            if name1 in aliases and name2 in aliases:
                return 1.0
            if name1 == supplier and name2 in aliases:
                return 0.9
            if name2 == supplier and name1 in aliases:
                return 0.9
        
        return 0.0
    
    def _calculate_quantity_similarity(self, qty1: float, qty2: float) -> float:
        """Calculate quantity similarity with tolerance"""
        if qty1 == 0 and qty2 == 0:
            return 1.0
        
        if qty1 == 0 or qty2 == 0:
            return 0.0
        
        diff = abs(qty1 - qty2) / max(qty1, qty2)
        tolerance = 0.1  # 10% tolerance
        
        if diff <= tolerance:
            return 1.0 - (diff / tolerance) * 0.5
        else:
            return 0.5 * (0.5 ** ((diff - tolerance) / tolerance))
    
    def _calculate_confidence(
        self, 
        supplier_score: float, 
        date_score: float, 
        line_item_score: float,
        quantity_score: float,
        price_score: float
    ) -> float:
        """Calculate overall confidence score"""
        # Weighted average with emphasis on supplier and date
        confidence = (
            supplier_score * 0.4 +
            date_score * 0.3 +
            line_item_score * 0.2 +
            quantity_score * 0.05 +
            price_score * 0.05
        )
        
        return min(1.0, confidence)
    
    def _determine_pairing_method(
        self, 
        supplier_score: float, 
        date_score: float, 
        line_item_score: float
    ) -> str:
        """Determine the primary pairing method used"""
        if supplier_score >= 0.9 and date_score >= 0.8:
            return 'exact'
        elif supplier_score >= 0.7 and line_item_score >= 0.6:
            return 'fuzzy'
        else:
            return 'auto'
    
    def _generate_pairing_reasoning(
        self,
        supplier_score: float,
        date_score: float,
        line_item_score: float,
        quantity_score: float,
        price_score: float
    ) -> List[str]:
        """Generate human-readable reasoning for pairing"""
        reasoning = []
        
        if supplier_score >= 0.8:
            reasoning.append(f"Strong supplier match ({supplier_score:.2f})")
        elif supplier_score >= 0.6:
            reasoning.append(f"Good supplier match ({supplier_score:.2f})")
        
        if date_score >= 0.8:
            reasoning.append(f"Close date proximity ({date_score:.2f})")
        elif date_score >= 0.6:
            reasoning.append(f"Reasonable date proximity ({date_score:.2f})")
        
        if line_item_score >= 0.7:
            reasoning.append(f"Good line item similarity ({line_item_score:.2f})")
        
        if quantity_score >= 0.8:
            reasoning.append(f"Quantity match ({quantity_score:.2f})")
        
        if price_score >= 0.8:
            reasoning.append(f"Price match ({price_score:.2f})")
        
        return reasoning
    
    def _is_already_paired(self, invoice_id: str, dn_id: str) -> bool:
        """Check if invoice and delivery note are already paired"""
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM doc_pairs 
            WHERE invoice_id = ? AND delivery_note_id = ? AND status = 'active'
        """, (invoice_id, dn_id))
        return cursor.fetchone()[0] > 0
    
    def _create_pair(self, result: PairingResult) -> str:
        """Create a new document pair"""
        pair_id = str(uuid.uuid4())
        
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO doc_pairs (
                id, invoice_id, delivery_note_id, score, pairing_method,
                supplier_match_score, date_proximity_score, line_item_similarity_score,
                quantity_match_score, price_match_score, total_confidence,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pair_id,
            result.invoice_id,
            result.delivery_note_id,
            result.total_score,
            result.pairing_method,
            result.supplier_match_score,
            result.date_proximity_score,
            result.line_item_similarity_score,
            result.quantity_match_score,
            result.price_match_score,
            result.confidence,
            'active',
            datetime.datetime.now(datetime.timezone.utc).isoformat()
        ))
        
        return pair_id
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """Parse date string in various formats"""
        if not date_str:
            return None
        
        formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d',
            '%d.%m.%Y', '%Y.%m.%d', '%d %m %Y', '%Y %m %d'
        ]
        
        for fmt in formats:
            try:
                return datetime.datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None


def auto_pair_enhanced(db) -> Dict[str, Any]:
    """
    Enhanced automatic pairing function.
    
    Args:
        db: Database connection object
        
    Returns:
        Dictionary with pairing statistics
    """
    service = EnhancedPairingService(db)
    return service.auto_pair()
