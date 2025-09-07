from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID

from ..contracts import RecoveryStatus, ActivateRecoveryRequest
from ..services.permissions import require_permission
from ..services.auth import get_current_user
from ..services.recovery_mode import (
	activate_recovery_mode, deactivate_recovery_mode, get_recovery_status,
	create_snapshot, rollback_to_snapshot, list_snapshots, should_activate_recovery_mode
)

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


@router.get("/status", response_model=RecoveryStatus)
async def get_recovery_status_endpoint(request: Request):
	"""Get current recovery mode status."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	status = get_recovery_status()
	
	return RecoveryStatus(
		active=status["active"],
		reason=status["reason"],
		activated_at=status["activated_at"],
		activated_by=UUID(status["activated_by"]) if status["activated_by"] else None
	)


@router.post("/activate")
async def activate_recovery_endpoint(
	payload: ActivateRecoveryRequest,
	request: Request
):
	"""Activate recovery mode (Admin only)."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check permissions - Admin role required
	_ = require_permission("settings.manage_roles")(request)
	
	result = activate_recovery_mode(
		reason=payload.reason,
		activated_by=str(user["id"])
	)
	
	if not result["success"]:
		raise HTTPException(400, result["message"])
	
	return result


@router.post("/deactivate")
async def deactivate_recovery_endpoint(request: Request):
	"""Deactivate recovery mode (Admin only)."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check permissions - Admin role required
	_ = require_permission("settings.manage_roles")(request)
	
	result = deactivate_recovery_mode(deactivated_by=str(user["id"]))
	
	if not result["success"]:
		raise HTTPException(400, result["message"])
	
	return result


@router.post("/snapshot")
async def create_snapshot_endpoint(
	request: Request,
	reason: str = None
):
	"""Create a database snapshot (Admin only)."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check permissions - Admin role required
	_ = require_permission("settings.manage_roles")(request)
	
	result = create_snapshot(
		created_by=str(user["id"]),
		reason=reason
	)
	
	if not result["success"]:
		raise HTTPException(400, result["message"])
	
	return result


@router.post("/rollback/{snapshot_id}")
async def rollback_snapshot_endpoint(
	snapshot_id: str,
	request: Request
):
	"""Rollback to a specific snapshot (Admin only)."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check permissions - Admin role required
	_ = require_permission("settings.manage_roles")(request)
	
	result = rollback_to_snapshot(
		snapshot_id=snapshot_id,
		rolled_back_by=str(user["id"])
	)
	
	if not result["success"]:
		raise HTTPException(400, result["message"])
	
	return result


@router.get("/snapshots")
async def list_snapshots_endpoint(request: Request):
	"""List all available snapshots."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check permissions - Admin role required
	_ = require_permission("settings.manage_roles")(request)
	
	snapshots = list_snapshots()
	
	return {
		"snapshots": snapshots,
		"count": len(snapshots)
	}


@router.get("/health-check")
async def health_check_endpoint(request: Request):
	"""Check system health and determine if recovery mode should be activated."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check permissions - Admin role required
	_ = require_permission("settings.manage_roles")(request)
	
	health_check = should_activate_recovery_mode()
	
	return health_check 