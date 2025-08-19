from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from uuid import UUID
from typing import Optional, List

from ..contracts import Escalation, CreateEscalationRequest, UpdateEscalationRequest
from ..services.permissions import require_permission
from ..services.auth import get_current_user
from ..services.suppliers.escalation_service import create_escalation, update_escalation, get_escalation, list_escalations

router = APIRouter(prefix="/api/escalations", tags=["escalations"])


@router.post("", response_model=Escalation)
async def create_escalation_endpoint(
	payload: CreateEscalationRequest,
	request: Request
):
	"""Create a new escalation (Finance/GM only)."""
	# Check permissions
	_ = require_permission("flagged_issues.escalate")(request)
	
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Create escalation
	escalation_data = create_escalation(
		supplier_id=str(payload.supplier_id),
		venue_id=str(payload.venue_id),
		opened_by=str(user["id"]),
		title=payload.title,
		description=payload.description,
		level=payload.level,
		assigned_to=str(payload.assigned_to) if payload.assigned_to else None
	)
	
	# Convert to contract format
	from ..contracts import EscalationNote
	
	notes = []
	for note in escalation_data.get("notes", []):
		notes.append(EscalationNote(
			id=UUID(note["id"]),
			author_id=UUID(note["author_id"]),
			body=note["body"],
			created_at=note["created_at"]
		))
	
	return Escalation(
		id=UUID(escalation_data["id"]),
		supplier_id=UUID(escalation_data["supplier_id"]),
		venue_id=UUID(escalation_data["venue_id"]),
		level=escalation_data["level"],
		status=escalation_data["status"],
		title=escalation_data["title"],
		description=escalation_data["description"],
		due_at=escalation_data["due_at"],
		opened_by=UUID(escalation_data["opened_by"]),
		assigned_to=UUID(escalation_data["assigned_to"]) if escalation_data["assigned_to"] else None,
		created_at=escalation_data["created_at"],
		updated_at=escalation_data["updated_at"],
		notes=notes
	)


@router.patch("/{escalation_id}", response_model=Escalation)
async def update_escalation_endpoint(
	escalation_id: UUID,
	payload: UpdateEscalationRequest,
	request: Request
):
	"""Update an escalation (Finance/GM only)."""
	# Check permissions
	_ = require_permission("flagged_issues.escalate")(request)
	
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Update escalation
	escalation_data = update_escalation(
		escalation_id=str(escalation_id),
		status=payload.status,
		level=payload.level,
		assigned_to=str(payload.assigned_to) if payload.assigned_to else None,
		add_note=payload.add_note,
		author_id=str(user["id"]) if payload.add_note else None
	)
	
	# Get full escalation with notes
	full_escalation = get_escalation(str(escalation_id))
	
	# Convert to contract format
	from ..contracts import EscalationNote
	
	notes = []
	for note in full_escalation.get("notes", []):
		notes.append(EscalationNote(
			id=UUID(note["id"]),
			author_id=UUID(note["author_id"]),
			body=note["body"],
			created_at=note["created_at"]
		))
	
	return Escalation(
		id=UUID(full_escalation["id"]),
		supplier_id=UUID(full_escalation["supplier_id"]),
		venue_id=UUID(full_escalation["venue_id"]),
		level=full_escalation["level"],
		status=full_escalation["status"],
		title=full_escalation["title"],
		description=full_escalation["description"],
		due_at=full_escalation["due_at"],
		opened_by=UUID(full_escalation["opened_by"]),
		assigned_to=UUID(full_escalation["assigned_to"]) if full_escalation["assigned_to"] else None,
		created_at=full_escalation["created_at"],
		updated_at=full_escalation["updated_at"],
		notes=notes
	)


@router.get("/{escalation_id}", response_model=Escalation)
async def get_escalation_endpoint(
	escalation_id: UUID,
	request: Request
):
	"""Get escalation details."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	escalation_data = get_escalation(str(escalation_id))
	if not escalation_data:
		raise HTTPException(404, "Escalation not found")
	
	# Convert to contract format
	from ..contracts import EscalationNote
	
	notes = []
	for note in escalation_data.get("notes", []):
		notes.append(EscalationNote(
			id=UUID(note["id"]),
			author_id=UUID(note["author_id"]),
			body=note["body"],
			created_at=note["created_at"]
		))
	
	return Escalation(
		id=UUID(escalation_data["id"]),
		supplier_id=UUID(escalation_data["supplier_id"]),
		venue_id=UUID(escalation_data["venue_id"]),
		level=escalation_data["level"],
		status=escalation_data["status"],
		title=escalation_data["title"],
		description=escalation_data["description"],
		due_at=escalation_data["due_at"],
		opened_by=UUID(escalation_data["opened_by"]),
		assigned_to=UUID(escalation_data["assigned_to"]) if escalation_data["assigned_to"] else None,
		created_at=escalation_data["created_at"],
		updated_at=escalation_data["updated_at"],
		notes=notes
	)


@router.get("", response_model=List[Escalation])
async def list_escalations_endpoint(
	request: Request,
	supplier_id: Optional[UUID] = Query(None, description="Filter by supplier"),
	venue_id: Optional[UUID] = Query(None, description="Filter by venue"),
	status: Optional[str] = Query(None, description="Filter by status")
):
	"""List escalations with optional filtering."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	escalations_data = list_escalations(
		supplier_id=str(supplier_id) if supplier_id else None,
		venue_id=str(venue_id) if venue_id else None,
		status=status
	)
	
	# Convert to contract format
	escalations = []
	for escalation_data in escalations_data:
		escalations.append(Escalation(
			id=UUID(escalation_data["id"]),
			supplier_id=UUID(escalation_data["supplier_id"]),
			venue_id=UUID(escalation_data["venue_id"]),
			level=escalation_data["level"],
			status=escalation_data["status"],
			title=escalation_data["title"],
			description=escalation_data["description"],
			due_at=escalation_data["due_at"],
			opened_by=UUID(escalation_data["opened_by"]),
			assigned_to=UUID(escalation_data["assigned_to"]) if escalation_data["assigned_to"] else None,
			created_at=escalation_data["created_at"],
			updated_at=escalation_data["updated_at"],
			notes=[]  # Notes not included in list view for performance
		))
	
	return escalations 