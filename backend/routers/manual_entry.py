from fastapi import APIRouter, HTTPException, Depends
from typing import Any, Dict, Union, Optional
import sqlite3
import json
from decimal import Decimal
from pydantic import BaseModel, Field, condecimal, constr
from backend.services.pack_math import calc_line_totals
from backend.services.audit import audit_log
from backend.services import permissions as perm

DB_PATH = "data/owlin.db"
router = APIRouter(prefix="/manual", tags=["manual"])

# ---- SIMPLE ACTOR STUB (replace later with real auth/session) ----
def get_actor() -> Dict[str, str]:
    # TODO: wire to real user/role
    return {"user": "local_user", "role": "Finance"}

# Schema will be ensured on first use via schema_guard

# ---- Pydantic schemas ----
Currency = constr(min_length=3, max_length=3)

class LineItemIn(BaseModel):
    description: constr(min_length=1)
    outer_qty: condecimal(ge=0)
    items_per_outer: Optional[condecimal(gt=0)] = None
    unit_size: Optional[condecimal(gt=0)] = None  # ml/grams (info)
    unit_price: condecimal(ge=0)               # per-unit (NOT per crate)
    vat_rate_percent: condecimal(ge=0) = Decimal("20")

class InvoiceIn(BaseModel):
    supplier_id: constr(min_length=1)
    supplier_name: constr(min_length=1)
    invoice_date: constr(min_length=10, max_length=10)  # YYYY-MM-DD
    invoice_ref: constr(min_length=1)
    currency: Currency = "GBP"
    notes: Optional[str] = None
    lines: list[LineItemIn] = Field(min_items=1)

class DeliveryNoteIn(BaseModel):
    supplier_id: constr(min_length=1)
    supplier_name: constr(min_length=1)
    delivery_date: constr(min_length=10, max_length=10)  # YYYY-MM-DD
    delivery_ref: constr(min_length=1)
    currency: Currency = "GBP"
    notes: Optional[str] = None
    lines: list[LineItemIn] = Field(min_items=1)

class PairRequest(BaseModel):
    invoice_id: constr(min_length=1)
    delivery_note_id: constr(min_length=1)

# ---- Helpers ----
def _conn(): 
    from backend.services.schema_guard import ensure_schema_once
    ensure_schema_once()  # Ensure schema before connecting
    return sqlite3.connect(DB_PATH)
def _dec(x) -> Decimal: return Decimal(str(x))

