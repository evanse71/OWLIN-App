from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from datetime import date
from ..contracts import ItemForecast, AggregateForecast
from ..services.forecasting import forecast_item_prices, forecast_aggregate

router = APIRouter(prefix="/api/forecast", tags=["forecast"]) 


@router.get("/items/{item_id}", response_model=ItemForecast)
async def get_item_forecast(item_id: UUID, horizon: int = Query(3, ge=1, le=12)):
	try:
		return forecast_item_prices(str(item_id), horizon)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/aggregate/{scope_type}/{scope_id}", response_model=AggregateForecast)
async def get_aggregate_forecast(scope_type: str, scope_id: UUID, horizon: int = Query(3, ge=1, le=12)):
	if scope_type not in ("supplier", "category", "site"):
		raise HTTPException(status_code=400, detail="invalid scope_type")
	try:
		return forecast_aggregate(scope_type, str(scope_id), horizon)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e)) 