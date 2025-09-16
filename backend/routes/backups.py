from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from uuid import UUID
from typing import List

from contracts import BackupInfo, BackupCreateResult, RestorePreview
from services import permissions
from services import backup as backup_service

router = APIRouter(prefix="/backups", tags=["backups"])


@router.get("", response_model=List[BackupInfo])
async def list_backups(request: Request):
    """List all backups."""
    backups = backup_service.backup_list()
    
    result = []
    for backup in backups:
        result.append(BackupInfo(
            id=UUID(backup["id"]),
            created_at=backup["created_at"],
            path=backup["path"],
            size_bytes=backup["size_bytes"],
            mode=backup["mode"],
            app_version=backup["app_version"],
            db_schema_version=backup["db_schema_version"]
        ))
    
    return result


@router.post("", response_model=BackupCreateResult)
async def create_backup(request: Request):
    """Create a new backup (GM/Finance only)."""
    _ = require_permission("data.backup.create")(request)
    
    try:
        result = backup_service.backup_create('manual')
        
        return BackupCreateResult(
            id=UUID(result["id"]),
            created_at=result["created_at"],
            path=result["path"],
            size_bytes=result["size_bytes"]
        )
    except Exception as e:
        raise HTTPException(400, f"Backup creation failed: {str(e)}")


@router.post("/restore")
async def restore_backup(
    backup_id: UUID,
    dry_run: bool = Query(True, description="Preview only if True"),
    request: Request = None
):
    """Restore from backup (GM only for actual restore)."""
    if not dry_run:
        _ = require_permission("data.backup.restore")(request)
    
    try:
        if dry_run:
            result = backup_service.restore_preview(str(backup_id))
            
            changes = []
            for change in result.get("changes", []):
                changes.append({
                    "table": change["table"],
                    "adds": change["adds"],
                    "updates": change["updates"],
                    "deletes": change["deletes"]
                })
            
            return RestorePreview(
                backup_id=backup_id,
                ok=result["ok"],
                reason=result.get("reason"),
                changes=changes
            )
        else:
            result = backup_service.restore_commit(str(backup_id))
            
            if not result["ok"]:
                raise HTTPException(400, result["reason"])
            
            return {
                "ok": True,
                "message": "Restore completed successfully",
                "pre_restore_backup_id": result.get("pre_restore_backup_id")
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Restore failed: {str(e)}")
