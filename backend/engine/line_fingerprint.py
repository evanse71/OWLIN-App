"""
Line Fingerprint System

Computes stable SHA256 fingerprints for line items and persists to database.
"""

import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from ..db_manager_unified import get_db_manager

logger = logging.getLogger(__name__)

class LineFingerprint:
    """Line fingerprint computation and persistence"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.engine_version = "1.0"
    
    def compute_fingerprint(self, line_data: Dict[str, Any]) -> str:
        """
        Compute SHA256 fingerprint for line item.
        
        Args:
            line_data: Dictionary containing line item data
            
        Returns:
            SHA256 hash string
        """
        try:
            # Extract critical fields in deterministic order
            critical_fields = [
                str(line_data.get('sku_id', '')),
                str(line_data.get('qty', 0)),
                str(line_data.get('uom_key', '')),
                str(line_data.get('unit_price_raw', 0)),
                str(line_data.get('nett_price', 0)),
                str(line_data.get('nett_value', 0)),
                str(line_data.get('date', '')),
                str(line_data.get('supplier_id', '')),
                str(line_data.get('ruleset_id', 1)),
                self.engine_version
            ]
            
            # Join with pipe separator
            fingerprint_string = '|'.join(critical_fields)
            
            # Compute SHA256
            fingerprint = hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()
            
            logger.debug(f"Computed fingerprint: {fingerprint[:8]}...")
            return fingerprint
            
        except Exception as e:
            logger.error(f"❌ Fingerprint computation failed: {e}")
            return ""
    
    def persist_fingerprint(self, invoice_id: int, line_id: int, fingerprint: str) -> bool:
        """
        Persist fingerprint to database.
        
        Args:
            invoice_id: Invoice ID
            line_id: Line item ID
            fingerprint: SHA256 fingerprint
            
        Returns:
            True if persisted successfully
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if line_fingerprint column exists
                cursor.execute("PRAGMA table_info(invoice_line_items)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'line_fingerprint' not in columns:
                    # Add column if it doesn't exist
                    cursor.execute("""
                        ALTER TABLE invoice_line_items 
                        ADD COLUMN line_fingerprint TEXT
                    """)
                    logger.info("Added line_fingerprint column to invoice_line_items")
                
                # Update the line item with fingerprint
                cursor.execute("""
                    UPDATE invoice_line_items 
                    SET line_fingerprint = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND invoice_id = ?
                """, (fingerprint, line_id, invoice_id))
                
                if cursor.rowcount == 0:
                    logger.warning(f"No line item found: invoice_id={invoice_id}, line_id={line_id}")
                    return False
                
                conn.commit()
                logger.info(f"✅ Persisted fingerprint for line {line_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to persist fingerprint: {e}")
            return False
    
    def get_fingerprint(self, invoice_id: int, line_id: int) -> Optional[str]:
        """
        Retrieve fingerprint from database.
        
        Args:
            invoice_id: Invoice ID
            line_id: Line item ID
            
        Returns:
            Fingerprint string or None if not found
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT line_fingerprint 
                    FROM invoice_line_items 
                    WHERE id = ? AND invoice_id = ?
                """, (line_id, invoice_id))
                
                row = cursor.fetchone()
                return row[0] if row else None
                
        except Exception as e:
            logger.error(f"❌ Failed to get fingerprint: {e}")
            return None
    
    def find_duplicate_fingerprints(self, fingerprint: str) -> list:
        """
        Find all line items with the same fingerprint.
        
        Args:
            fingerprint: SHA256 fingerprint to search for
            
        Returns:
            List of (invoice_id, line_id) tuples
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT invoice_id, id 
                    FROM invoice_line_items 
                    WHERE line_fingerprint = ?
                    ORDER BY created_at DESC
                """, (fingerprint,))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"❌ Failed to find duplicate fingerprints: {e}")
            return []
    
    def compute_and_persist(self, invoice_id: int, line_id: int, 
                          line_data: Dict[str, Any]) -> Optional[str]:
        """
        Compute and persist fingerprint in one operation.
        
        Args:
            invoice_id: Invoice ID
            line_id: Line item ID
            line_data: Line item data
            
        Returns:
            Fingerprint string or None if failed
        """
        try:
            fingerprint = self.compute_fingerprint(line_data)
            if not fingerprint:
                return None
            
            success = self.persist_fingerprint(invoice_id, line_id, fingerprint)
            return fingerprint if success else None
            
        except Exception as e:
            logger.error(f"❌ Compute and persist failed: {e}")
            return None
    
    def validate_fingerprint_stability(self, line_data: Dict[str, Any]) -> bool:
        """
        Validate that fingerprint is stable across multiple computations.
        
        Args:
            line_data: Line item data
            
        Returns:
            True if fingerprint is stable
        """
        try:
            # Compute fingerprint multiple times
            fingerprints = []
            for _ in range(5):
                fingerprint = self.compute_fingerprint(line_data)
                fingerprints.append(fingerprint)
            
            # All fingerprints should be identical
            return len(set(fingerprints)) == 1 and fingerprints[0] != ""
            
        except Exception as e:
            logger.error(f"❌ Fingerprint stability validation failed: {e}")
            return False

# Global line fingerprint instance
_line_fingerprint: Optional[LineFingerprint] = None

def get_line_fingerprint() -> LineFingerprint:
    """Get global line fingerprint instance"""
    global _line_fingerprint
    if _line_fingerprint is None:
        _line_fingerprint = LineFingerprint()
    return _line_fingerprint 