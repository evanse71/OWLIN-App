#!/usr/bin/env python3
"""
Support Pack Service - Generate debug packages for invoices
"""
import json
import zipfile
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import tempfile
import shutil

from backend.db_manager_unified import get_db_manager

class SupportPackService:
    """Generates comprehensive debug packages for invoices"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.output_dir = Path("backups/support_packs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_support_pack(self, invoice_id: str) -> str:
        """
        Generate support pack for invoice
        Returns path to generated zip file
        """
        conn = self.db.get_connection()
        
        # Create temporary directory for pack contents
        with tempfile.TemporaryDirectory() as temp_dir:
            pack_dir = Path(temp_dir) / f"support_pack_{invoice_id}"
            pack_dir.mkdir(exist_ok=True)
            
            # Collect all data
            self._collect_invoice_metadata(conn, invoice_id, pack_dir)
            self._collect_ocr_results(conn, invoice_id, pack_dir)
            self._collect_header_fingerprints(conn, invoice_id, pack_dir)
            self._collect_canonical_outputs(conn, invoice_id, pack_dir)
            self._collect_solver_decisions(conn, invoice_id, pack_dir)
            self._collect_verdicts(conn, invoice_id, pack_dir)
            self._collect_pairing_reasons(conn, invoice_id, pack_dir)
            self._collect_asset_files(conn, invoice_id, pack_dir)
            
            # Create zip file
            zip_path = self.output_dir / f"{invoice_id}.zip"
            self._create_zip_archive(pack_dir, zip_path)
            
            return str(zip_path)
    
    def _collect_invoice_metadata(self, conn: sqlite3.Connection, invoice_id: str, pack_dir: Path):
        """Collect basic invoice metadata"""
        cur = conn.cursor()
        cur.execute("""
            SELECT id, supplier_name, invoice_no, date_iso, currency, 
                   status, total_inc, ocr_avg_conf, ocr_min_conf, created_at
            FROM invoices WHERE id = ?
        """, (invoice_id,))
        
        invoice_data = cur.fetchone()
        if invoice_data:
            metadata = {
                'invoice_id': invoice_data[0],
                'supplier_name': invoice_data[1],
                'invoice_no': invoice_data[2],
                'date_iso': invoice_data[3],
                'currency': invoice_data[4],
                'status': invoice_data[5],
                'total_inc': invoice_data[6],
                'ocr_avg_conf': invoice_data[7],
                'ocr_min_conf': invoice_data[8],
                'created_at': invoice_data[9],
                'pack_generated_at': datetime.now().isoformat()
            }
            
            with open(pack_dir / "invoice_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
    
    def _collect_ocr_results(self, conn: sqlite3.Connection, invoice_id: str, pack_dir: Path):
        """Collect OCR text and confidence data per page"""
        cur = conn.cursor()
        cur.execute("""
            SELECT page_number, ocr_text, ocr_avg_conf_page, ocr_min_conf_line
            FROM invoice_pages 
            WHERE invoice_id = ?
            ORDER BY page_number
        """, (invoice_id,))
        
        ocr_dir = pack_dir / "ocr_results"
        ocr_dir.mkdir(exist_ok=True)
        
        for row in cur.fetchall():
            page_no, ocr_text, avg_conf, min_conf = row
            
            page_data = {
                'page_number': page_no,
                'ocr_text': ocr_text or '',
                'ocr_avg_conf_page': avg_conf,
                'ocr_min_conf_line': min_conf,
                'extracted_at': datetime.now().isoformat()
            }
            
            with open(ocr_dir / f"page_{page_no}_ocr.json", 'w') as f:
                json.dump(page_data, f, indent=2)
    
    def _collect_header_fingerprints(self, conn: sqlite3.Connection, invoice_id: str, pack_dir: Path):
        """Collect header fingerprint data"""
        cur = conn.cursor()
        cur.execute("""
            SELECT ia.header_id, ia.path, ia.checksum_sha256
            FROM document_pages dp
            JOIN ingest_assets ia ON dp.asset_id = ia.id
            WHERE dp.document_id = ?
            ORDER BY dp.page_order
        """, (invoice_id,))
        
        fingerprints = []
        for row in cur.fetchall():
            fingerprints.append({
                'header_id': row[0],
                'asset_path': row[1],
                'checksum': row[2]
            })
        
        if fingerprints:
            with open(pack_dir / "header_fingerprints.json", 'w') as f:
                json.dump(fingerprints, f, indent=2)
    
    def _collect_canonical_outputs(self, conn: sqlite3.Connection, invoice_id: str, pack_dir: Path):
        """Collect canonical quantity parsing results"""
        cur = conn.cursor()
        cur.execute("""
            SELECT id, sku, description, quantity, canonical_quantities, line_flags
            FROM invoice_items 
            WHERE invoice_id = ?
            ORDER BY id
        """, (invoice_id,))
        
        canonical_data = []
        for row in cur.fetchall():
            line_data = {
                'line_id': row[0],
                'sku': row[1],
                'description': row[2],
                'raw_quantity': row[3],
                'canonical_quantities': json.loads(row[4]) if row[4] else None,
                'line_flags': json.loads(row[5]) if row[5] else []
            }
            canonical_data.append(line_data)
        
        if canonical_data:
            with open(pack_dir / "canonical_parsing.json", 'w') as f:
                json.dump(canonical_data, f, indent=2)
    
    def _collect_solver_decisions(self, conn: sqlite3.Connection, invoice_id: str, pack_dir: Path):
        """Collect discount solver decisions and residuals"""
        cur = conn.cursor()
        cur.execute("""
            SELECT id, sku, unit_price, line_total, 
                   discount_kind, discount_value, discount_residual_pennies
            FROM invoice_items 
            WHERE invoice_id = ? AND discount_kind IS NOT NULL
            ORDER BY id
        """, (invoice_id,))
        
        solver_data = []
        for row in cur.fetchall():
            solver_data.append({
                'line_id': row[0],
                'sku': row[1],
                'unit_price': row[2],
                'line_total': row[3],
                'discount_hypothesis': {
                    'kind': row[4],
                    'value': row[5],
                    'residual_pennies': row[6]
                }
            })
        
        if solver_data:
            with open(pack_dir / "discount_solver.json", 'w') as f:
                json.dump(solver_data, f, indent=2)
    
    def _collect_verdicts(self, conn: sqlite3.Connection, invoice_id: str, pack_dir: Path):
        """Collect line verdicts"""
        cur = conn.cursor()
        cur.execute("""
            SELECT id, sku, line_verdict, line_flags
            FROM invoice_items 
            WHERE invoice_id = ?
            ORDER BY id
        """, (invoice_id,))
        
        verdicts_data = []
        for row in cur.fetchall():
            verdicts_data.append({
                'line_id': row[0],
                'sku': row[1],
                'verdict': row[2],
                'flags': json.loads(row[3]) if row[3] else []
            })
        
        if verdicts_data:
            with open(pack_dir / "verdicts.json", 'w') as f:
                json.dump(verdicts_data, f, indent=2)
    
    def _collect_pairing_reasons(self, conn: sqlite3.Connection, invoice_id: str, pack_dir: Path):
        """Collect pairing match reasons"""
        cur = conn.cursor()
        cur.execute("""
            SELECT ml.dn_id, ml.score, mli.invoice_item_id, 
                   mli.dn_item_id, mli.reason, mli.qty_match_pct
            FROM match_links ml
            LEFT JOIN match_link_items mli ON ml.id = mli.link_id
            WHERE ml.invoice_id = ?
            ORDER BY ml.score DESC, mli.invoice_item_id
        """, (invoice_id,))
        
        pairing_data = []
        for row in cur.fetchall():
            pairing_data.append({
                'dn_id': row[0],
                'doc_score': row[1],
                'invoice_item_id': row[2],
                'dn_item_id': row[3],
                'reason': row[4],
                'qty_match_pct': row[5]
            })
        
        if pairing_data:
            with open(pack_dir / "pairing_reasons.json", 'w') as f:
                json.dump(pairing_data, f, indent=2)
    
    def _collect_asset_files(self, conn: sqlite3.Connection, invoice_id: str, pack_dir: Path):
        """Collect original asset files"""
        cur = conn.cursor()
        cur.execute("""
            SELECT ia.path, ia.mime, dp.page_order
            FROM document_pages dp
            JOIN ingest_assets ia ON dp.asset_id = ia.id
            WHERE dp.document_id = ?
            ORDER BY dp.page_order
        """, (invoice_id,))
        
        assets_dir = pack_dir / "original_assets"
        assets_dir.mkdir(exist_ok=True)
        
        for row in cur.fetchall():
            asset_path, mime, page_order = row
            
            if Path(asset_path).exists():
                # Copy asset with descriptive name
                ext = Path(asset_path).suffix
                dest_name = f"page_{page_order:02d}{ext}"
                shutil.copy2(asset_path, assets_dir / dest_name)
    
    def _create_zip_archive(self, source_dir: Path, zip_path: Path) -> None:
        """Create zip archive from directory"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)

