from __future__ import annotations
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from uuid import UUID
from typing import List

from contracts import SupportPackInfo
from services import permissions
from services import support_pack as support_pack_service

router = APIRouter(prefix="/support-packs", tags=["support-packs"])


@router.get("", response_model=List[SupportPackInfo])
async def list_packs(request: Request):
    """List all support packs (GM/Finance/Shift Lead)."""
    _ = require_permission("data.support.view")(request)
    
    packs = support_pack_service.pack_list()
    
    result = []
    for pack in packs:
        result.append(SupportPackInfo(
            id=UUID(pack["id"]),
            created_at=pack["created_at"],
            path=pack["path"],
            size_bytes=pack["size_bytes"],
            notes=pack.get("notes"),
            app_version=pack["app_version"]
        ))
    
    return result


@router.post("", response_model=SupportPackInfo)
async def create_pack(notes: str = None, request: Request = None):
    """Create a new support pack (GM/Finance only)."""
    _ = require_permission("data.support.create")(request)
    
    try:
        result = support_pack_service.pack_create(notes)
        
        return SupportPackInfo(
            id=UUID(result["id"]),
            created_at=result["created_at"],
            path=result["path"],
            size_bytes=result["size_bytes"],
            notes=result.get("notes"),
            app_version=result["app_version"]
        )
    except Exception as e:
        raise HTTPException(400, f"Support pack creation failed: {str(e)}")


@router.get("/{pack_id}/download")
async def download_pack(pack_id: UUID, request: Request):
    """Download support pack (GM/Finance/Shift Lead)."""
    _ = require_permission("data.support.view")(request)
    
    try:
        # Get pack info
        pack_info = support_pack_service.pack_get_info(str(pack_id))
        if not pack_info:
            raise HTTPException(404, "Support pack not found")
        
        # Get file path
        pack_path = pack_info["path"]
        if not pack_path or not Path(pack_path).exists():
            raise HTTPException(404, "Support pack file not found")
        
        # Create streaming response
        def generate():
            for chunk in support_pack_service.pack_stream(str(pack_id)):
                if chunk:
                    yield chunk
        
        filename = f"support_pack_{pack_id}.zip"
        
        return StreamingResponse(
            generate(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(pack_info["size_bytes"])
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Download failed: {str(e)}")
