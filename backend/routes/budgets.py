from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from datetime import date
from typing import Optional
from ..contracts import BudgetGuardrail, BudgetViolationsResponse
from ..services.forecasting import create_guardrail, list_guardrails, evaluate_guardrails

router = APIRouter(prefix="/api/budgets", tags=["budgets"]) 


@router.get("/guardrails", response_model=list[BudgetGuardrail])
async def get_guardrails(scope_type: Optional[str] = None, scope_id: Optional[UUID] = None):
	return list_guardrails(scope_type, str(scope_id) if scope_id else None)


@router.post("/guardrails", response_model=BudgetGuardrail)
async def post_guardrail(scope_type: str, scope_id: UUID, period_start: date, period_end: date, amount_pennies: int, hard_limit: bool = False, created_by: Optional[UUID] = None):
	try:
		creator = str(created_by) if created_by else "00000000-0000-0000-0000-000000000000"
		return create_guardrail(scope_type, str(scope_id), period_start, period_end, int(amount_pennies), bool(hard_limit), creator)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/violations", response_model=BudgetViolationsResponse)
async def get_violations():
	violations = evaluate_guardrails()
	return {"violations": violations} 