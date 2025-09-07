"""
Supplier Discount Service

Manages supplier discount rules with versioning and validation.
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from db_manager_unified import get_db_manager

logger = logging.getLogger(__name__)

@dataclass
class SupplierDiscount:
    id: Optional[int]
    supplier_id: str
    scope: str  # 'supplier', 'category', 'sku'
    kind: str   # 'percent', 'per_case', 'per_litre'
    value: float
    ruleset_id: int
    created_at: str
    updated_at: str
    valid_from: Optional[str]
    valid_to: Optional[str]
    evidence_ref: Optional[str]

class DiscountService:
    """Service for managing supplier discount rules"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
    
    def create_discount(self, supplier_id: str, scope: str, kind: str, 
                       value: float, ruleset_id: int = 1, 
                       valid_from: Optional[str] = None,
                       valid_to: Optional[str] = None,
                       evidence_ref: Optional[str] = None) -> SupplierDiscount:
        """Create a new supplier discount rule"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Validate inputs
                if scope not in ['supplier', 'category', 'sku']:
                    raise ValueError(f"Invalid scope: {scope}")
                if kind not in ['percent', 'per_case', 'per_litre']:
                    raise ValueError(f"Invalid kind: {kind}")
                if value < 0:
                    raise ValueError(f"Discount value must be positive: {value}")
                
                cursor.execute("""
                    INSERT INTO supplier_discounts 
                    (supplier_id, scope, kind, value, ruleset_id, valid_from, valid_to, evidence_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (supplier_id, scope, kind, value, ruleset_id, valid_from, valid_to, evidence_ref))
                
                discount_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"✅ Created discount rule {discount_id} for {supplier_id}")
                
                return self.get_discount(discount_id)
                
        except Exception as e:
            logger.error(f"❌ Failed to create discount: {e}")
            raise
    
    def get_discount(self, discount_id: int) -> Optional[SupplierDiscount]:
        """Get discount by ID"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, supplier_id, scope, kind, value, ruleset_id, 
                           created_at, updated_at, valid_from, valid_to, evidence_ref
                    FROM supplier_discounts WHERE id = ?
                """, (discount_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return SupplierDiscount(*row)
                
        except Exception as e:
            logger.error(f"❌ Failed to get discount {discount_id}: {e}")
            return None
    
    def get_discounts_for_supplier(self, supplier_id: str, 
                                  ruleset_id: Optional[int] = None) -> List[SupplierDiscount]:
        """Get all discounts for a supplier"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT id, supplier_id, scope, kind, value, ruleset_id, 
                           created_at, updated_at, valid_from, valid_to, evidence_ref
                    FROM supplier_discounts 
                    WHERE supplier_id = ?
                """
                params = [supplier_id]
                
                if ruleset_id is not None:
                    query += " AND ruleset_id = ?"
                    params.append(ruleset_id)
                
                query += " ORDER BY scope, kind, created_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [SupplierDiscount(*row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Failed to get discounts for {supplier_id}: {e}")
            return []
    
    def update_discount(self, discount_id: int, **kwargs) -> Optional[SupplierDiscount]:
        """Update discount rule"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                valid_fields = {'scope', 'kind', 'value', 'ruleset_id', 'valid_from', 'valid_to', 'evidence_ref'}
                update_fields = []
                params = []
                
                for field, value in kwargs.items():
                    if field in valid_fields:
                        update_fields.append(f"{field} = ?")
                        params.append(value)
                
                if not update_fields:
                    raise ValueError("No valid fields to update")
                
                update_fields.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(discount_id)
                
                cursor.execute(f"""
                    UPDATE supplier_discounts 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """, params)
                
                if cursor.rowcount == 0:
                    return None
                
                conn.commit()
                logger.info(f"✅ Updated discount {discount_id}")
                
                return self.get_discount(discount_id)
                
        except Exception as e:
            logger.error(f"❌ Failed to update discount {discount_id}: {e}")
            return None
    
    def delete_discount(self, discount_id: int) -> bool:
        """Delete discount rule"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM supplier_discounts WHERE id = ?", (discount_id,))
                
                if cursor.rowcount == 0:
                    return False
                
                conn.commit()
                logger.info(f"✅ Deleted discount {discount_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to delete discount {discount_id}: {e}")
            return False
    
    def find_applicable_discount(self, supplier_id: str, sku: Optional[str] = None,
                                category: Optional[str] = None, 
                                ruleset_id: int = 1) -> Optional[SupplierDiscount]:
        """Find the most specific applicable discount rule"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Priority: sku > category > supplier
                if sku:
                    cursor.execute("""
                        SELECT id, supplier_id, scope, kind, value, ruleset_id, 
                               created_at, updated_at, valid_from, valid_to, evidence_ref
                        FROM supplier_discounts 
                        WHERE supplier_id = ? AND scope = 'sku' AND ruleset_id = ?
                        ORDER BY created_at DESC LIMIT 1
                    """, (supplier_id, ruleset_id))
                    row = cursor.fetchone()
                    if row:
                        return SupplierDiscount(*row)
                
                if category:
                    cursor.execute("""
                        SELECT id, supplier_id, scope, kind, value, ruleset_id, 
                               created_at, updated_at, valid_from, valid_to, evidence_ref
                        FROM supplier_discounts 
                        WHERE supplier_id = ? AND scope = 'category' AND ruleset_id = ?
                        ORDER BY created_at DESC LIMIT 1
                    """, (supplier_id, ruleset_id))
                    row = cursor.fetchone()
                    if row:
                        return SupplierDiscount(*row)
                
                # Fall back to supplier-level
                cursor.execute("""
                    SELECT id, supplier_id, scope, kind, value, ruleset_id, 
                           created_at, updated_at, valid_from, valid_to, evidence_ref
                    FROM supplier_discounts 
                    WHERE supplier_id = ? AND scope = 'supplier' AND ruleset_id = ?
                    ORDER BY created_at DESC LIMIT 1
                """, (supplier_id, ruleset_id))
                row = cursor.fetchone()
                
                return SupplierDiscount(*row) if row else None
                
        except Exception as e:
            logger.error(f"❌ Failed to find applicable discount: {e}")
            return None

# Global service instance
_discount_service: Optional[DiscountService] = None

def get_discount_service() -> DiscountService:
    """Get global discount service instance"""
    global _discount_service
    if _discount_service is None:
        _discount_service = DiscountService()
    return _discount_service 