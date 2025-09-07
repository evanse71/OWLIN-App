"""
Document assembly service - groups assets into coherent documents
"""
import sqlite3
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import json
from backend.db_manager_unified import get_db_manager
from backend.ocr.header_fingerprint import HeaderFingerprint
from backend.config_units import ASSEMBLY_TIME_WINDOW_S

class DocumentAssembler:
    """Assembles multi-asset documents using header fingerprinting"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.fingerprinter = HeaderFingerprint()
        
    def assemble_batch(self, batch_id: str) -> List[str]:
        """Assemble assets in batch into coherent documents"""
        conn = self.db.get_connection()
        
        # Get all assets in batch
        assets = self._get_batch_assets(conn, batch_id)
        if not assets:
            return []
            
        # Compute header fingerprints
        self._compute_header_fingerprints(conn, assets)
        
        # Group assets into documents
        doc_groups = self._group_assets_by_continuity(assets)
        
        # Create document records
        document_ids = []
        for i, group in enumerate(doc_groups):
            doc_id = self._create_document_from_group(conn, batch_id, group, i)
            if doc_id:
                document_ids.append(doc_id)
                
        conn.commit()
        return document_ids
    
    def _get_batch_assets(self, conn: sqlite3.Connection, batch_id: str) -> List[Dict]:
        """Get all assets in batch with metadata"""
        cur = conn.cursor()
        cur.execute("""
            SELECT id, path, mime, exif_ts, header_id, checksum_sha256
            FROM ingest_assets 
            WHERE batch_id = ?
            ORDER BY exif_ts, path
        """, (batch_id,))
        
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    def _compute_header_fingerprints(self, conn: sqlite3.Connection, assets: List[Dict]):
        """Compute and store header fingerprints for assets"""
        cur = conn.cursor()
        
        for asset in assets:
            if asset['header_id']:
                continue  # Already computed
                
            header_id = self.fingerprinter.compute_header_id(asset['path'])
            
            cur.execute("""
                UPDATE ingest_assets 
                SET header_id = ? 
                WHERE id = ?
            """, (header_id, asset['id']))
            
            asset['header_id'] = header_id
    
    def _group_assets_by_continuity(self, assets: List[Dict]) -> List[List[Dict]]:
        """Group assets into document sets using header fingerprint and timing"""
        if not assets:
            return []
            
        groups = []
        current_group = [assets[0]]
        
        for i in range(1, len(assets)):
            current = assets[i]
            previous = assets[i-1]
            
            # Check continuity criteria
            if self._assets_belong_together(previous, current):
                current_group.append(current)
            else:
                # Start new group
                groups.append(current_group)
                current_group = [current]
        
        # Add final group
        if current_group:
            groups.append(current_group)
            
        return groups
    
    def _assets_belong_together(self, asset1: Dict, asset2: Dict) -> bool:
        """Check if two assets belong to the same document"""
        # Time window check (≤60s)
        if asset1.get('exif_ts') and asset2.get('exif_ts'):
            try:
                dt1 = datetime.fromisoformat(asset1['exif_ts'].replace('Z', '+00:00'))
                dt2 = datetime.fromisoformat(asset2['exif_ts'].replace('Z', '+00:00'))
                if abs((dt2 - dt1).total_seconds()) > ASSEMBLY_TIME_WINDOW_S:
                    return False
            except Exception:
                pass
        
        # Header fingerprint match (≥0.8 similarity)
        if asset1.get('header_id') and asset2.get('header_id'):
            similarity = self.fingerprinter.compare_headers(
                asset1['header_id'], 
                asset2['header_id']
            )
            return similarity >= 0.8
            
        # Filename proximity fallback
        path1 = Path(asset1['path']).stem
        path2 = Path(asset2['path']).stem
        
        # Remove page numbers and check base similarity
        base1 = path1.rstrip('0123456789_-')
        base2 = path2.rstrip('0123456789_-')
        
        return base1 == base2 and len(base1) > 3
    
    def _create_document_from_group(self, conn: sqlite3.Connection, batch_id: str, 
                                   assets: List[Dict], order_index: int) -> Optional[str]:
        """Create document record from asset group"""
        if not assets:
            return None
            
        # Generate document ID
        doc_id = f"doc_{assets[0]['checksum_sha256'][:8]}"
        
        # Determine document kind (simple heuristic for now)
        kind = self._classify_document_kind(assets)
        
        # Get representative header ID
        header_id = assets[0].get('header_id', '')
        
        cur = conn.cursor()
        
        # Create document
        cur.execute("""
            INSERT OR REPLACE INTO documents 
            (id, batch_id, kind, header_id, page_count)
            VALUES (?, ?, ?, ?, ?)
        """, (doc_id, batch_id, kind, header_id, len(assets)))
        
        # Link pages
        for page_order, asset in enumerate(assets):
            cur.execute("""
                INSERT OR REPLACE INTO document_pages 
                (document_id, asset_id, page_order)
                VALUES (?, ?, ?)
            """, (doc_id, asset['id'], page_order))
        
        return doc_id
    
    def _classify_document_kind(self, assets: List[Dict]) -> str:
        """Classify document as invoice or delivery note"""
        # Simple classification based on filename patterns
        for asset in assets:
            path_lower = Path(asset['path']).name.lower()
            if any(keyword in path_lower for keyword in ['delivery', 'dn', 'receipt']):
                return 'delivery_note'
        
        return 'invoice'  # Default to invoice 