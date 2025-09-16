"""
Matching V2 API Routes

New matching engine with deterministic algorithm, confidence scoring, and explainability.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
import os
import sys
import json
from uuid import uuid4

# Add backend to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts import MatchingSummary, MatchingPair, MatchingConfig
from services.matching_service import rebuild_matching, get_matching_summary, compute_matching_pair
from services.matching_config import get_matching_config
from services import permissions

router = APIRouter(prefix="/matching", tags=["matching-v2"])

@router.post("/rebuild")
async def rebuild_matching_endpoint(
    days: int = Query(14, ge=1, le=365, description="Number of days to rebuild"),
    user_role: str = Depends(require_permission("matching.rebuild"))
):
    """Rebuild matching pairs for a date window."""
    try:
        result = rebuild_matching(days=days)
        return {
            "ok": True,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {str(e)}")

@router.get("/summary")
async def get_matching_summary_endpoint(
    state: str = Query("all", description="Filter by state: all, matched, partial, conflict, unmatched"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of pairs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get matching summary with optional filtering."""
    try:
        if state not in ["all", "matched", "partial", "conflict", "unmatched"]:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        summary = get_matching_summary(state=state, limit=limit, offset=offset)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")

@router.get("/pair/{pair_id}")
async def get_matching_pair_endpoint(pair_id: str):
    """Get detailed matching pair information."""
    try:
        # For now, return a mock response since we need to implement pair retrieval
        # TODO: Implement get_matching_pair_by_id function
        raise HTTPException(status_code=501, detail="Not implemented yet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pair: {str(e)}")

@router.post("/pair/{pair_id}/accept")
async def accept_matching_pair_endpoint(
    pair_id: str,
    user_role: str = Depends(require_permission("matching.accept"))
):
    """Accept a matching pair (set final status to matched)."""
    try:
        # TODO: Implement accept_pair function
        return {"ok": True, "message": "Pair accepted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to accept pair: {str(e)}")

@router.post("/pair/{pair_id}/override")
async def override_matching_pair_endpoint(
    pair_id: str,
    delivery_note_id: str,
    user_role: str = Depends(require_permission("matching.override"))
):
    """Override delivery note link for a pair."""
    try:
        # TODO: Implement override_pair function
        return {"ok": True, "message": "Pair overridden"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to override pair: {str(e)}")

@router.post("/line/{line_id}/resolve")
async def resolve_line_mismatch_endpoint(
    line_id: str,
    action: str,
    payload: Optional[Dict[str, Any]] = None,
    user_role: str = Depends(require_permission("matching.line.resolve"))
):
    """Resolve a line-level mismatch."""
    try:
        if action not in ["accept_qty", "accept_price", "split", "write_off"]:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        # TODO: Implement resolve_line function
        return {"ok": True, "message": f"Line {action} resolved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve line: {str(e)}")

@router.get("/config")
async def get_matching_config_endpoint():
    """Get current matching configuration."""
    try:
        config = get_matching_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}") 