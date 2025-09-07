"""
Quarantine API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from backend.services.support_pack import get_quarantine_service

router = APIRouter(prefix="/api/quarantine", tags=["quarantine"])

class PromoteAssetRequest(BaseModel):
    asset_id: str

@router.get("")
async def list_quarantined_assets():
    """List all quarantined assets with reasons"""
    try:
        service = get_quarantine_service()
        assets = service.list_quarantined_assets()
        
        return {
            "quarantined_assets": assets,
            "total_count": len(assets)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list quarantined assets: {e}")

@router.post("/promote")
async def promote_quarantined_asset(request: PromoteAssetRequest):
    """Promote asset from quarantine back to processing"""
    try:
        service = get_quarantine_service()
        success = service.promote_asset(request.asset_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Asset not found in quarantine")
        
        return {
            "asset_id": request.asset_id,
            "promoted": True
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Failed to promote asset: {e}")

@router.get("/stats")
async def get_quarantine_stats():
    """Get quarantine statistics"""
    try:
        service = get_quarantine_service()
        assets = service.list_quarantined_assets()
        
        # Group by reason
        reason_counts = {}
        for asset in assets:
            reason = asset['reason']
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        return {
            "total_quarantined": len(assets),
            "reasons": reason_counts,
            "common_reasons": [
                "unsupported_mime",
                "decode_timeout", 
                "size_cap_exceeded",
                "ocr_confidence_too_low",
                "parse_failure"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quarantine stats: {e}") 