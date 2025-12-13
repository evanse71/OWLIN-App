from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import date
from uuid import UUID
import sqlite3
import os
from ..contracts import InsightSummary, MetricSeries, InsightAlertsResponse
from ..services.insights import build_summary, _sum_spend, _price_volatility, _on_time_rate, _mismatch_rate, _confidence_median

router = APIRouter(prefix="/api/insights", tags=["insights"])


def get_cursor():
	db_path = os.path.join("data", "owlin.db")
	os.makedirs(os.path.dirname(db_path), exist_ok=True)
	conn = sqlite3.connect(db_path)
	return conn, conn.cursor()


@router.get("/suppliers/{supplier_id}/summary", response_model=InsightSummary)
async def get_summary(supplier_id: UUID, start: date, end: date, bucket: str = "month"):
	# Resolve supplier_name via invoices (first occurrence)
	conn, cur = get_cursor()
	cur.execute("SELECT supplier_name FROM invoices WHERE supplier_name IS NOT NULL LIMIT 1")
	row = cur.fetchone()
	supplier_name = row[0] if row else ""
	data = build_summary(cur, supplier_name, str(supplier_id), start, end, bucket)
	conn.close()
	return {
		"supplier_id": supplier_id,
		"period_start": start,
		"period_end": end,
		"top_badges": data["top_badges"],
		"series": data["series"],
	}


@router.get("/suppliers/{supplier_id}/timeseries", response_model=MetricSeries)
async def get_timeseries(supplier_id: UUID, metric: str = "spend", start: date = Query(...), end: date = Query(...), bucket: str = "month"):
	conn, cur = get_cursor()
	# Resolve supplier_name
	cur.execute("SELECT supplier_name FROM invoices WHERE supplier_name IS NOT NULL LIMIT 1")
	row = cur.fetchone()
	supplier_name = row[0] if row else ""
	if metric == "spend":
		res = _sum_spend(cur, supplier_name, start, end, bucket)
	elif metric == "price_volatility":
		res = _price_volatility(cur, supplier_name, start, end, bucket)
	elif metric == "on_time_rate":
		res = _on_time_rate(cur, supplier_name, start, end, bucket)
	elif metric == "mismatch_rate":
		res = _mismatch_rate(cur, str(supplier_id), start, end, bucket)
	elif metric == "confidence_median":
		res = _confidence_median(cur, supplier_name, start, end, bucket)
	else:
		conn.close()
		raise HTTPException(status_code=400, detail="Unknown metric")
	conn.close()
	return res


@router.get("/suppliers/{supplier_id}/alerts", response_model=InsightAlertsResponse)
async def get_alerts(supplier_id: UUID, start: date, end: date):
	# Minimal placeholder: no alerts generated yet
	return {"supplier_id": supplier_id, "alerts": []} 