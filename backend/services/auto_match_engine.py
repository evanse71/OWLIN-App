"""
Auto-matching engine for delivery notes and invoices
Provides similarity scoring, tolerance rules, and matching suggestions
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
from dataclasses import dataclass
try:
    from ..db import fetch_all, fetch_one
except ImportError:
    try:
        from backend.db import fetch_all, fetch_one
    except ImportError:
        from db import fetch_all, fetch_one

@dataclass
class MatchSuggestion:
    """Represents a matching suggestion between delivery note and invoice"""
    invoice_id: str
    score: float
    reason: str
    confidence: str  # 'high', 'medium', 'low'

class AutoMatchEngine:
    """Engine for automatically matching delivery notes to invoices"""
    
    def __init__(self):
        # Matching tolerances
        self.date_tolerance_days = 7
        self.total_tolerance_percent = 0.05  # 5%
        self.supplier_similarity_threshold = 0.8
        
    def suggest_for_dn(self, delivery_note: Dict[str, Any], db_connection=None, max_age_days: int = 35) -> Optional[MatchSuggestion]:
        """
        Suggest best matching invoice for a delivery note
        
        Args:
            delivery_note: Delivery note data with supplier, date, total_amount
            db_connection: Database connection (optional)
            max_age_days: Maximum age of invoices to consider
            
        Returns:
            MatchSuggestion or None if no good matches
        """
        if not delivery_note:
            return None
            
        # Extract DN data
        dn_supplier = self._normalize_supplier(delivery_note.get('supplier', ''))
        dn_date = delivery_note.get('note_date') or delivery_note.get('date_iso')
        dn_total = delivery_note.get('total_amount', 0)
        
        if not dn_supplier or not dn_date:
            return None
            
        # Find candidate invoices
        candidates = self._find_candidate_invoices(dn_supplier, dn_date, max_age_days)
        
        if not candidates:
            return None
            
        # Score each candidate
        best_match = None
        best_score = 0.0
        
        for invoice in candidates:
            score, reason = self._calculate_match_score(
                delivery_note, invoice, dn_supplier, dn_date, dn_total
            )
            
            if score > best_score:
                best_score = score
                best_match = MatchSuggestion(
                    invoice_id=invoice['id'],
                    score=score,
                    reason=reason,
                    confidence=self._get_confidence_level(score)
                )
        
        # Only return if score is above threshold
        if best_match and best_match.score >= 0.6:
            return best_match
            
        return None
    
    def _find_candidate_invoices(self, supplier: str, date: str, max_age_days: int) -> List[Dict[str, Any]]:
        """Find candidate invoices within date range and supplier similarity"""
        try:
            # Parse date
            dn_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            start_date = (dn_date - timedelta(days=max_age_days)).isoformat()
            end_date = (dn_date + timedelta(days=self.date_tolerance_days)).isoformat()
            
            # Query invoices in date range
            query = """
                SELECT id, supplier, invoice_date, total_value, status
                FROM invoices 
                WHERE invoice_date BETWEEN ? AND ?
                AND status IN ('scanned', 'manual')
                ORDER BY invoice_date DESC
            """
            
            invoices = fetch_all(query, (start_date, end_date))
            
            # Filter by supplier similarity
            candidates = []
            for inv in invoices:
                inv_supplier = self._normalize_supplier(inv.get('supplier', ''))
                similarity = self._calculate_supplier_similarity(supplier, inv_supplier)
                
                if similarity >= self.supplier_similarity_threshold:
                    candidates.append(inv)
                    
            return candidates
            
        except Exception as e:
            print(f"Error finding candidate invoices: {e}")
            return []
    
    def _calculate_match_score(self, dn: Dict[str, Any], invoice: Dict[str, Any], 
                             dn_supplier: str, dn_date: str, dn_total: float) -> Tuple[float, str]:
        """Calculate match score between delivery note and invoice"""
        score = 0.0
        reasons = []
        
        # Supplier match (40% weight)
        inv_supplier = self._normalize_supplier(invoice.get('supplier', ''))
        supplier_sim = self._calculate_supplier_similarity(dn_supplier, inv_supplier)
        supplier_score = supplier_sim * 0.4
        score += supplier_score
        reasons.append(f"Supplier: {supplier_sim:.2f}")
        
        # Date match (30% weight)
        date_score = self._calculate_date_score(dn_date, invoice.get('invoice_date'))
        score += date_score * 0.3
        reasons.append(f"Date: {date_score:.2f}")
        
        # Total amount match (30% weight)
        inv_total = invoice.get('total_value', 0)
        total_score = self._calculate_total_score(dn_total, inv_total)
        score += total_score * 0.3
        reasons.append(f"Total: {total_score:.2f}")
        
        reason = "; ".join(reasons)
        return min(score, 1.0), reason
    
    def _calculate_supplier_similarity(self, supplier1: str, supplier2: str) -> float:
        """Calculate similarity between two supplier names"""
        if not supplier1 or not supplier2:
            return 0.0
            
        # Normalize and compare
        s1 = self._normalize_supplier(supplier1)
        s2 = self._normalize_supplier(supplier2)
        
        if s1 == s2:
            return 1.0
            
        # Simple word overlap similarity
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_date_score(self, date1: str, date2: str) -> float:
        """Calculate date similarity score"""
        if not date1 or not date2:
            return 0.0
            
        try:
            d1 = datetime.fromisoformat(date1.replace('Z', '+00:00'))
            d2 = datetime.fromisoformat(date2.replace('Z', '+00:00'))
            
            days_diff = abs((d1 - d2).days)
            
            if days_diff == 0:
                return 1.0
            elif days_diff <= 1:
                return 0.9
            elif days_diff <= 3:
                return 0.7
            elif days_diff <= 7:
                return 0.5
            else:
                return max(0.0, 1.0 - (days_diff / 30))
                
        except Exception:
            return 0.0
    
    def _calculate_total_score(self, total1: float, total2: float) -> float:
        """Calculate total amount similarity score"""
        if total1 == 0 and total2 == 0:
            return 1.0
        if total1 == 0 or total2 == 0:
            return 0.0
            
        diff_percent = abs(total1 - total2) / max(total1, total2)
        
        if diff_percent <= 0.01:  # 1%
            return 1.0
        elif diff_percent <= 0.05:  # 5%
            return 0.8
        elif diff_percent <= 0.1:  # 10%
            return 0.6
        elif diff_percent <= 0.2:  # 20%
            return 0.4
        else:
            return max(0.0, 1.0 - diff_percent)
    
    def _normalize_supplier(self, supplier: str) -> str:
        """Normalize supplier name for comparison"""
        if not supplier:
            return ""
            
        # Convert to lowercase and remove common words
        normalized = supplier.lower().strip()
        
        # Remove common business suffixes
        suffixes = ['ltd', 'limited', 'inc', 'corp', 'llc', 'plc', 'co', 'company']
        for suffix in suffixes:
            if normalized.endswith(f' {suffix}'):
                normalized = normalized[:-len(f' {suffix}')]
                
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level based on score"""
        if score >= 0.9:
            return 'high'
        elif score >= 0.7:
            return 'medium'
        else:
            return 'low'

# Global instance
_engine = None

def get_auto_match_engine() -> AutoMatchEngine:
    """Get singleton instance of auto match engine"""
    global _engine
    if _engine is None:
        _engine = AutoMatchEngine()
    return _engine
