#!/usr/bin/env python3
"""
Support Pack Export Service

Exports diagnostic information including database, audit logs, config, and recent OCR results
"""

import json
import zipfile
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SupportPackExporter:
    """Support pack exporter for diagnostic information"""
    
    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent
        self.base_path = base_path
        self.db_path = base_path / "owlin.db"
        self.audit_log_path = base_path / "audit.log"
        self.config_path = base_path / "ocr" / "ocr_config.json"
        self.ocr_metrics_path = base_path / "data" / "ocr_metrics.log"
    
    def export_support_pack(self, output_path: Optional[Path] = None) -> Path:
        """
        Export a complete support pack
        
        Args:
            output_path: Output path for the zip file
            
        Returns:
            Path to the exported support pack
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.base_path / "support_packs" / f"support_pack_{timestamp}.zip"
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📦 Creating support pack: {output_path}")
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. Database (read-only copy)
            if self.db_path.exists():
                self._add_database_snapshot(zipf)
            else:
                logger.warning("⚠️ Database not found")
            
            # 2. Audit log
            if self.audit_log_path.exists():
                zipf.write(self.audit_log_path, "audit.log")
                logger.info("✅ Added audit.log")
            else:
                logger.warning("⚠️ Audit log not found")
            
            # 3. OCR config
            if self.config_path.exists():
                zipf.write(self.config_path, "ocr_config.json")
                logger.info("✅ Added ocr_config.json")
            else:
                logger.warning("⚠️ OCR config not found")
            
            # 4. Recent OCR results (last 50)
            self._add_recent_ocr_results(zipf)
            
            # 5. System info
            self._add_system_info(zipf)
            
            # 6. OCR metrics
            if self.ocr_metrics_path.exists():
                zipf.write(self.ocr_metrics_path, "ocr_metrics.log")
                logger.info("✅ Added ocr_metrics.log")
        
        logger.info(f"✅ Support pack created: {output_path}")
        return output_path
    
    def _add_database_snapshot(self, zipf: zipfile.ZipFile):
        """Add a read-only snapshot of the database"""
        try:
            # Create a temporary copy for export
            temp_db_path = self.base_path / "temp_export.db"
            
            # Copy database
            import shutil
            shutil.copy2(self.db_path, temp_db_path)
            
            # Add to zip
            zipf.write(temp_db_path, "owlin.db")
            
            # Clean up
            temp_db_path.unlink()
            
            logger.info("✅ Added database snapshot")
            
        except Exception as e:
            logger.error(f"❌ Failed to add database snapshot: {e}")
    
    def _add_recent_ocr_results(self, zipf: zipfile.ZipFile):
        """Add recent OCR results from audit log"""
        try:
            if not self.db_path.exists():
                return
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Get last 50 OCR processing events
            cursor.execute("""
                SELECT metadata_json, created_at
                FROM audit_log 
                WHERE action = 'OCR_PROCESSING' 
                ORDER BY created_at DESC 
                LIMIT 50
            """)
            
            results = []
            for row in cursor.fetchall():
                metadata_json, created_at = row
                if metadata_json:
                    try:
                        metadata = json.loads(metadata_json)
                        results.append({
                            "created_at": created_at,
                            "metadata": metadata
                        })
                    except json.JSONDecodeError:
                        continue
            
            conn.close()
            
            # Write to JSON file in zip
            ocr_results_data = {
                "exported_at": datetime.now().isoformat(),
                "total_results": len(results),
                "results": results
            }
            
            zipf.writestr("recent_ocr_results.json", json.dumps(ocr_results_data, indent=2))
            logger.info(f"✅ Added {len(results)} recent OCR results")
            
        except Exception as e:
            logger.error(f"❌ Failed to add recent OCR results: {e}")
    
    def _add_system_info(self, zipf: zipfile.ZipFile):
        """Add system information"""
        try:
            import platform
            import sys
            
            system_info = {
                "exported_at": datetime.now().isoformat(),
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor()
                },
                "python": {
                    "version": sys.version,
                    "executable": sys.executable
                },
                "paths": {
                    "base_path": str(self.base_path),
                    "db_path": str(self.db_path),
                    "config_path": str(self.config_path)
                }
            }
            
            zipf.writestr("system_info.json", json.dumps(system_info, indent=2))
            logger.info("✅ Added system info")
            
        except Exception as e:
            logger.error(f"❌ Failed to add system info: {e}")
    
    def get_support_pack_info(self) -> Dict[str, Any]:
        """Get information about what would be included in a support pack"""
        info = {
            "database": self.db_path.exists(),
            "audit_log": self.audit_log_path.exists(),
            "config": self.config_path.exists(),
            "ocr_metrics": self.ocr_metrics_path.exists(),
            "base_path": str(self.base_path)
        }
        
        # Count recent OCR results
        if self.db_path.exists():
            try:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM audit_log 
                    WHERE action = 'OCR_PROCESSING'
                """)
                info["recent_ocr_count"] = cursor.fetchone()[0]
                conn.close()
            except Exception:
                info["recent_ocr_count"] = 0
        
        return info

# Global exporter instance
_support_pack_exporter: Optional[SupportPackExporter] = None

def get_support_pack_exporter() -> SupportPackExporter:
    """Get global support pack exporter instance"""
    global _support_pack_exporter
    if _support_pack_exporter is None:
        _support_pack_exporter = SupportPackExporter()
    return _support_pack_exporter
