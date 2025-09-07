import sqlite3

def _has_table(cur, name):
    cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,))
    return cur.fetchone() is not None

def apply(conn: sqlite3.Connection):
    c = conn.cursor()

    if not _has_table(c, "ingest_batches"):
        c.execute("""CREATE TABLE ingest_batches(
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            uploader TEXT,
            source_hint TEXT
        )""")

    if not _has_table(c, "ingest_assets"):
        c.execute("""CREATE TABLE ingest_assets(
            id TEXT PRIMARY KEY,
            batch_id TEXT,
            mime TEXT NOT NULL,
            path TEXT NOT NULL,
            width INTEGER, height INTEGER, dpi INTEGER,
            checksum_sha256 TEXT,
            exif_ts TEXT,
            FOREIGN KEY(batch_id) REFERENCES ingest_batches(id)
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_assets_batch ON ingest_assets(batch_id)")

    if not _has_table(c, "doc_sets"):
        c.execute("""CREATE TABLE doc_sets(
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            order_index INTEGER NOT NULL
        )""")

    if not _has_table(c, "documents"):
        c.execute("""CREATE TABLE documents(
            id TEXT PRIMARY KEY,
            batch_id TEXT,
            kind TEXT,           -- 'invoice' | 'delivery_note' | 'other'
            vendor_id TEXT,
            header_id TEXT,
            page_count INTEGER DEFAULT 0
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_documents_kind ON documents(kind)")

    if not _has_table(c, "document_pages"):
        c.execute("""CREATE TABLE document_pages(
            document_id TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            page_order INTEGER NOT NULL,
            PRIMARY KEY(document_id, page_order)
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_docpages_asset ON document_pages(asset_id)")

    conn.commit()

def rollback(conn): pass 