class QuarantineService:
    """Manages quarantined files and promotion"""
    
    def __init__(self):
        self.db = get_db_manager()
    
    def quarantine_asset(self, asset_id: str, reason: str, details: Optional[Dict] = None):
        """Quarantine an asset with reason"""
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE ingest_assets 
            SET quarantine_reason = ?, quarantine_details = ?, quarantine_at = ?
            WHERE id = ?
        """, (reason, json.dumps(details) if details else None, 
              datetime.now().isoformat(), asset_id))
        
        conn.commit()
    
    def list_quarantined_assets(self) -> List[Dict[str, Any]]:
        """List all quarantined assets"""
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, path, mime, quarantine_reason, quarantine_details, quarantine_at
            FROM ingest_assets 
            WHERE quarantine_reason IS NOT NULL
            ORDER BY quarantine_at DESC
        """)
        
        quarantined = []
        for row in cur.fetchall():
            quarantined.append({
                'asset_id': row[0],
                'filename': Path(row[1]).name,
                'mime': row[2],
                'reason': row[3],
                'details': json.loads(row[4]) if row[4] else None,
                'quarantined_at': row[5]
            })
        
        return quarantined
    
    def promote_asset(self, asset_id: str) -> bool:
        """Promote asset from quarantine back to processing"""
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE ingest_assets 
            SET quarantine_reason = NULL, quarantine_details = NULL, quarantine_at = NULL
            WHERE id = ?
        """, (asset_id,))
        
        conn.commit()
        return cur.rowcount > 0

# Global instances
_support_pack_service: Optional[SupportPackService] = None
_quarantine_service: Optional[QuarantineService] = None

def get_support_pack_service() -> SupportPackService:
    """Get global support pack service instance"""
    global _support_pack_service
    if _support_pack_service is None:
        _support_pack_service = SupportPackService()
    return _support_pack_service

def get_quarantine_service() -> QuarantineService:
    """Get global quarantine service instance"""
    global _quarantine_service
    if _quarantine_service is None:
        _quarantine_service = QuarantineService()
    return _quarantine_service

# Add missing cleanup function for tests
def cleanup_old_support_packs(dir_path: str, keep: int = 10) -> None:
    """Clean up old support pack files, keeping only the most recent ones"""
    p = Path(dir_path)
    if not p.exists(): 
        return
    
    zips = sorted(p.glob("*.zip"), key=lambda x: x.stat().st_mtime, reverse=True)
    for z in zips[keep:]:
        try: 
            z.unlink()
        except Exception: 
            pass
