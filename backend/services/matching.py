from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from rapidfuzz import fuzz
from ..services.audit import log_event

W_SUPPLIER, W_DATE, W_AMOUNT, W_LINES = 0.40, 0.20, 0.20, 0.20


def _supplier_sim(a: str | None, b: str | None) -> float:
	if not a or not b:
		return 0.0
	return fuzz.token_set_ratio(a, b) / 100.0


def _date_score(d1: date | None, d2: date | None) -> float:
	if not d1 or not d2:
		return 0.0
	diff = abs((d1 - d2).days)
	return 1.0 if diff == 0 else (0.0 if diff >= 3 else max(0.0, 1.0 - diff / 3.0))


def _amount_score(a: int, b: int) -> float:
	if a <= 0 or b <= 0:
		return 0.0
	ratio = min(a, b) / max(a, b)
	return 1.0 if ratio >= 0.98 else ratio


def _norm(s: str) -> str:
	return " ".join(s.lower().split())


def _lines_score(session: Session, dn_id, inv_id) -> float:
	dn_items = session.execute(
		"SELECT description, qty FROM line_items WHERE parent_type='delivery_note' AND parent_id=:id",
		{"id": dn_id},
	).fetchall()
	inv_items = session.execute(
		"SELECT description, qty FROM line_items WHERE parent_type='invoice' AND parent_id=:id",
		{"id": inv_id},
	).fetchall()
	if not dn_items or not inv_items:
		return 0.0
	A = [(_norm(x[0] or ""), max(0.0, float(x[1] or 0))) for x in dn_items]
	B = [(_norm(x[0] or ""), max(0.0, float(x[1] or 0))) for x in inv_items]
	used = set()
	matches = 0
	for desc_a, qty_a in A:
		best, jbest = 0.0, None
		for j, (desc_b, qty_b) in enumerate(B):
			if j in used:
				continue
			sim = fuzz.token_set_ratio(desc_a, desc_b) / 100.0
			if sim >= 0.85 and abs(qty_a - qty_b) <= max(0.05 * max(qty_a, 1.0), 0.1):
				if sim > best:
					best, jbest = sim, j
		if jbest is not None:
			used.add(jbest)
			matches += 1
	return (2.0 * matches) / (len(A) + len(B))


def calc_score(session: Session, dn_row, inv_row) -> tuple[float, dict]:
	dn_id, dn_supplier, dn_date = dn_row[0], dn_row[1], dn_row[2]
	inv_id, inv_supplier, inv_date, inv_total, inv_vat, inv_status, inv_conf = (
		inv_row[0],
		inv_row[1],
		inv_row[2],
		int(inv_row[3] or 0),
		int(inv_row[4] or 0),
		inv_row[5],
		int(inv_row[6] or 0),
	)
	dn_total = int(
		sum(x[0] or 0 for x in session.execute(
			"SELECT total_pennies FROM line_items WHERE parent_type='delivery_note' AND parent_id=:id",
			{"id": dn_id},
		).fetchall())
	)
	amount = _amount_score(dn_total, inv_total)
	supplier = _supplier_sim(dn_supplier, inv_supplier)
	date_s = _date_score(dn_date, inv_date)
	lines = _lines_score(session, dn_id, inv_id)
	score = 100.0 * (W_SUPPLIER * supplier + W_DATE * date_s + W_AMOUNT * amount + W_LINES * lines)
	return round(score, 1), {
		"supplier": round(100 * supplier, 1),
		"date": round(100 * date_s, 1),
		"amount": round(100 * amount, 1),
		"lines": round(100 * lines, 1),
	}


def suggest_matches(session: Session, delivery_note_id: str, limit: int = 3):
	dn_row = session.execute(
		"SELECT id, supplier_name, date FROM delivery_notes WHERE id=:id",
		{"id": delivery_note_id},
	).fetchone()
	assert dn_row, "delivery note not found"
	q = "SELECT id, supplier_name, invoice_date, total_amount_pennies, vat_amount_pennies, status, confidence FROM invoices WHERE status IN ('scanned','matched')"
	params = {}
	if dn_row[2]:
		q += " AND invoice_date >= :start AND invoice_date <= :end"
		params["start"] = (dn_row[2] - timedelta(days=7)).isoformat()
		params["end"] = (dn_row[2] + timedelta(days=7)).isoformat()
	inv_rows = session.execute(q, params).fetchall()
	cands = []
	for inv in inv_rows:
		s, breakdown = calc_score(session, dn_row, inv)
		cands.append((s, breakdown, inv))
	cands.sort(key=lambda x: x[0], reverse=True)
	out = []
	for s, breakdown, inv in cands[:limit]:
		out.append(
			{
				"invoice": {
					"id": inv[0],
					"supplier_name": inv[1],
					"invoice_number": "",  # not in select, keep minimal summary
					"invoice_date": inv[2],
					"total_amount_pennies": int(inv[3] or 0),
					"vat_amount_pennies": int(inv[4] or 0),
					"currency": "GBP",
					"status": inv[5],
					"confidence": int(inv[6] or 0),
				},
				"score": s,
				"breakdown": breakdown,
			}
		)
	return out


def confirm_match(session: Session, delivery_note_id: str, invoice_id: str, actor_role: str) -> None:
	if actor_role not in ("GM", "Finance"):
		raise PermissionError("Forbidden")
	row = session.execute("SELECT id, matched_invoice_id, status FROM delivery_notes WHERE id=:id", {"id": delivery_note_id}).fetchone()
	assert row, "not found"
	if row[1] == invoice_id and row[2] == "matched":
		return
	session.execute(
		"UPDATE delivery_notes SET matched_invoice_id=:inv, status='matched', updated_at=:ts WHERE id=:id",
		{"inv": invoice_id, "ts": datetime.utcnow().isoformat(), "id": delivery_note_id},
	)
	session.commit()
	log_event(session, "dn_match_confirmed", "delivery_note", str(delivery_note_id), f"invoice_id={invoice_id}, role={actor_role}")


def reject_match(session: Session, delivery_note_id: str, actor_role: str) -> None:
	if actor_role not in ("GM", "Finance"):
		raise PermissionError("Forbidden")
	row = session.execute("SELECT id, status FROM delivery_notes WHERE id=:id", {"id": delivery_note_id}).fetchone()
	assert row, "not found"
	if row[1] == "rejected":
		return
	session.execute(
		"UPDATE delivery_notes SET matched_invoice_id=NULL, status='rejected', updated_at=:ts WHERE id=:id",
		{"ts": datetime.utcnow().isoformat(), "id": delivery_note_id},
	)
	session.commit()
	log_event(session, "dn_match_rejected", "delivery_note", str(delivery_note_id), f"role={actor_role}") 