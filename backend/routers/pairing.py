from fastapi import APIRouter, HTTPException
try:
    from ..db import fetch_one, fetch_all
except ImportError:
    try:
        from backend.db import fetch_one, fetch_all
    except ImportError:
        from db import fetch_one, fetch_all

router = APIRouter(prefix="/api/pairing", tags=["pairing"])

@router.get("/suggestions")
def suggest(invoice_id: str):
    inv = fetch_one("SELECT supplier, invoice_date, total_value FROM invoices WHERE id=?", (invoice_id,))
    if not inv: raise HTTPException(404, "invoice not found")
    cands = fetch_all("SELECT id, supplier, note_date, total_amount FROM delivery_notes ORDER BY note_date DESC LIMIT 50")
    out = []
    for c in cands:
        score = 0
        if inv["supplier"] and c["supplier"] and inv["supplier"].lower()==c["supplier"].lower():
            score += 50
        if inv["invoice_date"] and c["note_date"] and inv["invoice_date"]==c["note_date"]:
            score += 30
        if inv["total_value"] and c["total_amount"] and abs(inv["total_value"]-c["total_amount"])<=2.0:
            score += 20
        if score>0:
            out.append({"delivery_note_id": c["id"], "score": score, "reason":"heuristics"})
    out.sort(key=lambda x: x["score"], reverse=True)
    return {"suggestions": out, "total_candidates": len(cands)}