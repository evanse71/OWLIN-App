"""
Delivery Matching API Routes

Provides endpoints for invoice-delivery note matching with confidence scoring.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import uuid
from uuid import UUID
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts import (
    MatchCandidatesResponse, MatchConfirmRequest, MatchRejectRequest,
    MatchConfirmResponse, MatchRejectResponse, RetryLateResponse
)
from services.delivery_matching import (
    find_candidates, confirm_match, reject_match, retry_late_uploads
)

router = APIRouter(prefix="/matching", tags=["matching"])

@router.get("/candidates/{invoice_id}", response_model=MatchCandidatesResponse)
async def get_match_candidates(
    invoice_id: UUID,
    limit: int = Query(5, ge=1, le=20, description="Maximum number of candidates to return"),
    min_confidence: float = Query(0.0, ge=0.0, le=100.0, description="Minimum confidence score")
):
    """
    Get candidate delivery notes for an invoice with confidence scores.
    
    Returns delivery notes ranked by confidence score, with detailed breakdown
    of how the score was calculated.
    """
    try:
        candidates = find_candidates(str(invoice_id), min_confidence, limit)
        
        return MatchCandidatesResponse(
            invoice_id=invoice_id,
            candidate_delivery_notes=candidates
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding candidates: {str(e)}")

@router.post("/confirm", response_model=MatchConfirmResponse)
async def confirm_match_endpoint(request: MatchConfirmRequest):
    """
    Confirm a match between an invoice and delivery note.
    
    This will:
    - Mark both documents as matched
    - Store the pairing in the database
    - Remove the delivery note from unmatched queue
    """
    try:
        result = confirm_match(
            str(request.invoice_id),
            str(request.delivery_note_id),
            "user"  # TODO: Get from auth context
        )
        
        return MatchConfirmResponse(
            status="confirmed",
            confidence=result["confidence"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error confirming match: {str(e)}")

@router.post("/reject", response_model=MatchRejectResponse)
async def reject_match_endpoint(request: MatchRejectRequest):
    """
    Reject a match between an invoice and delivery note.
    
    This will:
    - Record the rejection in matching history
    - Prevent this specific pair from being auto-suggested again
    """
    try:
        result = reject_match(
            str(request.invoice_id),
            str(request.delivery_note_id),
            "user",  # TODO: Get from auth context
            ""  # TODO: Add notes field to request
        )
        
        return MatchRejectResponse(status="rejected")
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rejecting match: {str(e)}")

@router.post("/retry-late", response_model=RetryLateResponse)
async def retry_late_uploads_endpoint():
    """
    Trigger a re-run of the matching engine for all unmatched invoices and delivery notes.
    
    This will:
    - Find new high-confidence matches
    - Auto-confirm matches above 80% confidence
    - Return count of new matches found
    """
    try:
        result = retry_late_uploads()
        
        return RetryLateResponse(
            new_matches_found=result["new_matches_found"],
            message=result["message"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrying matches: {str(e)}")

@router.get("/stats")
async def get_matching_stats():
    """
    Get matching statistics for dashboard display.
    """
    try:
        from services.delivery_matching import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM invoices WHERE status = 'scanned'")
        unmatched_invoices = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM delivery_notes WHERE status = 'parsed'")
        unmatched_delivery_notes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM invoice_delivery_pairs WHERE status = 'confirmed'")
        confirmed_matches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM matching_history WHERE action = 'rejected'")
        rejected_matches = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "unmatched_invoices": unmatched_invoices,
            "unmatched_delivery_notes": unmatched_delivery_notes,
            "confirmed_matches": confirmed_matches,
            "rejected_matches": rejected_matches
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}") 