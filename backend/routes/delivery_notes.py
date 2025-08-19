from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from ..session import get_session
from ..services.delivery_ingest import ingest_delivery_notes
from ..services.matching import suggest_matches, confirm_match, reject_match
from ..contracts import DeliveryNote as ApiDN
from pydantic import BaseModel
from ..services.permissions import require_permission

router = APIRouter(prefix="/api")


class UploadDNResponse(BaseModel):
	delivery_notes: list[ApiDN]


@router.post("/delivery-notes/upload", response_model=UploadDNResponse, dependencies=[Depends(require_permission("invoice.upload"))])
async def upload_delivery_notes(files: List[UploadFile] = File(...), session: Session = Depends(get_session)):
	return ingest_delivery_notes(session, files)


@router.get("/delivery-notes", response_model=list[ApiDN])
async def list_delivery_notes(
	status: Optional[str] = Query(None),
	q: Optional[str] = Query(None),
	limit: int = Query(50, ge=1, le=200),
	offset: int = Query(0, ge=0),
	session: Session = Depends(get_session)
):
	base = "SELECT id, supplier_name, note_number, date, status, ocr_confidence, matched_invoice_id FROM delivery_notes"
	conds = []
	params = {}
	if status:
		conds.append("status = :status")
		params["status"] = status
	if q:
		conds.append("(supplier_name LIKE :q OR note_number LIKE :q)")
		params["q"] = f"%{q}%"
	if conds:
		base += " WHERE " + " AND ".join(conds)
	base += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
	params["limit"] = limit
	params["offset"] = offset
	rows = session.execute(base, params).fetchall()
	# load items per DN
	out = []
	for r in rows:
		items = session.execute(
			"SELECT id, description, qty, unit_price_pennies, total_pennies, uom, sku FROM line_items WHERE parent_type='delivery_note' AND parent_id=:id",
			{"id": r[0]},
		).fetchall()
		out.append(
			ApiDN(
				id=r[0], supplier_name=r[1], note_number=r[2], date=r[3], status=r[4], ocr_confidence=int(r[5] or 0), matched_invoice_id=r[6],
				items=[
					{
						"id": i[0],
						"description": i[1],
						"qty": float(i[2] or 0),
						"unit_price_pennies": int(i[3] or 0),
						"total_pennies": int(i[4] or 0),
						"uom": i[5],
						"sku": i[6],
					}
					for i in items
				],
			)
		)
	return out


class MatchConfirmRequest(BaseModel):
	delivery_note_id: UUID
	invoice_id: UUID


class MatchRejectRequest(BaseModel):
	delivery_note_id: UUID


class OkResponse(BaseModel):
	ok: bool


@router.get("/match/suggestions")
async def get_suggestions(delivery_note_id: UUID, limit: int = 3, session: Session = Depends(get_session)):
	cands = suggest_matches(session, str(delivery_note_id), limit=limit)
	return {"delivery_note_id": delivery_note_id, "candidates": cands}


@router.post("/match/confirm", response_model=OkResponse, dependencies=[Depends(require_permission("match.confirm"))])
async def post_confirm(req: MatchConfirmRequest, session: Session = Depends(get_session)):
	try:
		confirm_match(session, str(req.delivery_note_id), str(req.invoice_id), "Finance")
	except PermissionError:
		raise HTTPException(status_code=403, detail="Forbidden")
	return {"ok": True}


@router.post("/match/reject", response_model=OkResponse, dependencies=[Depends(require_permission("match.reject"))])
async def post_reject(req: MatchRejectRequest, session: Session = Depends(get_session)):
	try:
		reject_match(session, str(req.delivery_note_id), "Finance")
	except PermissionError:
		raise HTTPException(status_code=403, detail="Forbidden")
	return {"ok": True} 