#!/usr/bin/env python3
"""
Database migration script to add new columns for multi-page PDF support
"""

import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "data/owlin.db"

def migrate_database():
    """Add new columns to the invoices table"""
    logger.info("🚀 Starting database migration...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(invoices)")
        columns = [column[1] for column in cursor.fetchall()]
        
        logger.info(f"📋 Current columns: {columns}")
        
        # Add new columns if they don't exist
        new_columns = [
            ("delivery_note_required", "BOOLEAN DEFAULT TRUE"),
            ("ocr_text", "TEXT"),
            ("parent_pdf_filename", "TEXT"),
            ("page_number", "INTEGER DEFAULT 1"),
            ("is_utility_invoice", "BOOLEAN DEFAULT FALSE"),
            ("utility_keywords", "TEXT")
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in columns:
                logger.info(f"🔄 Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE invoices ADD COLUMN {column_name} {column_type}")
                logger.info(f"✅ Added column: {column_name}")
            else:
                logger.info(f"✅ Column already exists: {column_name}")
        
        # Update status column to include new values
        logger.info("🔄 Updating status column constraints...")
        cursor.execute("""
            UPDATE invoices 
            SET status = CASE 
                WHEN status = 'pending' THEN 'waiting'
                ELSE status 
            END
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Database migration completed successfully!")
        
        # Verify the migration
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(invoices)")
        columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"📋 Final columns: {columns}")
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Database migration failed: {str(e)}")
        raise Exception(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    migrate_database() 