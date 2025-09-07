from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..session import get_session
from ..services.issues import create_flagged_issue, update_flagged_issue_status, group_issues, escalate_issue, list_issues
from ..contracts import FlaggedIssue as IssueModel
from pydantic import BaseModel
from uuid import UUID
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api")


class CreateIssueRequest(BaseModel):
	invoice_id: UUID
	supplier_id: Optional[UUID] = None
	type: str
	description: str
	severity: str
	user_id: Optional[str] = None


class UpdateIssueRequest(BaseModel):
	status: Optional[str] = None
	description: Optional[str] = None
	role: str = "ShiftLead"
	user_id: Optional[str] = None


class GroupIssuesRequest(BaseModel):
	issue_ids: List[UUID]
	group_name: str
	user_id: Optional[str] = None


class EscalateIssueRequest(BaseModel):
	to_role: str
	note: Optional[str] = None
	role: str = "GM"
	user_id: Optional[str] = None


@router.get("/flagged-issues")
async def get_flagged_issues(
	status: Optional[str] = Query(None),
	supplier: Optional[str] = Query(None),
	date_range: Optional[str] = Query(None),
	limit: int = Query(100, ge=1, le=500),
	offset: int = Query(0, ge=0),
	session: Session = Depends(get_session),
):
	items = list_issues(session, status=status, supplier=supplier, date_range=date_range, limit=limit, offset=offset)
	resp = JSONResponse(content={"items": items})
	resp.headers["Cache-Control"] = "public, max-age=60"
	return resp


@router.post("/flagged-issues")
async def post_flagged_issue(req: CreateIssueRequest, session: Session = Depends(get_session)):
	res = create_flagged_issue(
		session,
		invoice_id=str(req.invoice_id),
		supplier_id=str(req.supplier_id) if req.supplier_id else None,
		issue_type=req.type,
		description=req.description,
		severity=req.severity,
		user_id=req.user_id,
	)
	return res


@router.patch("/flagged-issues/{issue_id}")
async def patch_flagged_issue(issue_id: UUID, req: UpdateIssueRequest, session: Session = Depends(get_session)):
	try:
		if req.status:
			update_flagged_issue_status(session, issue_id=str(issue_id), status=req.status, description=req.description, role=req.role, user_id=req.user_id)
		else:
			update_flagged_issue_status(session, issue_id=str(issue_id), status="open", description=req.description, role=req.role, user_id=req.user_id)
	except PermissionError:
		raise HTTPException(status_code=403, detail="Forbidden")
	return {"ok": True}


@router.post("/flagged-issues/group")
async def post_group_issues(req: GroupIssuesRequest, session: Session = Depends(get_session)):
	gid = group_issues(session, issue_ids=[str(x) for x in req.issue_ids], group_name=req.group_name, user_id=req.user_id)
	return {"group_id": gid}


@router.post("/flagged-issues/{issue_id}/escalate")
async def post_escalate_issue(issue_id: UUID, req: EscalateIssueRequest, session: Session = Depends(get_session)):
	try:
		eid = escalate_issue(session, issue_id=str(issue_id), to_role=req.to_role, note=req.note, role=req.role, user_id=req.user_id)
	except PermissionError:
		raise HTTPException(status_code=403, detail="Forbidden")
	return {"escalation_id": eid} 