"""
Forecast V2 API Routes

New forecasting endpoints with model selection, confidence intervals, and scenario controls.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
import os
import sys
import json
from uuid import uuid4

# Add backend to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts import ForecastSeries, ForecastQuality, ForecastSummary, ForecastScenario, ForecastJob
from services.forecast_service import (
    compute_forecast, save_forecast, get_forecast_summary, get_forecast_quality
)
from services import permissions

router = APIRouter(prefix="/forecast", tags=["forecast-v2"])

@router.get("/items")
async def get_forecast_items(
    search: Optional[str] = Query(None, description="Search by item name"),
    supplier_id: Optional[int] = Query(None, description="Filter by supplier"),
    venue_id: Optional[int] = Query(None, description="Filter by venue"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get forecast summary for items."""
    try:
        summary = get_forecast_summary(
            limit=limit,
            offset=offset,
            search=search,
            supplier_id=supplier_id,
            venue_id=venue_id
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get forecast summary: {str(e)}")

@router.get("/item/{item_id}")
async def get_item_forecast(
    item_id: int,
    horizon: int = Query(12, ge=1, le=24, description="Forecast horizon in months"),
    supplier_id: Optional[int] = Query(None, description="Filter by supplier"),
    venue_id: Optional[int] = Query(None, description="Filter by venue"),
    scenario: Optional[str] = Query(None, description="JSON-encoded scenario parameters")
):
    """Get detailed forecast for a specific item."""
    try:
        # Parse scenario if provided
        forecast_scenario = None
        if scenario:
            try:
                scenario_data = json.loads(scenario)
                forecast_scenario = ForecastScenario(**scenario_data)
            except (json.JSONDecodeError, ValueError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid scenario format: {str(e)}")
        
        forecast = compute_forecast(
            item_id=item_id,
            horizon_months=horizon,
            supplier_id=supplier_id,
            venue_id=venue_id,
            scenario=forecast_scenario
        )
        
        # Save forecast to database
        save_forecast(forecast)
        
        return forecast
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute forecast: {str(e)}")

@router.get("/quality/{item_id}")
async def get_forecast_quality_endpoint(item_id: int):
    """Get quality metrics for an item's best model."""
    try:
        quality = get_forecast_quality(item_id)
        if not quality:
            raise HTTPException(status_code=404, detail="No quality metrics found for this item")
        return quality
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quality metrics: {str(e)}")

@router.post("/recompute")
async def recompute_forecasts(
    item_ids: Optional[List[int]] = None,
    all: bool = False,
    user_role: str = Depends(require_permission("forecast.recompute"))
):
    """Recompute forecasts for specified items or all items."""
    try:
        if all:
            # TODO: Implement recompute all
            return {"ok": True, "message": "Recompute all queued", "job_id": str(uuid4())}
        elif item_ids:
            # TODO: Implement recompute subset
            return {"ok": True, "message": f"Recompute {len(item_ids)} items queued", "job_id": str(uuid4())}
        else:
            raise HTTPException(status_code=400, detail="Must specify item_ids or all=true")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue recompute: {str(e)}")

@router.get("/config")
async def get_forecast_config():
    """Get current forecast configuration."""
    try:
        config = {
            "window_days": 180,
            "acceptance_threshold": 0.03,
            "min_history_months": 12,
            "models": ["naive", "seasonal_naive", "ewma_0.1", "ewma_0.2", "ewma_0.3", "ewma_0.5", "holt_winters"],
            "default_horizon": 12,
            "confidence_levels": [80, 95]
        }
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

@router.get("/progress")
async def get_forecast_progress():
    """Get progress of queued forecast jobs."""
    try:
        # TODO: Implement job queue progress
        return {
            "total": 0,
            "done": 0,
            "running_item_id": None,
            "pct": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}") 