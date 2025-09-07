from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID
from typing import List

from contracts import UpdateBundle, ChangelogEntry, UpdateValidateResult, UpdateDependencies, UpdateProgressTick
from services.permissions import require_permission
from services import update_manager as svc

router = APIRouter(prefix="/api/updates", tags=["updates"])


@router.get("/available", response_model=List[UpdateBundle])
async def available_updates(request: Request):
	"""List available update bundles."""
	updates = svc.list_available_updates()
	
	# Convert to contract format
	result = []
	for update in updates:
		result.append(UpdateBundle(
			id=UUID(update["id"]),
			filename=update["filename"],
			version=update["version"],
			build=update["build"],
			created_at=update["created_at"],
			description=update["description"],
			verified=update["verified"],
			reason=update["reason"]
		))
	
	return result


@router.post("/verify/{bundle_id}", response_model=UpdateBundle)
async def verify_bundle(bundle_id: UUID, request: Request):
	"""Verify a specific bundle (GM only)."""
	_ = require_permission("settings.manage_roles")(request)  # GM permission
	
	result = svc.verify_bundle(str(bundle_id))
	
	if not result["ok"]:
		raise HTTPException(400, result["reason"])
	
	# Get updated bundle info
	updates = svc.list_available_updates()
	bundle = next((u for u in updates if u["id"] == str(bundle_id)), None)
	
	if not bundle:
		raise HTTPException(404, "Bundle not found")
	
	return UpdateBundle(
		id=UUID(bundle["id"]),
		filename=bundle["filename"],
		version=bundle["version"],
		build=bundle["build"],
		created_at=bundle["created_at"],
		description=bundle["description"],
		verified=bundle["verified"],
		reason=bundle["reason"]
	)


@router.post("/apply/{bundle_id}")
async def apply_update(bundle_id: UUID, request: Request):
	"""Apply an update (GM only)."""
	_ = require_permission("recovery.restore")(request)  # GM permission
	
	# Get bundle filename
	updates = svc.list_available_updates()
	bundle = next((u for u in updates if u["id"] == str(bundle_id)), None)
	
	if not bundle:
		raise HTTPException(404, "Bundle not found")
	
	if bundle["verified"] != "ok":
		raise HTTPException(400, "Bundle not verified")
	
	# Apply update
	from pathlib import Path
	zip_path = Path("updates") / bundle["filename"]
	
	result = svc.apply_update(str(zip_path))
	
	if not result["ok"]:
		raise HTTPException(400, f"Update failed: {'; '.join(result['reasons'])}")
	
	return {
		"ok": True,
		"message": "Update applied successfully",
		"snapshot": result["snapshot"],
		"changelog_id": result["changelog_id"],
		"job_id": result["job_id"]
	}


@router.post("/rollback/{changelog_id}")
async def rollback_update(changelog_id: UUID, request: Request):
	"""Rollback to a previous version (GM only)."""
	_ = require_permission("recovery.restore")(request)  # GM permission
	
	# Get changelog entry
	changelog = svc.get_changelog()
	entry = next((c for c in changelog if c["id"] == str(changelog_id)), None)
	
	if not entry:
		raise HTTPException(404, "Changelog entry not found")
	
	if entry["status"] != "success":
		raise HTTPException(400, "Can only rollback successful updates")
	
	# Perform rollback
	result = svc.rollback_to_changelog(str(changelog_id))
	
	if not result["ok"]:
		raise HTTPException(400, f"Rollback failed: {result['reason']}")
	
	return {
		"ok": True,
		"message": "Rollback completed successfully",
		"rollback_to_version": entry["version"]
	}


@router.get("/changelog", response_model=List[ChangelogEntry])
async def get_changelog(request: Request):
	"""Get changelog entries."""
	changelog = svc.get_changelog()
	
	result = []
	for entry in changelog:
		result.append(ChangelogEntry(
			id=UUID(entry["id"]),
			version=entry["version"],
			build=entry["build"],
			applied_at=entry["applied_at"],
			status=entry["status"],
			notes=entry.get("notes")
		))
	
	return result


@router.get("/validate/{bundle_id}", response_model=UpdateValidateResult)
async def validate_update(bundle_id: UUID, request: Request):
	"""Validate a specific bundle (GM only)."""
	_ = require_permission("settings.manage_roles")(request)  # GM permission
	
	result = svc.validate_bundle(str(bundle_id))
	
	return UpdateValidateResult(
		bundle_id=UUID(result["bundle_id"]),
		filename=result["filename"],
		version=result["version"],
		build=result["build"],
		signature_ok=result["signature_ok"],
		manifest_ok=result["manifest_ok"],
		reason=result["reason"],
		checksum_sha256=result["checksum_sha256"],
		created_at=result["created_at"]
	)


@router.get("/dependencies/{bundle_id}", response_model=UpdateDependencies)
async def get_dependencies(bundle_id: UUID, request: Request):
	"""Get dependencies for a specific bundle (GM only)."""
	_ = require_permission("settings.manage_roles")(request)  # GM permission
	
	result = svc.compute_dependencies(str(bundle_id))
	
	items = []
	for item in result["items"]:
		items.append({
			"id": item["id"],
			"version": item["version"],
			"satisfied": item["satisfied"],
			"reason": item["reason"]
		})
	
	return UpdateDependencies(
		bundle_id=UUID(result["bundle_id"]),
		items=items,
		all_satisfied=result["all_satisfied"]
	)


@router.get("/progress/{job_id}", response_model=List[UpdateProgressTick])
async def get_update_progress(job_id: UUID, request: Request):
	"""Get progress for a specific job (GM only)."""
	_ = require_permission("settings.manage_roles")(request)  # GM permission
	
	ticks = svc.get_progress(str(job_id))
	
	result = []
	for tick in ticks:
		result.append(UpdateProgressTick(
			job_id=UUID(tick["job_id"]),
			kind=tick["kind"],
			step=tick["step"],
			percent=tick["percent"],
			message=tick["message"],
			occurred_at=tick["occurred_at"]
		))
	
	return result
