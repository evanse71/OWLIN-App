"""
Document Assembler Service
Implements header fingerprinting to stitch scattered images into logical documents
"""
import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import sqlite3
from PIL import Image
import numpy as np

from db_manager_unified import get_db_manager

class DocumentAssembler:
    """Assembles scattered image files into logical documents using fingerprinting"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.fingerprint_window = 60  # seconds for same fingerprint grouping
        
    def create_batch(self, batch_id: str) -> str:
        """Create a new ingest batch"""
        conn = self.db.get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ingest_batches(id, created_at, status) VALUES(?, ?, ?)",
            (batch_id, datetime.now().isoformat(), 'processing')
        )
        conn.commit()
        return batch_id
    
    def add_asset(self, batch_id: str, file_path: str, mime_type: str, 
                  file_size: int) -> str:
        """Add an asset to a batch with fingerprinting"""
        conn = self.db.get_conn()
        cur = conn.cursor()
        
        # Generate asset ID
        asset_id = f"asset_{int(time.time() * 1000000)}"
        
        # Generate perceptual hash
        phash = self._generate_phash(file_path)
        
        # Extract header text (first 1000 chars for fingerprinting)
        header_text = self._extract_header_text(file_path, mime_type)
        
        cur.execute(
            """INSERT INTO ingest_assets
               (id, batch_id, path, phash, header_text, mime, file_size, created_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
            (asset_id, batch_id, file_path, phash, header_text, mime_type,
             file_size, datetime.now().isoformat())
        )
        
        # Update batch asset count
        cur.execute(
            "UPDATE ingest_batches SET total_assets = total_assets + 1 WHERE id = ?",
            (batch_id,)
        )
        
        conn.commit()
        return asset_id
    
    def _generate_phash(self, file_path: str) -> str:
        """Generate perceptual hash for image similarity"""
        try:
            with Image.open(file_path) as img:
                # Resize to 8x8 for simple pHash
                img = img.convert('L').resize((8, 8))
                pixels = np.array(img)
                
                # Calculate average pixel value
                avg = pixels.mean()
                
                # Generate hash: 1 if pixel > avg, 0 otherwise
                hash_bits = (pixels > avg).flatten()
                hash_int = sum([int(bit) * (2 ** i) for i, bit in enumerate(hash_bits)])
                
                return f"{hash_int:016x}"
        except Exception as e:
            # Fallback to file hash if image processing fails
            return hashlib.md5(Path(file_path).read_bytes()).hexdigest()
    
    def _extract_header_text(self, file_path: str, mime_type: str) -> str:
        """Extract header text for fingerprinting (OCR or fallback)"""
        try:
            # For now, return first part of filename as header text
            # TODO: Integrate with OCR service for actual text extraction
            filename = Path(file_path).stem
            return filename[:1000]  # Limit to 1000 chars
        except Exception:
            return ""
    
    def assemble_documents(self, batch_id: str) -> List[Dict[str, Any]]:
        """Assemble assets into logical documents using fingerprinting"""
        conn = self.db.get_conn()
        cur = conn.cursor()
        
        # Get all assets in this batch
        cur.execute(
            "SELECT id, phash, header_text, created_at FROM ingest_assets WHERE batch_id = ? ORDER BY created_at",
            (batch_id,)
        )
        assets = cur.fetchall()
        
        if not assets:
            return []
        
        # Group assets by fingerprint within time window
        doc_groups = self._group_assets_by_fingerprint(assets)
        
        assembled_docs = []
        
        for doc_idx, group in enumerate(doc_groups):
            # Create document
            doc_id = f"doc_{batch_id}_{doc_idx}"
            fingerprint_hash = self._generate_doc_fingerprint(group)
            
            # Determine document kind from content analysis
            doc_kind = self._determine_doc_kind(group)
            
            # Use correct column names from schema
            cur.execute(
                """INSERT INTO documents
                   (id, batch_id, kind, fingerprint_hash, created_at, assembled_at, page_count, doc_kind_new)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, batch_id, doc_kind, fingerprint_hash,
                 datetime.now().isoformat(), datetime.now().isoformat(), len(group), doc_kind)
            )
            
            # Create document pages for each asset
            for page_idx, asset in enumerate(group):
                page_id = f"page_{doc_id}_{page_idx}"
                cur.execute(
                    """INSERT INTO document_pages
                       (document_id, asset_id, page_order)
                       VALUES(?, ?, ?)""",
                    (doc_id, asset['id'], page_idx)
                )
            
            assembled_docs.append({
                "id": doc_id,
                "batch_id": batch_id,
                "doc_kind_new": doc_kind,
                "page_count": len(group),
                "fingerprint_hash": fingerprint_hash
            })
        
        # Update batch status
        cur.execute(
            "UPDATE ingest_batches SET processed_assets = ?, status = 'completed' WHERE id = ?",
            (len(assets), batch_id)
        )
        
        conn.commit()
        return assembled_docs
    
    def _group_assets_by_fingerprint(self, assets: List[Tuple]) -> List[List[Dict]]:
        """Group assets by fingerprint within time window"""
        # Convert to list of dicts for easier manipulation
        asset_dicts = [
            {'id': a[0], 'phash': a[1], 'header_text': a[2], 'created_at': a[3]}
            for a in assets
        ]
        
        groups = []
        processed = set()
        
        for asset in asset_dicts:
            if asset['id'] in processed:
                continue
                
            # Find similar assets within time window
            group = [asset]
            processed.add(asset['id'])
            
            asset_time = datetime.fromisoformat(asset['created_at'])
            
            for other in asset_dicts:
                if other['id'] in processed:
                    continue
                    
                other_time = datetime.fromisoformat(other['created_at'])
                time_diff = abs((asset_time - other_time).total_seconds())
                
                # Check if within time window and similar fingerprint
                if (time_diff <= self.fingerprint_window and 
                    self._fingerprint_similarity(asset['phash'], other['phash']) > 0.8):
                    group.append(other)
                    processed.add(other['id'])
            
            groups.append(group)
        
        return groups
    
    def _fingerprint_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two fingerprints (0.0 to 1.0)"""
        try:
            # Convert hex hashes to binary
            h1 = int(hash1, 16)
            h2 = int(hash2, 16)
            
            # Calculate Hamming distance
            xor_result = h1 ^ h2
            hamming_distance = bin(xor_result).count('1')
            
            # Convert to similarity (0.0 to 1.0)
            max_distance = 64  # 64-bit hash
            similarity = 1.0 - (hamming_distance / max_distance)
            
            return max(0.0, min(1.0, similarity))
        except Exception:
            return 0.0
    
    def _generate_doc_fingerprint(self, assets: List[Dict]) -> str:
        """Generate document-level fingerprint from asset group"""
        # Combine all asset fingerprints and header text
        combined = ""
        for asset in assets:
            combined += asset['phash'] + "|" + (asset['header_text'] or "")
        
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _determine_doc_kind(self, assets: List[Dict]) -> str:
        """Determine document kind from asset analysis"""
        # Simple heuristic: check header text for keywords
        header_text = " ".join([a.get('header_text', '') for a in assets]).lower()
        
        if any(word in header_text for word in ['invoice', 'bill', 'receipt']):
            return 'invoice'
        elif any(word in header_text for word in ['delivery', 'dn', 'dispatch']):
            return 'dn'
        elif any(word in header_text for word in ['utility', 'electric', 'gas', 'water']):
            return 'utility'
        else:
            return 'receipt'  # Default fallback
    
    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get current status of a batch"""
        conn = self.db.get_conn()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT * FROM ingest_batches WHERE id = ?",
            (batch_id,)
        )
        batch = cur.fetchone()
        
        if not batch:
            return {'error': 'Batch not found'}
        
        # Get asset count
        cur.execute(
            "SELECT COUNT(*) FROM ingest_assets WHERE batch_id = ?",
            (batch_id,)
        )
        asset_count = cur.fetchone()[0]
        
        # Get document count
        cur.execute(
            "SELECT COUNT(*) FROM documents WHERE batch_id = ?",
            (batch_id,)
        )
        doc_count = cur.fetchone()[0]
        
        return {
            'id': batch[0],
            'status': batch[2],
            'total_assets': asset_count,
            'processed_assets': batch[4] or 0,
            'document_count': doc_count,
            'created_at': batch[1]
        } 