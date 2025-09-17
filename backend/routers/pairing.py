from __future__ import annotations
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

router = APIRouter(prefix="/api/pairing", tags=["pairing"])


class PairingSuggestionDTO(BaseModel):
    delivery_note_id: str
    invoice_id: Optional[str] = None
    score: float
    reason: Optional[str] = None


@router.get("/suggestions")
def suggestions(invoice_id: str = Query(...)) -> Dict[str, List[PairingSuggestionDTO]]:
    # Stub: return empty list; wire up real scoring later
    return {"suggestions": []}


# Delivery-notes side (if your UI calls /api/delivery-notes/pair etc.)
dn_router = APIRouter(prefix="/api/delivery-notes", tags=["delivery-notes-pairing"])


class PairBody(BaseModel):
    delivery_note_id: str
    invoice_id: str


@dn_router.post("/pair")
def pair_dn(body: PairBody = Body(...)) -> Dict[str, Any]:
    # TODO: write relationship into DB table delivery_notes.invoice_id = body.invoice_id
    return {"ok": True}


@dn_router.post("/unpair")
def unpair_dn(body: Dict[str, str] = Body(...)) -> Dict[str, Any]:
    # TODO: set delivery_notes.invoice_id = NULL where id=body["delivery_note_id"]
    return {"ok": True}


@dn_router.get("/suggestions")
def dn_suggestions(id: str = Query(...)) -> Dict[str, List[PairingSuggestionDTO]]:
    return {"suggestions": []}