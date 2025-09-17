from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
try:
    from ..db import execute, fetch_one, fetch_all, uuid_str
except ImportError:
    try:
        from backend.db import execute, fetch_one, fetch_all, uuid_str
    except ImportError:
        from db import execute, fetch_one, fetch_all, uuid_str
import os, json, zipfile, time, uuid

router = APIRouter(prefix="/api/exports", tags=["exports"])

BACKUPS_DIR = os.path.join("backups")
os.makedirs(BACKUPS_DIR, exist_ok=True)

@router.post("/invoices")
def export_invoices(body: Dict[str,Any]):
    ids: List[str] = body.get("invoice_ids") or []
    if not ids: raise HTTPException(400, "no invoice ids")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    zpath = os.path.join(BACKUPS_DIR, f"owlin-invoices-{stamp}.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for iid in ids:
            inv = fetch_one("SELECT * FROM invoices WHERE id=?", (iid,))
            if not inv: continue
            items = fetch_all("SELECT * FROM invoice_line_items WHERE invoice_id=?", (iid,))
            pages = fetch_all("SELECT * FROM invoice_pages WHERE invoice_id=?", (iid,))
            z.writestr(f"{iid}/invoice.json", json.dumps(dict(inv), default=str, indent=2))
            z.writestr(f"{iid}/line_items.json", json.dumps([dict(i) for i in items], default=str, indent=2))
            z.writestr(f"{iid}/pages.json", json.dumps([dict(p) for p in pages], default=str, indent=2))
    return {"ok": True, "zip_path": zpath}
