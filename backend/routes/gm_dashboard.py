from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timedelta

from ..contracts import DashboardSummary, RefreshRequest
from ..services.permissions import require_permission
from ..services.auth import get_current_user
from ..services import aggregator as agg

router = APIRouter(prefix="/api/gm", tags=["gm-dashboard"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
	request: Request,
	start: str = Query(..., description="Start date (YYYY-MM-DD)"),
	end: str = Query(..., description="End date (YYYY-MM-DD)")
):
	"""Get dashboard summary for user's accessible venues."""
	# Get current user
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Determine user role (simplified - in real app this would come from user roles)
	user_role = "gm"  # Default for testing
	
	# Get venue IDs user has access to
	venue_ids = agg.get_user_venue_ids(str(user["id"]), user_role)
	
	if not venue_ids:
		raise HTTPException(403, "No venues accessible")
	
	# Get dashboard summary
	summary = agg.get_dashboard_summary(start, end, venue_ids)
	
	# Convert to contract format
	from ..contracts import KpiCard, VenueRow, VenueSeries, SeriesPoint
	
	kpi_cards = []
	for card in summary["kpi_cards"]:
		kpi_cards.append(KpiCard(
			title=card["title"],
			value=card["value"],
			delta=card["delta"],
			trend=card["trend"],
			series=card["series"]
		))
	
	venue_comparison = []
	for venue in summary["venue_comparison"]:
		venue_comparison.append(VenueRow(
			venue_id=UUID(venue["venue_id"]),
			venue_name=venue["venue_name"],
			total_invoices=venue["total_invoices"],
			total_spend=venue["total_spend"],
			match_rate=venue["match_rate"],
			avg_confidence=venue["avg_confidence"],
			flagged_issues=venue["flagged_issues"],
			delivery_reliability=venue["delivery_reliability"]
		))
	
	trends = []
	for trend in summary["trends"]:
		series_points = []
		for point in trend["series"]:
			series_points.append(SeriesPoint(
				date=point["date"],
				value=point["value"]
			))
		
		trends.append(VenueSeries(
			venue_id=UUID(trend["venue_id"]),
			venue_name=trend["venue_name"],
			series=series_points
		))
	
	return DashboardSummary(
		period=summary["period"],
		total_venues=summary["total_venues"],
		total_invoices=summary["total_invoices"],
		total_spend=summary["total_spend"],
		avg_match_rate=summary["avg_match_rate"],
		avg_confidence=summary["avg_confidence"],
		total_issues=summary["total_issues"],
		kpi_cards=kpi_cards,
		venue_comparison=venue_comparison,
		trends=trends
	)


@router.post("/dashboard/refresh")
async def refresh_dashboard_data(
	request: Request,
	payload: RefreshRequest
):
	"""Refresh KPI data for specified venues."""
	# Check permissions (GM only)
	_ = require_permission("settings.manage_roles")(request)
	
	# Get current user
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Get venue IDs to refresh
	if payload.venue_ids:
		venue_ids = [str(vid) for vid in payload.venue_ids]
	else:
		# Refresh all venues user has access to
		user_role = "gm"  # Default for testing
		venue_ids = agg.get_user_venue_ids(str(user["id"]), user_role)
	
	# Refresh KPIs
	agg.refresh_venue_kpis(venue_ids, payload.force)
	
	return {
		"ok": True,
		"message": f"Refreshed KPIs for {len(venue_ids)} venues",
		"venue_ids": venue_ids
	}


@router.get("/dashboard/venues")
async def get_accessible_venues(request: Request):
	"""Get list of venues accessible to current user."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	user_role = "gm"  # Default for testing
	venue_ids = agg.get_user_venue_ids(str(user["id"]), user_role)
	
	# Get venue details
	from sqlite3 import connect
	import os
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	venues = []
	for venue_id in venue_ids:
		cur.execute("SELECT id, name, code FROM venues WHERE id = ?", (venue_id,))
		row = cur.fetchone()
		if row:
			venues.append({
				"id": row[0],
				"name": row[1],
				"code": row[2]
			})
	
	conn.close()
	
	return {"venues": venues}


@router.get("/dashboard/kpis/{venue_id}")
async def get_venue_kpis(
	request: Request,
	venue_id: str,
	start: str = Query(..., description="Start date (YYYY-MM-DD)"),
	end: str = Query(..., description="End date (YYYY-MM-DD)")
):
	"""Get detailed KPIs for a specific venue."""
	user = get_current_user(request)
	if not user:
		raise HTTPException(401, "Not authenticated")
	
	# Check if user has access to this venue
	user_role = "gm"  # Default for testing
	accessible_venues = agg.get_user_venue_ids(str(user["id"]), user_role)
	
	if venue_id not in accessible_venues:
		raise HTTPException(403, "Venue not accessible")
	
	# Get KPIs for the venue
	kpis = agg._compute_venue_kpis(venue_id, start, end)
	
	# Get venue name
	from sqlite3 import connect
	import os
	
	db_path = os.path.join("data", "owlin.db")
	conn = connect(db_path)
	cur = conn.cursor()
	
	cur.execute("SELECT name FROM venues WHERE id = ?", (venue_id,))
	venue_name = cur.fetchone()[0] if cur.fetchone() else "Unknown"
	conn.close()
	
	return {
		"venue_id": venue_id,
		"venue_name": venue_name,
		"period": f"{start} to {end}",
		"total_invoices": kpis["total_invoices"],
		"total_spend": kpis["total_spend_pennies"] / 100.0,
		"match_rate": kpis["match_rate"],
		"avg_confidence": kpis["avg_confidence"],
		"flagged_issues": kpis["flagged_issues"],
		"delivery_reliability": kpis["delivery_reliability"]
	} 