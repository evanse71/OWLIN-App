from fastapi import APIRouter, UploadFile, BackgroundTasks, HTTPException
from pathlib import Path
import uuid, shutil, sqlite3, datetime, os, logging

log = logging.getLogger("owlin.upload")

router = APIRouter()

DATA_DIR = Path("data")
UPLOAD_DIR = DATA_DIR / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "owlin.db"

def _db():
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    # pragmatic pragmas for fewer Windows locks
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    return con

def _ensure_schema():
    with _db() as con:
        cur = con.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS documents(
            id TEXT PRIMARY KEY, sha256 TEXT, type TEXT, path TEXT,
            ocr_confidence REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );""")
        cur.execute("""CREATE TABLE IF NOT EXISTS invoices(
            id TEXT PRIMARY KEY, document_id TEXT, supplier TEXT,
            invoice_date TEXT, total_value REAL, matched_delivery_note_id TEXT,
            status TEXT DEFAULT 'queued'
        );""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_doc ON invoices(document_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type)")
        con.commit()

def _save_upload(file: UploadFile) -> tuple[str, Path]:
    # Defensive filename handling
    original = file.filename or "upload.pdf"
    ext = Path(original).suffix.lower() or ".pdf"
    doc_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{doc_id}{ext}"
    # Ensure pointer at start then copy
    try:
        file.file.seek(0)
    except Exception:
        pass
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    # Ensure OS flush
    try:
        os.fsync(f.fileno())
    except Exception:
        pass
    return doc_id, dest

def process_document_sync(document_id: str, file_path: Path):
    """Placeholder OCR/parse — mark scanned so UI can reflect progress."""
    try:
        _ensure_schema()
        with _db() as con:
            cur = con.cursor()
            cur.execute("UPDATE invoices SET status=? WHERE document_id=?", ("scanned", document_id))
            con.commit()
        log.info("Document %s processed: %s", document_id, file_path.name)
    except Exception as e:
        log.exception("Background processing failed for %s: %s", document_id, e)

@router.post("/upload")
async def upload(file: UploadFile, background_tasks: BackgroundTasks):
    _ensure_schema()
    if not file or not file.filename:
        raise HTTPException(400, "No file provided")
    doc_id, dest = _save_upload(file)

    # create document + invoice stub
    today = datetime.date.today().isoformat()
    with _db() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO documents(id, sha256, type, path, ocr_confidence) VALUES(?,?,?,?,?)",
            (doc_id, None, "invoice", str(dest), None)
        )
        inv_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO invoices(id, document_id, supplier, invoice_date, total_value, status) VALUES(?,?,?,?,?,?)",
            (inv_id, doc_id, "Unknown", today, None, "queued")
        )
        con.commit()

    # Close the UploadFile handle early (Windows file locks)
    try:
        await file.close()
    except Exception:
        pass

    # Background task (pure sync)
    background_tasks.add_task(process_document_sync, doc_id, dest)
    return {"document_id": doc_id, "invoice_id": inv_id, "status": "queued"}