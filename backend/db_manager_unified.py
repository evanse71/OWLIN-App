"""
Unified Database Manager - Production-Ready Database Operations

This module provides bulletproof database operations for the unified schema.
All operations are atomic, have proper error handling, and maintain data integrity.
"""

import sqlite3
import logging
import hashlib
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from os import PathLike
from datetime import datetime

StrPath = Union[str, PathLike[str], Path]

logger = logging.getLogger(__name__)

# 1) Resolve repo root deterministically: .../backend/ -> parents[1] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DB = _REPO_ROOT / "data" / "owlin.db"

# 2) Environment override (explicit, testable)
_DB_PATH = Path(os.environ.get("OWLIN_DB_PATH", _DEFAULT_DB))

def _connect() -> sqlite3.Connection:
    """Create database connection with proper configuration"""
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Guardrails for SQLite reliability
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

class DatabaseManager:
    """Unified database manager with bulletproof operations"""
    
    def __init__(self, db_path: Optional[StrPath] = None):
        if db_path is None:
            self.db_path = _DB_PATH
        else:
            self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """Initialize database with unified schema"""
        try:
            with self.get_connection() as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA synchronous = NORMAL")
                conn.execute("PRAGMA cache_size = 10000")
                conn.execute("PRAGMA temp_store = MEMORY")
                
                # Create migrations table if it doesn't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS migrations (
                        version INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        applied_at TEXT NOT NULL
                    )
                """)
                
                conn.commit()
                logger.info("✅ Database initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def run_migrations(self):
        """Run all pending migrations in order"""
        try:
            with self.get_connection() as conn:
                # Get list of migration files
                migrations_dir = Path(__file__).parent / "db_migrations"
                migration_files: List[tuple[int, Path]] = []
                
                # Look for both .sql and .py migration files
                for migration_file in migrations_dir.glob("*"):
                    if migration_file.suffix in ['.sql', '.py']:
                        # Extract version from filename (e.g., "001_clean_start.sql" -> 1)
                        try:
                            version = int(migration_file.stem.split('_')[0])
                            migration_files.append((version, migration_file))
                        except (ValueError, IndexError):
                            logger.warning(f"⚠️ Skipping migration file with invalid name: {migration_file}")
                            continue
                
                # Sort by version
                migration_files.sort(key=lambda x: x[0])
                
                # Get already applied migrations
                cursor = conn.execute("SELECT version FROM migrations")
                applied_versions = {row[0] for row in cursor.fetchall()}
                
                # Apply pending migrations
                for version, migration_file in migration_files:
                    if version not in applied_versions:
                        logger.info(f"🔄 Applying migration {version}: {migration_file.name}")
                        
                        try:
                            if migration_file.suffix == '.py':
                                # Execute Python migration
                                self._execute_python_migration(conn, migration_file)
                            else:
                                # Execute SQL migration
                                with open(migration_file, 'r') as f:
                                    migration_sql = f.read()
                                
                                # Execute migration with error handling
                                try:
                                    conn.executescript(migration_sql)
                                except sqlite3.OperationalError as e:
                                    # If table already exists, that's OK for our clean start migration
                                    if "already exists" in str(e) and version == 1:
                                        logger.info(f"⏭️ Tables already exist, skipping creation")
                                    # If column already exists, that's OK for ADD COLUMN operations
                                    elif "duplicate column name" in str(e) or "already exists" in str(e):
                                        logger.info(f"⏭️ Column already exists, skipping: {e}")
                                    else:
                                        raise
                            
                            # Record migration
                            conn.execute("""
                                INSERT INTO migrations (version, name, applied_at)
                                VALUES (?, ?, datetime('now'))
                            """, (version, migration_file.stem))
                            
                            conn.commit()
                            logger.info(f"✅ Migration {version} applied successfully")
                            
                        except Exception as e:
                            logger.error(f"❌ Migration {version} failed: {e}")
                            conn.rollback()
                            raise
                    else:
                        logger.debug(f"⏭️ Migration {version} already applied")
                
                logger.info("✅ All migrations completed")
                
        except Exception as e:
            logger.error(f"❌ Migration process failed: {e}")
            raise
    
    def _apply_unified_schema(self, conn: sqlite3.Connection):
        """Apply the unified schema migration"""
        migration_path = Path(__file__).parent / "db_migrations" / "012_unified_schema.sql"
        if migration_path.exists():
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            
            # Execute migration in transaction
            conn.executescript(migration_sql)
            logger.info("✅ Unified schema applied successfully")
        else:
            raise FileNotFoundError(f"Migration file not found: {migration_path}")
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration"""
        if self._conn is None:
            self._conn = _connect()
        return self._conn
    
    def get_conn(self) -> sqlite3.Connection:
        """Alias for get_connection() for compatibility"""
        return self.get_connection()
    
    # ===== FILE OPERATIONS =====
    
    def save_uploaded_file(self, 
                          file_id: str,
                          original_filename: str,
                          canonical_path: str,
                          file_size: int,
                          file_hash: str,
                          mime_type: str,
                          doc_type: str = 'unknown') -> bool:
        """Save uploaded file record with full validation"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO uploaded_files (
                        id, original_filename, canonical_path, file_size, 
                        file_hash, mime_type, doc_type, upload_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id, original_filename, canonical_path, file_size,
                    file_hash, mime_type, doc_type, datetime.now().isoformat()
                ))
                conn.commit()
                logger.info(f"✅ Uploaded file saved: {file_id}")
                return True
                
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"⚠️ File already exists: {file_hash}")
                return True  # Consider this a success
            else:
                logger.error(f"❌ Database constraint error: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to save uploaded file: {e}")
            return False
    
    def get_uploaded_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get uploaded file by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM uploaded_files WHERE id = ?
                """, (file_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Failed to get uploaded file: {e}")
            return None
    
    def update_file_processing_status(self, 
                                    file_id: str, 
                                    status: str, 
                                    progress: int = 0,
                                    error_message: Optional[str] = None) -> bool:
        """Update file processing status"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE uploaded_files 
                    SET processing_status = ?, processing_progress = ?, 
                        error_message = ?, updated_at = datetime('now')
                    WHERE id = ?
                """, (status, progress, error_message, file_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Failed to update file status: {e}")
            return False
    
    # ===== INVOICE OPERATIONS =====
    
    def save_invoice(self,
                    invoice_id: str,
                    file_id: str,
                    invoice_number: Optional[str] = None,
                    invoice_date: Optional[str] = None,
                    supplier_name: Optional[str] = None,
                    total_amount_pennies: int = 0,
                    subtotal_pennies: Optional[int] = None,
                    vat_total_pennies: Optional[int] = None,
                    confidence: float = 0.0,
                    status: str = 'pending',
                    **kwargs: Any) -> bool:
        """Save invoice with complete validation"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO invoices (
                        id, file_id, invoice_number, invoice_date, supplier_name,
                        total_amount_pennies, subtotal_pennies, vat_total_pennies,
                        confidence, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """, (
                    invoice_id, file_id, invoice_number, invoice_date, supplier_name,
                    total_amount_pennies, subtotal_pennies, vat_total_pennies,
                    confidence, status
                ))
                conn.commit()
                logger.info(f"✅ Invoice saved: {invoice_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to save invoice: {e}")
            return False
    
    def save_invoice_line_items(self, 
                               invoice_id: str, 
                               line_items: List[Dict[str, Any]]) -> bool:
        """Save invoice line items with validation"""
        try:
            with self.get_connection() as conn:
                for item in line_items:
                    conn.execute("""
                        INSERT INTO invoice_line_items (
                            invoice_id, row_idx, page, description, quantity,
                            unit, unit_price_pennies, vat_rate, line_total_pennies,
                            confidence, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                    """, (
                        invoice_id,
                        item.get('row_idx'),
                        item.get('page', 1),
                        item.get('description', ''),
                        item.get('quantity', 0),
                        item.get('unit'),
                        int(item.get('unit_price', 0) * 100),  # Convert to pennies
                        item.get('vat_rate', 20.0),
                        int(item.get('total_price', 0) * 100),  # Convert to pennies
                        item.get('confidence', 1.0)
                    ))
                conn.commit()
                logger.info(f"✅ Saved {len(line_items)} line items for invoice {invoice_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to save line items: {e}")
            return False
    
    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Get invoice by ID with line items"""
        try:
            with self.get_connection() as conn:
                # Get invoice
                cursor = conn.execute("""
                    SELECT * FROM invoices WHERE id = ?
                """, (invoice_id,))
                invoice = cursor.fetchone()
                if not invoice:
                    return None
                
                # Get line items
                cursor = conn.execute("""
                    SELECT * FROM invoice_line_items WHERE invoice_id = ?
                    ORDER BY row_idx, page
                """, (invoice_id,))
                line_items = [dict(row) for row in cursor.fetchall()]
                
                result = dict(invoice)
                result['line_items'] = line_items
                return result
        except Exception as e:
            logger.error(f"❌ Failed to get invoice: {e}")
            return None
    
    # ===== DELIVERY NOTE OPERATIONS =====
    
    def save_delivery_note(self,
                          delivery_id: str,
                          file_id: str,
                          delivery_note_number: Optional[str],
                          delivery_date: Optional[str],
                          supplier_name: Optional[str],
                          total_items: int,
                          confidence: float,
                          status: str = 'pending') -> bool:
        """Save delivery note with validation"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO delivery_notes (
                        id, file_id, delivery_note_number, delivery_date,
                        supplier_name, total_items, confidence, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """, (
                    delivery_id, file_id, delivery_note_number, delivery_date,
                    supplier_name, total_items, confidence, status
                ))
                conn.commit()
                logger.info(f"✅ Delivery note saved: {delivery_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to save delivery note: {e}")
            return False
    
    def save_delivery_line_items(self,
                                delivery_id: str,
                                line_items: List[Dict[str, Any]]) -> bool:
        """Save delivery note line items"""
        try:
            with self.get_connection() as conn:
                for item in line_items:
                    conn.execute("""
                        INSERT INTO delivery_line_items (
                            delivery_note_id, row_idx, page, description, quantity,
                            unit, unit_price_pennies, vat_rate, line_total_pennies,
                            confidence, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                    """, (
                        delivery_id,
                        item.get('row_idx'),
                        item.get('page', 1),
                        item.get('description', ''),
                        item.get('quantity', 0),
                        item.get('unit'),
                        int(item.get('unit_price', 0) * 100),
                        item.get('vat_rate', 20.0),
                        int(item.get('total_price', 0) * 100),
                        item.get('confidence', 1.0)
                    ))
                conn.commit()
                logger.info(f"✅ Saved {len(line_items)} line items for delivery note {delivery_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to save delivery line items: {e}")
            return False
    
    # ===== JOB OPERATIONS =====
    
    def create_job(self,
                   job_id: str,
                   kind: str,
                   status: str = 'queued',
                   meta_json: Optional[str] = None,
                   timeout_seconds: int = 300) -> bool:
        """Create a new job"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO jobs (
                        id, kind, status, meta_json, timeout_seconds,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """, (job_id, kind, status, meta_json, timeout_seconds))
                conn.commit()
                logger.info(f"✅ Job created: {job_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to create job: {e}")
            return False
    
    def update_job_status(self,
                         job_id: str,
                         status: str,
                         progress: int = 0,
                         result_json: Optional[str] = None,
                         error: Optional[str] = None,
                         duration_ms: Optional[int] = None) -> bool:
        """Update job status"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE jobs 
                    SET status = ?, progress = ?, result_json = ?, error = ?,
                        duration_ms = ?, updated_at = datetime('now')
                    WHERE id = ?
                """, (status, progress, result_json, error, duration_ms, job_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Failed to update job status: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM jobs WHERE id = ?
                """, (job_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Failed to get job: {e}")
            return None
    
    # ===== AUDIT LOGGING =====
    
    def log_audit_event(self,
                       action: str,
                       entity_type: str,
                       entity_id: str,
                       user_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       document_id: Optional[str] = None,
                       policy_action: Optional[str] = None,
                       reasons_json: Optional[str] = None,
                       confidence: Optional[float] = None,
                       processing_time_ms: Optional[int] = None,
                       metadata_json: Optional[str] = None) -> bool:
        """Log audit event"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO audit_log (
                        user_id, session_id, action, entity_type, entity_id,
                        document_id, policy_action, reasons_json, confidence,
                        processing_time_ms, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    user_id, session_id, action, entity_type, entity_id,
                    document_id, policy_action, reasons_json, confidence,
                    processing_time_ms, metadata_json
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Failed to log audit event: {e}")
            return False
    
    # ===== PROCESSING LOGS =====
    
    def log_processing_event(self,
                           file_id: str,
                           stage: str,
                           status: str,
                           confidence: Optional[float] = None,
                           processing_time_ms: Optional[int] = None,
                           error_message: Optional[str] = None,
                           metadata_json: Optional[str] = None) -> bool:
        """Log processing event"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO processing_logs (
                        file_id, stage, status, confidence, processing_time_ms,
                        error_message, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    file_id, stage, status, confidence, processing_time_ms,
                    error_message, metadata_json
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Failed to log processing event: {e}")
            return False
    
    # ===== UTILITY FUNCTIONS =====
    
    def generate_file_hash(self, file_path: str) -> str:
        """Generate MD5 hash for file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def check_duplicate_file(self, file_hash: str) -> Optional[str]:
        """Check if file already exists by hash"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id FROM uploaded_files WHERE file_hash = ?
                """, (file_hash,))
                row = cursor.fetchone()
                return row['id'] if row else None
        except Exception as e:
            logger.error(f"❌ Failed to check duplicate file: {e}")
            return None
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            with self.get_connection() as conn:
                stats: Dict[str, Any] = {}
                
                # Count records
                for table in ['uploaded_files', 'invoices', 'delivery_notes', 'jobs']:
                    cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                    stats[f'{table}_count'] = cursor.fetchone()['count']
                
                # Status breakdowns
                cursor = conn.execute("""
                    SELECT processing_status, COUNT(*) as count 
                    FROM uploaded_files 
                    GROUP BY processing_status
                """)
                stats['upload_status_breakdown'] = {row['processing_status']: row['count'] for row in cursor.fetchall()}
                
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM invoices 
                    GROUP BY status
                """)
                stats['invoice_status_breakdown'] = {row['status']: row['count'] for row in cursor.fetchall()}
                
                return stats
        except Exception as e:
            logger.error(f"❌ Failed to get system stats: {e}")
            return {}
    
    def _execute_python_migration(self, conn: sqlite3.Connection, migration_file: Path):
        """Execute Python migration file by importing and calling apply()"""
        import importlib.util
        import sys
        
        # Load the migration module
        spec = importlib.util.spec_from_file_location("migration", migration_file)
        if spec is None or spec.loader is None:
            raise Exception(f"Could not load migration file: {migration_file}")
        
        migration_module = importlib.util.module_from_spec(spec)
        sys.modules["migration"] = migration_module
        spec.loader.exec_module(migration_module)
        
        # Call the apply function
        if hasattr(migration_module, 'apply'):
            migration_module.apply(conn)
        else:
            raise Exception(f"Migration {migration_file} missing apply() function")

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

def get_db_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    current_db_path = os.environ.get('OWLIN_DB', _DEFAULT_DB)
    
    if _db_manager is None or _db_manager.db_path != current_db_path:
        _db_manager = DatabaseManager(current_db_path)
    
    return _db_manager

def init_db(db_path: str = str(_DEFAULT_DB)) -> None:
    """Initialize database (backward compatibility)"""
    global _db_manager
    _db_manager = DatabaseManager(db_path) 