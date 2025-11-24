# -*- coding: utf-8 -*-
"""
Forecast Route

This module implements the GET /api/forecast/{item_id} endpoint that returns
forecast data for trend graphs as specified in System Bible Section 2.11 (line 231).
"""

from __future__ import annotations
import logging
from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from backend.services.forecast_engine import get_forecast_for_item

LOGGER = logging.getLogger("owlin.routes.forecast")
router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("/{item_id}")
async def get_forecast(item_id: str) -> Dict[str, Any]:
    """
    Get forecast data for an item.
    
    Returns forecast points (1, 3, 12 months) with confidence bands for trend graphs.
    
    Args:
        item_id: Item ID to forecast
    
    Returns:
        Dictionary with trend data and forecast points
    """
    try:
        forecast_data = get_forecast_for_item(item_id)
        
        if not forecast_data:
            raise HTTPException(
                status_code=404,
                detail=f"No forecast data available for item {item_id}. Need at least 3 price observations."
            )
        
        return forecast_data
        
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Error getting forecast for item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get forecast: {str(e)}")

