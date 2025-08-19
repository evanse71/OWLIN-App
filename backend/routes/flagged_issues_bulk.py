from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts import (
    BulkUpdateRequest, BulkEscalateRequest, BulkAssignRequest, BulkCommentRequest,
    BulkActionResponse
)
from services.flagged_issue_service import (
    bulk_update_issues, bulk_escalate_issues, bulk_assign_issues, bulk_comment_issues
)

router = APIRouter(prefix="/flagged-issues", tags=["flagged-issues-bulk"])

# Mock user authentication - in production, this would come from JWT/session
def get_current_user():
    """Mock current user - in production, extract from JWT token."""
    return {
        "id": "user-123",
        "role": "gm"  # Mock role - in production, get from user record
    }

@router.post("/bulk-update", response_model=BulkActionResponse)
async def bulk_update_flagged_issues(
    request: BulkUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Bulk resolve or dismiss flagged issues.
    
    Requires GM or Finance role.
    """
    try:
        response = bulk_update_issues(request, current_user["id"], current_user["role"])
        
        if not response.ok:
            raise HTTPException(status_code=400, detail=response.message)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bulk update: {str(e)}")

@router.post("/bulk-escalate", response_model=BulkActionResponse)
async def bulk_escalate_flagged_issues(
    request: BulkEscalateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Bulk escalate flagged issues to GM or Finance.
    
    Requires GM role.
    """
    try:
        response = bulk_escalate_issues(request, current_user["id"], current_user["role"])
        
        if not response.ok:
            raise HTTPException(status_code=400, detail=response.message)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bulk escalation: {str(e)}")

@router.post("/bulk-assign", response_model=BulkActionResponse)
async def bulk_assign_flagged_issues(
    request: BulkAssignRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Bulk assign flagged issues to a team member.
    
    Requires GM or Finance role.
    """
    try:
        response = bulk_assign_issues(request, current_user["id"], current_user["role"])
        
        if not response.ok:
            raise HTTPException(status_code=400, detail=response.message)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bulk assignment: {str(e)}")

@router.post("/bulk-comment", response_model=BulkActionResponse)
async def bulk_comment_flagged_issues(
    request: BulkCommentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Bulk comment on flagged issues.
    
    Requires GM, Finance, or Shift Lead role.
    """
    try:
        response = bulk_comment_issues(request, current_user["id"], current_user["role"])
        
        if not response.ok:
            raise HTTPException(status_code=400, detail=response.message)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bulk comment: {str(e)}") 