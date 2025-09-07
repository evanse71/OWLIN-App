from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from uuid import UUID

from contracts import (
    SupplierEventRequest, SupplierEventResponse, SupplierEventsResponse,
    SupplierInsightsResponse, SupplierAlertsResponse
)
from services.supplier_behaviour_service import (
    log_event, list_events, get_insights, list_alerts
)

router = APIRouter(prefix="/supplier-behaviour", tags=["supplier-behaviour"])


def get_current_user():
    """Mock authentication - replace with actual auth in production."""
    return "test_user"


@router.post("/event", response_model=SupplierEventResponse)
async def create_supplier_event(request: SupplierEventRequest):
    """
    Log a supplier event.
    
    Creates a new supplier event and triggers insights recalculation.
    """
    try:
        user_id = get_current_user()
        result = log_event(request, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log event: {str(e)}")


@router.get("/events/{supplier_id}", response_model=SupplierEventsResponse)
async def get_supplier_events(
    supplier_id: UUID,
    limit: int = Query(default=20, ge=1, le=200, description="Maximum number of events to return")
):
    """
    Get events for a supplier.
    
    Returns the most recent events for the specified supplier.
    """
    try:
        result = list_events(str(supplier_id), limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get events: {str(e)}")


@router.get("/insights/{supplier_id}", response_model=SupplierInsightsResponse)
async def get_supplier_insights(supplier_id: UUID):
    """
    Get insights for a supplier.
    
    Returns calculated insights and trends for the specified supplier.
    """
    try:
        result = get_insights(str(supplier_id))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.get("/alerts", response_model=SupplierAlertsResponse)
async def get_supplier_alerts():
    """
    Get supplier alerts.
    
    Returns suppliers with high severity or repeated recent issues.
    """
    try:
        result = list_alerts()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}") 