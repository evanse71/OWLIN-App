# backend/db.py
import sqlite3, os, pathlib, contextlib, logging

# Use single environment variable for database path
DB_PATH = os.environ.get("OWLIN_DB", "owlin.db")
DB_PATH = pathlib.Path(DB_PATH).resolve()

log = logging.getLogger("db")

def get_conn():
    # Log the resolved database path on first connection
    if not hasattr(get_conn, '_logged_path'):
        log.info(f"Database path: {DB_PATH}")
        get_conn._logged_path = True
    
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    # Hardening pragmas
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=8000;")
    return conn

def init():
    with get_conn() as c:
        # core tables (create if not exists)
        c.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
          id TEXT PRIMARY KEY,
          status TEXT,
          confidence INTEGER,
          paired INTEGER DEFAULT 0,
          processing_progress INTEGER DEFAULT 0,
          supplier_name TEXT,
          invoice_date TEXT,
          total_amount INTEGER,
          subtotal_p INTEGER,
          vat_total_p INTEGER,
          total_p INTEGER,
          filename TEXT,
          issues_count INTEGER DEFAULT 0,
          file_hash TEXT
        );""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          invoice_id TEXT,
          description TEXT,
          qty REAL,
          unit_price INTEGER,
          total INTEGER,
          vat_rate INTEGER,
          confidence INTEGER,
          FOREIGN KEY(invoice_id) REFERENCES invoices(id)
        );""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY,
          kind TEXT,
          status TEXT,
          progress INTEGER,
          meta_json TEXT,
          result_json TEXT,
          error TEXT,
          duration_ms INTEGER,
          created_at TEXT DEFAULT (datetime('now')),
          updated_at TEXT DEFAULT (datetime('now'))
        );""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS delivery_notes (
          id TEXT PRIMARY KEY,
          status TEXT,
          supplier_name TEXT,
          note_date TEXT
        );""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS dn_items (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          dn_id TEXT,
          description TEXT,
          qty REAL,
          unit_price INTEGER,
          vat_rate INTEGER
        );""")

def migrate():
    # Idempotent "add column" helpers
    def add_col(table, col, ddl):
        with get_conn() as c:
            cols = [r["name"] for r in c.execute(f"PRAGMA table_info({table});").fetchall()]
            if col not in cols:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
    add_col("invoices","subtotal_p","subtotal_p INTEGER")
    add_col("invoices","vat_total_p","vat_total_p INTEGER")
    add_col("invoices","total_p","total_p INTEGER")
    add_col("invoices","filename","filename TEXT")
    add_col("invoices","issues_count","issues_count INTEGER DEFAULT 0")
    add_col("invoices","file_hash","file_hash TEXT")
    add_col("invoices","parsed_at","parsed_at TEXT")
    add_col("invoices","matched_at","matched_at TEXT")
    add_col("jobs","error","error TEXT")
    add_col("jobs","duration_ms","duration_ms INTEGER")
    add_col("jobs","meta_json","meta_json TEXT")
    add_col("jobs","result_json","result_json TEXT")

def reset_for_tests():
    with contextlib.suppress(FileNotFoundError):
        os.remove(DB_PATH)
    init()
    migrate() 