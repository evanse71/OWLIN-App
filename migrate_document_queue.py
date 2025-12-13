#!/usr/bin/env python3
"""
Migration script to add document queue columns to existing database.
"""

import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "data/owlin.db"

def migrate_document_queue():
    """Add document queue columns to existing tables"""
    logger.info("🚀 Starting document queue migration...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if columns already exist in uploaded_files
        cursor.execute("PRAGMA table_info(uploaded_files)")
        uploaded_files_columns = [column[1] for column in cursor.fetchall()]
        
        # Add reviewed_by and reviewed_at to uploaded_files if they don't exist
        if 'reviewed_by' not in uploaded_files_columns:
            logger.info("🔄 Adding reviewed_by column to uploaded_files")
            cursor.execute("ALTER TABLE uploaded_files ADD COLUMN reviewed_by TEXT")
        
        if 'reviewed_at' not in uploaded_files_columns:
            logger.info("🔄 Adding reviewed_at column to uploaded_files")
            cursor.execute("ALTER TABLE uploaded_files ADD COLUMN reviewed_at TEXT")
        
        # Check if columns already exist in invoices
        cursor.execute("PRAGMA table_info(invoices)")
        invoices_columns = [column[1] for column in cursor.fetchall()]
        
        # Add reviewed_by and reviewed_at to invoices if they don't exist
        if 'reviewed_by' not in invoices_columns:
            logger.info("🔄 Adding reviewed_by column to invoices")
            cursor.execute("ALTER TABLE invoices ADD COLUMN reviewed_by TEXT")
        
        if 'reviewed_at' not in invoices_columns:
            logger.info("🔄 Adding reviewed_at column to invoices")
            cursor.execute("ALTER TABLE invoices ADD COLUMN reviewed_at TEXT")
        
        # Check if columns already exist in delivery_notes
        cursor.execute("PRAGMA table_info(delivery_notes)")
        delivery_notes_columns = [column[1] for column in cursor.fetchall()]
        
        # Add reviewed_by and reviewed_at to delivery_notes if they don't exist
        if 'reviewed_by' not in delivery_notes_columns:
            logger.info("🔄 Adding reviewed_by column to delivery_notes")
            cursor.execute("ALTER TABLE delivery_notes ADD COLUMN reviewed_by TEXT")
        
        if 'reviewed_at' not in delivery_notes_columns:
            logger.info("🔄 Adding reviewed_at column to delivery_notes")
            cursor.execute("ALTER TABLE delivery_notes ADD COLUMN reviewed_at TEXT")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Document queue migration completed successfully!")
        
        # Verify the migration
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(uploaded_files)")
        uploaded_files_columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"📋 uploaded_files columns: {uploaded_files_columns}")
        
        cursor.execute("PRAGMA table_info(invoices)")
        invoices_columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"📋 invoices columns: {invoices_columns}")
        
        cursor.execute("PRAGMA table_info(delivery_notes)")
        delivery_notes_columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"📋 delivery_notes columns: {delivery_notes_columns}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    migrate_document_queue() 