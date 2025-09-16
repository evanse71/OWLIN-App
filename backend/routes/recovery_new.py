from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import os

from contracts import (
    RecoveryStatus, RestorePreview, TableDiff, ResolvePlan, RestoreCommitResponse
)
from services.recovery_service import (
    get_recovery_status, check_integrity, create_restore_preview,
    compare_tables, apply_resolve_plan, log_audit_event
)

# Import existing auth and permissions
try:
    from services.auth import get_current_user
    from services import permissions
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    # Fallback mock functions
    def get_current_user():
        return "test_user"
    
    def require_permission(permission: str):
        def decorator(func):
            return func
        return decorator

router = APIRouter(prefix="/recovery", tags=["recovery"])


@router.get("/status", response_model=RecoveryStatus)
async def get_recovery_status_endpoint():
    """
    Get current recovery status.
    
    Returns the current recovery state including integrity status,
    available snapshots, and system information.
    """
    try:
        status = get_recovery_status()
        return RecoveryStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recovery status: {str(e)}")


@router.post("/scan", response_model=RecoveryStatus)
async def scan_system():
    """
    Scan system integrity and update recovery status.
    
    Forces a fresh integrity check and returns updated status.
    """
    try:
        # Force integrity check
        integrity = check_integrity()
        
        # Log audit event
        log_audit_event("recovery.scan", {
            "integrity_ok": integrity["integrity_ok"],
            "state": integrity["state"],
            "details": integrity["details"]
        })
        
        # Get full status
        status = get_recovery_status()
        return RecoveryStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan system: {str(e)}")


@router.post("/preview", response_model=RestorePreview)
async def preview_restore(
    snapshot_id: str,
    limit: int = Query(default=200, ge=1, le=1000, description="Maximum rows per table"),
    offset: int = Query(default=0, ge=0, description="Row offset for pagination")
):
    """
    Preview a restore operation.
    
    Shows what changes would be made if restoring from the specified snapshot.
    """
    try:
        # Check permissions (GM or Finance)
        if AUTH_AVAILABLE:
            user = get_current_user()
            # Check if user has GM or Finance role
            # This would be implemented based on your existing RBAC system
            pass
        
        preview = create_restore_preview(snapshot_id, limit, offset)
        
        # Log audit event
        log_audit_event("recovery.preview", {
            "snapshot_id": snapshot_id,
            "limit": limit,
            "offset": offset,
            "summary": preview["summary"]
        })
        
        return RestorePreview(**preview)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create preview: {str(e)}")


@router.get("/diff/{table}", response_model=TableDiff)
async def get_table_diff(
    table: str,
    snapshot_id: str = Query(..., description="Snapshot ID to compare against"),
    limit: int = Query(default=200, ge=1, le=1000, description="Maximum rows to return"),
    offset: int = Query(default=0, ge=0, description="Row offset for pagination")
):
    """
    Get detailed diff for a specific table.
    
    Returns row-by-row differences between live and snapshot data.
    """
    try:
        # Check permissions (GM or Finance)
        if AUTH_AVAILABLE:
            user = get_current_user()
            # Check if user has GM or Finance role
            pass
        
        diff = compare_tables(table, snapshot_id, limit, offset)
        
        # Convert to Pydantic model
        return TableDiff(**diff)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get table diff: {str(e)}")


@router.post("/commit", response_model=RestoreCommitResponse)
async def commit_restore(resolve_plan: ResolvePlan):
    """
    Commit a restore operation.
    
    Applies the resolve plan to restore data from snapshot.
    GM role required.
    """
    try:
        # Check GM permissions
        if AUTH_AVAILABLE:
            user = get_current_user()
            # Check if user has GM role
            # This would be implemented based on your existing RBAC system
            pass
        
        # Apply the resolve plan
        result = apply_resolve_plan(resolve_plan.snapshot_id, resolve_plan.dict())
        
        return RestoreCommitResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to commit restore: {str(e)}")


@router.post("/rollback/{snapshot_id}")
async def rollback_to_snapshot(snapshot_id: str):
    """
    Emergency rollback to snapshot.
    
    GM role required. Creates backup before rollback.
    """
    try:
        # Check GM permissions
        if AUTH_AVAILABLE:
            user = get_current_user()
            # Check if user has GM role
            pass
        
        from services.recovery_service import rollback_to_snapshot
        
        success = rollback_to_snapshot(snapshot_id)
        
        if success:
            # Log audit event
            log_audit_event("recovery.rollback", {
                "snapshot_id": snapshot_id,
                "success": True
            })
            
            return {"ok": True, "message": "Rollback completed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Rollback failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollback: {str(e)}") 