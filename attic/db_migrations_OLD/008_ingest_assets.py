import sqlite3

def apply(conn: sqlite3.Connection):
    """Add ingest asset tracking and document assembly tables"""
    cur = conn.cursor()
    
    # Check if tables already exist
    cur.execute("PRAGMA table_info(ingest_batches)")
    if cur.fetchall():
        print("Ingest tables already exist, skipping")
        return
    
    cur.executescript("""
    PRAGMA foreign_keys=ON;
    
    -- Track upload batches
    CREATE TABLE IF NOT EXISTS ingest_batches (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        uploader TEXT,
        source_hint TEXT
    );
    
    -- Track individual assets (files)
    CREATE TABLE IF NOT EXISTS ingest_assets (
        id TEXT PRIMARY KEY,
        batch_id TEXT NOT NULL,
        mime TEXT NOT NULL,
        path TEXT NOT NULL,
        width INTEGER,
        height INTEGER,
        dpi INTEGER,
        checksum_sha256 TEXT NOT NULL,
        exif_ts TEXT,
        header_id TEXT,
        FOREIGN KEY(batch_id) REFERENCES ingest_batches(id) ON DELETE CASCADE
    );
    
    -- Document sets (assembled from multiple assets)
    CREATE TABLE IF NOT EXISTS doc_sets (
        id TEXT PRIMARY KEY,
        batch_id TEXT NOT NULL,
        order_index INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(batch_id) REFERENCES ingest_batches(id) ON DELETE CASCADE
    );
    
    -- Documents (invoices/DNs from doc sets)
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        batch_id TEXT NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN ('invoice', 'delivery_note')),
        vendor_id TEXT,
        header_id TEXT,
        page_count INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(batch_id) REFERENCES ingest_batches(id) ON DELETE CASCADE
    );
    
    -- Page order within documents
    CREATE TABLE IF NOT EXISTS document_pages (
        document_id TEXT NOT NULL,
        asset_id TEXT NOT NULL,
        page_order INTEGER NOT NULL,
        PRIMARY KEY(document_id, asset_id),
        FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
        FOREIGN KEY(asset_id) REFERENCES ingest_assets(id) ON DELETE CASCADE
    );
    
    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_ingest_assets_batch ON ingest_assets(batch_id);
    CREATE INDEX IF NOT EXISTS idx_ingest_assets_header ON ingest_assets(header_id);
    CREATE INDEX IF NOT EXISTS idx_doc_sets_batch ON doc_sets(batch_id);
    CREATE INDEX IF NOT EXISTS idx_documents_batch ON documents(batch_id);
    CREATE INDEX IF NOT EXISTS idx_documents_header ON documents(header_id);
    CREATE INDEX IF NOT EXISTS idx_document_pages_doc ON document_pages(document_id);
    """)
    
    conn.commit()
    print("Ingest asset tables created")

def rollback(conn: sqlite3.Connection):
    """Remove ingest asset tracking tables"""
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS document_pages;
    DROP TABLE IF EXISTS documents;
    DROP TABLE IF EXISTS doc_sets;
    DROP TABLE IF EXISTS ingest_assets;
    DROP TABLE IF EXISTS ingest_batches;
    """)
    conn.commit()
    print("Ingest asset tables removed") 