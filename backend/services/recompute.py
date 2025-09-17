"""
Recompute service for recalculating invoice totals and other derived values
"""
from typing import Optional, Dict, Any
try:
    from ..db import execute, fetch_one, fetch_all
except ImportError:
    try:
        from backend.db import execute, fetch_one, fetch_all
    except ImportError:
        from db import execute, fetch_one, fetch_all

class RecomputeService:
    """Service for recomputing derived values"""
    
    def __init__(self):
        pass
    
    def recompute_invoice_totals(self, invoice_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Recompute invoice totals from line items
        
        Args:
            invoice_id: ID of invoice to recompute
            force: Force recomputation even if total_value is already set
            
        Returns:
            Dict with recomputation results
        """
        # Get current invoice
        invoice = fetch_one("SELECT id, total_value FROM invoices WHERE id=?", (invoice_id,))
        if not invoice:
            return {"error": "Invoice not found"}
        
        # Check if recomputation is needed
        if not force and invoice.get("total_value") is not None:
            return {"skipped": "Total already computed", "current_total": invoice["total_value"]}
        
        # Get all line items
        line_items = fetch_all("""
            SELECT quantity, unit_price, vat_rate, total
            FROM invoice_line_items 
            WHERE invoice_id=?
        """, (invoice_id,))
        
        if not line_items:
            # No line items, set total to 0
            execute("UPDATE invoices SET total_value=0 WHERE id=?", (invoice_id,))
            return {"recomputed": True, "new_total": 0, "line_count": 0}
        
        # Calculate totals
        subtotal = 0.0
        vat_total = 0.0
        line_count = 0
        
        for item in line_items:
            quantity = float(item.get("quantity") or 0)
            unit_price = float(item.get("unit_price") or 0)
            vat_rate = float(item.get("vat_rate") or 0)
            
            # Calculate line total
            line_total = quantity * unit_price
            subtotal += line_total
            
            # Calculate VAT for this line
            line_vat = line_total * (vat_rate / 100)
            vat_total += line_vat
            
            line_count += 1
        
        # Calculate final total
        grand_total = subtotal + vat_total
        
        # Update invoice
        execute("""
            UPDATE invoices 
            SET total_value=? 
            WHERE id=?
        """, (grand_total, invoice_id))
        
        return {
            "recomputed": True,
            "new_total": grand_total,
            "subtotal": subtotal,
            "vat_total": vat_total,
            "line_count": line_count
        }
    
    def recompute_all_invoice_totals(self, force: bool = False) -> Dict[str, Any]:
        """
        Recompute totals for all invoices
        
        Args:
            force: Force recomputation even if total_value is already set
            
        Returns:
            Dict with recomputation results
        """
        # Get all invoices
        invoices = fetch_all("SELECT id FROM invoices")
        
        results = {
            "processed": 0,
            "recomputed": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": []
        }
        
        for invoice in invoices:
            invoice_id = invoice["id"]
            results["processed"] += 1
            
            try:
                result = self.recompute_invoice_totals(invoice_id, force)
                
                if result.get("recomputed"):
                    results["recomputed"] += 1
                elif result.get("skipped"):
                    results["skipped"] += 1
                elif result.get("error"):
                    results["errors"] += 1
                    results["error_details"].append({
                        "invoice_id": invoice_id,
                        "error": result["error"]
                    })
                    
            except Exception as e:
                results["errors"] += 1
                results["error_details"].append({
                    "invoice_id": invoice_id,
                    "error": str(e)
                })
        
        return results
    
    def validate_invoice_totals(self, invoice_id: str) -> Dict[str, Any]:
        """
        Validate that invoice totals are correct
        
        Args:
            invoice_id: ID of invoice to validate
            
        Returns:
            Dict with validation results
        """
        # Get invoice total
        invoice = fetch_one("SELECT total_value FROM invoices WHERE id=?", (invoice_id,))
        if not invoice:
            return {"valid": False, "error": "Invoice not found"}
        
        stored_total = invoice.get("total_value")
        if stored_total is None:
            return {"valid": False, "error": "No total stored"}
        
        # Recompute total
        result = self.recompute_invoice_totals(invoice_id, force=True)
        if result.get("error"):
            return {"valid": False, "error": result["error"]}
        
        computed_total = result["new_total"]
        
        # Compare totals (allow small floating point differences)
        difference = abs(stored_total - computed_total)
        tolerance = 0.01  # 1 cent tolerance
        
        is_valid = difference <= tolerance
        
        return {
            "valid": is_valid,
            "stored_total": stored_total,
            "computed_total": computed_total,
            "difference": difference,
            "tolerance": tolerance
        }
    
    def get_invoice_summary(self, invoice_id: str) -> Dict[str, Any]:
        """
        Get detailed summary of invoice calculations
        
        Args:
            invoice_id: ID of invoice
            
        Returns:
            Dict with invoice summary
        """
        # Get invoice
        invoice = fetch_one("""
            SELECT id, supplier, invoice_date, total_value, currency
            FROM invoices 
            WHERE id=?
        """, (invoice_id,))
        
        if not invoice:
            return {"error": "Invoice not found"}
        
        # Get line items with calculations
        line_items = fetch_all("""
            SELECT description, quantity, unit_price, vat_rate, total
            FROM invoice_line_items 
            WHERE invoice_id=?
            ORDER BY id
        """, (invoice_id,))
        
        # Calculate summary
        subtotal = 0.0
        vat_breakdown = {}
        line_count = 0
        
        for item in line_items:
            quantity = float(item.get("quantity") or 0)
            unit_price = float(item.get("unit_price") or 0)
            vat_rate = float(item.get("vat_rate") or 0)
            
            line_total = quantity * unit_price
            subtotal += line_total
            
            # Group by VAT rate
            vat_key = f"{vat_rate}%"
            if vat_key not in vat_breakdown:
                vat_breakdown[vat_key] = {"rate": vat_rate, "subtotal": 0.0, "vat_amount": 0.0}
            
            vat_breakdown[vat_key]["subtotal"] += line_total
            vat_breakdown[vat_key]["vat_amount"] += line_total * (vat_rate / 100)
            
            line_count += 1
        
        # Calculate total VAT
        total_vat = sum(vb["vat_amount"] for vb in vat_breakdown.values())
        grand_total = subtotal + total_vat
        
        return {
            "invoice": dict(invoice),
            "line_count": line_count,
            "subtotal": subtotal,
            "vat_breakdown": vat_breakdown,
            "total_vat": total_vat,
            "grand_total": grand_total,
            "stored_total": invoice.get("total_value"),
            "is_consistent": abs(grand_total - (invoice.get("total_value") or 0)) <= 0.01
        }

# Global instance
_recompute_service = None

def get_recompute_service() -> RecomputeService:
    """Get singleton instance of recompute service"""
    global _recompute_service
    if _recompute_service is None:
        _recompute_service = RecomputeService()
    return _recompute_service

def recompute_invoice_totals(invoice_id: str, force: bool = False) -> Dict[str, Any]:
    """Convenience function to recompute invoice totals"""
    return get_recompute_service().recompute_invoice_totals(invoice_id, force)