# ---- Routes ----
@router.post("/invoices")
def create_invoice(payload: InvoiceIn, actor: Dict[str, str] = Depends(get_actor)) -> dict[str, Any]:
    if not perm.can_create_invoice(actor["role"]): raise HTTPException(403, "Forbidden")
    total_net = Decimal("0"); total_vat = Decimal("0"); total_gross = Decimal("0"); computed=[]
    for li in payload.lines:
        res = calc_line_totals(li.outer_qty, li.items_per_outer, li.unit_price, li.vat_rate_percent)
        total_net += res["net"]; total_vat += res["vat"]; total_gross += res["gross"]
        computed.append(li.dict() | {
            "base_units": str(res["base_units"]),
            "net": str(res["net"]), "vat": str(res["vat"]), "gross": str(res["gross"])
        })

    with _conn() as conn:
        cur = conn.cursor()
        inv_id = payload.invoice_ref  # deterministic for now
        
        # prevent duplicate primary key (using human ref as id)
        cur.execute("SELECT 1 FROM invoices WHERE id=?", (inv_id,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Invoice reference already exists. Use a unique Invoice Ref.")
        
        cur.execute("""
            INSERT INTO invoices (
              id, supplier_id, supplier_name, invoice_date, invoice_ref, currency,
              status, entry_mode, total_net, total_vat, total_gross, notes, meta_json
            ) VALUES (?,?,?,?,?,?,'manual_entered','manual',?,?,?,?,?)
        """, (
            inv_id, payload.supplier_id, payload.supplier_name, payload.invoice_date, payload.invoice_ref, payload.currency,
            str(total_net), str(total_vat), str(total_gross), payload.notes or "", json.dumps({"lines": computed}, ensure_ascii=False)
        ))
        conn.commit()
    audit_log(actor["user"], "create", "invoice", inv_id, {"source":"manual","totals":{"net":str(total_net),"vat":str(total_vat),"gross":str(total_gross)}})
    return {"id": inv_id, "status": "manual_entered", "totals":{"net":str(total_net),"vat":str(total_vat),"gross":str(total_gross)}}

@router.patch("/invoices/{invoice_id}")
def edit_invoice(invoice_id: str, payload: InvoiceIn, actor: Dict[str, str] = Depends(get_actor)) -> dict[str, Any]:
    if not perm.can_edit_invoice(actor["role"]): raise HTTPException(403, "Forbidden")
    total_net = Decimal("0"); total_vat = Decimal("0"); total_gross = Decimal("0"); computed=[]
    for li in payload.lines:
        res = calc_line_totals(li.outer_qty, li.items_per_outer, li.unit_price, li.vat_rate_percent)
        total_net += res["net"]; total_vat += res["vat"]; total_gross += res["gross"]
        computed.append(li.dict() | {
            "base_units": str(res["base_units"]),
            "net": str(res["net"]), "vat": str(res["vat"]), "gross": str(res["gross"])
        })
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE invoices SET
              supplier_id=?, supplier_name=?, invoice_date=?, invoice_ref=?, currency=?,
              status='manual_entered', entry_mode='manual',
              total_net=?, total_vat=?, total_gross=?, notes=?, meta_json=?
            WHERE id=?
        """, (
            payload.supplier_id, payload.supplier_name, payload.invoice_date, payload.invoice_ref, payload.currency,
            str(total_net), str(total_vat), str(total_gross), payload.notes or "", json.dumps({"lines": computed}, ensure_ascii=False),
            invoice_id
        ))
        if cur.rowcount == 0: raise HTTPException(404, "Invoice not found")
        conn.commit()
    audit_log(actor["user"], "edit", "invoice", invoice_id, {"totals":{"net":str(total_net)}})
    return {"id": invoice_id, "status": "manual_entered"}

@router.post("/delivery-notes")
def create_dn(payload: DeliveryNoteIn, actor: Dict[str, str] = Depends(get_actor)) -> dict[str, Any]:
    if not perm.can_create_dn(actor["role"]): raise HTTPException(403, "Forbidden")
    from decimal import Decimal
    total_units = Decimal("0"); computed=[]
    for li in payload.lines:
        res = calc_line_totals(li.outer_qty, li.items_per_outer, li.unit_price, li.vat_rate_percent)
        total_units += res["base_units"]
        computed.append(li.dict() | {
            "base_units": str(res["base_units"]),
            "net": str(res["net"]), "vat": str(res["vat"]), "gross": str(res["gross"])
        })
    with _conn() as conn:
        cur = conn.cursor()
        dn_id = payload.delivery_ref
        
        # prevent duplicate primary key (using human ref as id)
        cur.execute("SELECT 1 FROM delivery_notes WHERE id=?", (dn_id,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Delivery Note reference already exists. Use a unique DN Ref.")
        
        cur.execute("""
            INSERT INTO delivery_notes (
              id, supplier_id, supplier_name, delivery_date, delivery_ref, currency,
              status, entry_mode, notes, meta_json
            ) VALUES (?,?,?,?,?,?,'manual_entered','manual',?,?)
        """, (dn_id, payload.supplier_id, payload.supplier_name, payload.delivery_date, payload.delivery_ref, payload.currency,
              payload.notes or "", json.dumps({"lines": computed, "total_units": str(total_units)}, ensure_ascii=False)))
        conn.commit()
    audit_log(actor["user"], "create", "delivery_note", dn_id, {"source":"manual"})
    return {"id": dn_id, "status": "manual_entered"}

@router.patch("/delivery-notes/{dn_id}")
def edit_dn(dn_id: str, payload: DeliveryNoteIn, actor: Dict[str, str] = Depends(get_actor)) -> dict[str, Any]:
    notes_only = perm.can_edit_dn_notes_only(actor["role"]) and not perm.can_edit_dn_full(actor["role"])
    with _conn() as conn:
        cur = conn.cursor()
        if notes_only:
            cur.execute("UPDATE delivery_notes SET notes=? WHERE id=?", (payload.notes or "", dn_id))
        else:
            total_units = Decimal("0"); computed=[]
            for li in payload.lines:
                res = calc_line_totals(li.outer_qty, li.items_per_outer, li.unit_price, li.vat_rate_percent)
                total_units += res["base_units"]
                computed.append(li.dict() | {
                    "base_units": str(res["base_units"]),
                    "net": str(res["net"]), "vat": str(res["vat"]), "gross": str(res["gross"])
                })
            cur.execute("""
                UPDATE delivery_notes SET
                  supplier_id=?, supplier_name=?, delivery_date=?, delivery_ref=?, currency=?,
                  status='manual_entered', entry_mode='manual', notes=?, meta_json=?
                WHERE id=?
            """, (payload.supplier_id, payload.supplier_name, payload.delivery_date, payload.delivery_ref, payload.currency,
                  payload.notes or "", json.dumps({"lines": computed, "total_units": str(total_units)}, ensure_ascii=False), dn_id))
        if cur.rowcount == 0: raise HTTPException(404, "Delivery note not found")
        conn.commit()
    audit_log(actor["user"], "edit", "delivery_note", dn_id, {"notes_only": notes_only})
    return {"id": dn_id, "status": "manual_entered"}

@router.get("/unpaired")
def list_unpaired(actor: Dict[str, str] = Depends(get_actor)) -> dict[str, Any]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, supplier_name, invoice_date, total_net, total_gross FROM invoices
            WHERE status IN ('manual_entered','scanned')
            ORDER BY invoice_date DESC, id DESC
        """)
        invoices = [{"id": r[0], "supplier_name": r[1], "date": r[2], "net": r[3], "gross": r[4]} for r in cur.fetchall()]
        cur.execute("""
            SELECT id, supplier_name, delivery_date FROM delivery_notes
            WHERE status IN ('manual_entered','scanned')
            ORDER BY delivery_date DESC, id DESC
        """)
        dns = [{"id": r[0], "supplier_name": r[1], "date": r[2]} for r in cur.fetchall()]
    return {"invoices": invoices, "delivery_notes": dns}

@router.post("/pair")
def pair_invoice_dn(payload: PairRequest, actor: Dict[str, str] = Depends(get_actor)) -> dict[str, Any]:
    if not perm.can_pair(actor["role"]): raise HTTPException(403, "Forbidden")
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM invoices WHERE id=?", (payload.invoice_id,))
        if not cur.fetchone(): raise HTTPException(404, "Invoice not found")
        cur.execute("SELECT id FROM delivery_notes WHERE id=?", (payload.delivery_note_id,))
        if not cur.fetchone(): raise HTTPException(404, "Delivery note not found")
        cur.execute("SELECT 1 FROM invoice_delivery_links WHERE invoice_id=? OR delivery_note_id=?",
                    (payload.invoice_id, payload.delivery_note_id))
        if cur.fetchone(): raise HTTPException(409, "Already paired")
        cur.execute("INSERT INTO invoice_delivery_links (invoice_id, delivery_note_id, linked_by) VALUES (?,?,?)",
                    (payload.invoice_id, payload.delivery_note_id, actor["user"]))
        cur.execute("UPDATE invoices SET status='paired' WHERE id=?", (payload.invoice_id,))
        cur.execute("UPDATE delivery_notes SET status='paired' WHERE id=?", (payload.delivery_note_id,))
        conn.commit()
    audit_log(actor["user"], "pair", "invoice_delivery", payload.invoice_id, {"delivery_note_id": payload.delivery_note_id})
    return {"ok": True, "invoice_id": payload.invoice_id, "delivery_note_id": payload.delivery_note_id}
