from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from uuid import UUID
from typing import Optional
from datetime import datetime

from ..contracts import TimelineResponse
from ..services.permissions import require_permission
from ..services.auth import get_current_user
from ..services.suppliers.timeline_builder import build_summary, build_timeline

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("/{supplier_id}/timeline", response_model=TimelineResponse)
async def get_supplier_timeline(
	supplier_id: UUID,
	request: Request,
	venue_id: Optional[UUID] = Query(None, description="Filter by venue"),
	start: datetime = Query(..., description="Start date"),
	end: datetime = Query(..., description="End date")
):
	"""Get supplier timeline with summary and events."""
	# Get current user
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check if user has access to this supplier/venue
	# For now, allow access (in production, check user permissions)
	
	# Build summary and timeline
	summary = build_summary(str(supplier_id), str(venue_id) if venue_id else None)
	events = build_timeline(str(supplier_id), str(venue_id) if venue_id else None, start, end)
	
	return TimelineResponse(
		summary=summary,
		events=events
	)


@router.get("/{supplier_id}/summary")
async def get_supplier_summary(
	supplier_id: UUID,
	request: Request,
	venue_id: Optional[UUID] = Query(None, description="Filter by venue")
):
	"""Get supplier summary only."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	summary = build_summary(str(supplier_id), str(venue_id) if venue_id else None)
	return summary 