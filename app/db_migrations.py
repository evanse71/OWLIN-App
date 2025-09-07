"""
Database migrations for Owlin App
Handles creation and updates of database tables with idempotent operations.
"""
import sqlite3
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path, check_same_thread=False)

def run_migrations():
    """Run all database migrations in order."""
    migrations = [
        create_issues_table,
        create_audit_log_table,
        create_pairings_table,
        create_uploaded_files_table,
        create_invoices_table,
        create_invoice_line_items_table,
        create_delivery_notes_table,
        add_missing_columns,
        create_indexes
    ]
    
    for migration in migrations:
        try:
            migration()
            logger.info(f"Migration {migration.__name__} completed successfully")
        except Exception as e:
            logger.error(f"Migration {migration.__name__} failed: {e}")
            raise

def create_issues_table():
    """Create issues table for flagged invoice problems."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL,
            line_item_id INTEGER,
            issue_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium',
            description TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            created_by TEXT,
            created_at TEXT NOT NULL,
            resolved_by TEXT,
            resolved_at TEXT,
            resolution_notes TEXT,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id),
            FOREIGN KEY (line_item_id) REFERENCES invoice_line_items (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_audit_log_table():
    """Create audit log table for tracking all mutations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            timestamp TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def create_pairings_table():
    """Create pairings table for invoice-delivery note matching."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pairings (
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL,
            delivery_note_id TEXT NOT NULL,
            similarity_score REAL NOT NULL,
            status TEXT DEFAULT 'suggested',
            created_at TEXT NOT NULL,
            confirmed_by TEXT,
            confirmed_at TEXT,
            rejected_by TEXT,
            rejected_at TEXT,
            rejection_reason TEXT,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id),
            FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_uploaded_files_table():
    """Create uploaded files table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            upload_timestamp TEXT NOT NULL,
            processing_status TEXT DEFAULT 'pending',
            extracted_text TEXT,
            confidence REAL,
            processed_images INTEGER,
            extraction_timestamp TEXT,
            user_id TEXT,
            upload_session_id TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def create_invoices_table():
    """Create invoices table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            invoice_number TEXT,
            invoice_date TEXT,
            supplier TEXT,
            total_amount_pennies INTEGER,
            currency TEXT DEFAULT 'GBP',
            status TEXT DEFAULT 'pending',
            file_id TEXT,
            extracted_text TEXT,
            confidence REAL,
            upload_timestamp TEXT NOT NULL,
            processing_status TEXT DEFAULT 'pending',
            vat_rate REAL DEFAULT 0.2,
            net_amount_pennies INTEGER,
            vat_amount_pennies INTEGER,
            gross_amount_pennies INTEGER,
            user_id TEXT,
            FOREIGN KEY (file_id) REFERENCES uploaded_files (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_invoice_line_items_table():
    """Create invoice line items table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_line_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT NOT NULL,
            item TEXT NOT NULL,
            qty REAL NOT NULL,
            unit_price_pennies INTEGER NOT NULL,
            total_pennies INTEGER NOT NULL,
            unit_descriptor TEXT,
            normalized_units INTEGER,
            delivery_qty REAL,
            flagged INTEGER DEFAULT 0,
            source TEXT DEFAULT 'invoice',
            upload_timestamp TEXT NOT NULL,
            confidence REAL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_delivery_notes_table():
    """Create delivery notes table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS delivery_notes (
            id TEXT PRIMARY KEY,
            delivery_number TEXT,
            delivery_date TEXT,
            supplier TEXT,
            invoice_id TEXT,
            file_id TEXT,
            extracted_text TEXT,
            confidence REAL,
            upload_timestamp TEXT NOT NULL,
            processing_status TEXT DEFAULT 'pending',
            total_amount_pennies INTEGER,
            currency TEXT DEFAULT 'GBP',
            user_id TEXT,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id),
            FOREIGN KEY (file_id) REFERENCES uploaded_files (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_missing_columns():
    """Add missing columns to existing tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Add missing columns to invoices table
    columns_to_add = [
        ("invoices", "total_amount_pennies", "INTEGER"),
        ("invoices", "currency", "TEXT DEFAULT 'GBP'"),
        ("invoices", "vat_rate", "REAL DEFAULT 0.2"),
        ("invoices", "net_amount_pennies", "INTEGER"),
        ("invoices", "vat_amount_pennies", "INTEGER"),
        ("invoices", "gross_amount_pennies", "INTEGER"),
        ("invoices", "user_id", "TEXT"),
        ("invoice_line_items", "unit_price_pennies", "INTEGER"),
        ("invoice_line_items", "total_pennies", "INTEGER"),
        ("invoice_line_items", "unit_descriptor", "TEXT"),
        ("invoice_line_items", "normalized_units", "INTEGER"),
        ("invoice_line_items", "confidence", "REAL"),
        ("uploaded_files", "user_id", "TEXT"),
        ("uploaded_files", "upload_session_id", "TEXT"),
        ("delivery_notes", "total_amount_pennies", "INTEGER"),
        ("delivery_notes", "currency", "TEXT DEFAULT 'GBP'"),
        ("delivery_notes", "user_id", "TEXT")
    ]
    
    for table, column, definition in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            logger.info(f"Added column {column} to {table}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info(f"Column {column} already exists in {table}")
            else:
                raise
    
    conn.commit()
    conn.close()

def create_indexes():
    """Create database indexes for performance."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_invoices_supplier ON invoices(supplier)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date)",
        "CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice_id ON invoice_line_items(invoice_id)",
        "CREATE INDEX IF NOT EXISTS idx_invoice_line_items_flagged ON invoice_line_items(flagged)",
        "CREATE INDEX IF NOT EXISTS idx_issues_invoice_id ON issues(invoice_id)",
        "CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status)",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id)",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_pairings_invoice_id ON pairings(invoice_id)",
        "CREATE INDEX IF NOT EXISTS idx_pairings_status ON pairings(status)",
        "CREATE INDEX IF NOT EXISTS idx_uploaded_files_status ON uploaded_files(processing_status)"
    ]
    
    for index_sql in indexes:
        try:
            cursor.execute(index_sql)
            logger.info(f"Created index: {index_sql}")
        except Exception as e:
            logger.warning(f"Failed to create index: {e}")
    
    conn.commit()
    conn.close()

def log_audit_event(user_id: str, action: str, entity_type: str, entity_id: str, 
                   old_values: Dict = None, new_values: Dict = None, 
                   ip_address: str = None, user_agent: str = None):
    """Log an audit event."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO audit_log 
        (user_id, action, entity_type, entity_id, old_values, new_values, 
         timestamp, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, action, entity_type, entity_id,
        str(old_values) if old_values else None,
        str(new_values) if new_values else None,
        datetime.now().isoformat(),
        ip_address, user_agent
    ))
    
    conn.commit()
    conn.close()

def get_current_user_id():
    """Get current user ID from session or default to system."""
    # In a real implementation, this would get the user from the session
    # For now, return a default system user
    return "system"

def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    ''', (table_name,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def get_table_columns(table_name: str) -> List[str]:
    """Get column names for a table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    
    return columns

# Run migrations on import
if __name__ == "__main__":
    run_migrations()
else:
    # Auto-run migrations when module is imported
    try:
        run_migrations()
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
