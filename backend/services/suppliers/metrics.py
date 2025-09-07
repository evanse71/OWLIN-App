from __future__ import annotations
from datetime import date
from statistics import median
from sqlite3 import connect
import os

DB_PATH = os.path.join("data", "owlin.db")


def _get_conn():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	return connect(DB_PATH)


def compute_monthly_metrics(supplier_id: str, venue_id: str, month_start: date, month_end: date) -> tuple[float, float, float]:
	"""Compute monthly metrics for a supplier."""
	conn = _get_conn()
	cur = conn.cursor()
	
	# Get invoices in date range
	cur.execute("""
		SELECT COUNT(*) as total_invoices
		FROM invoices 
		WHERE supplier_id = ? AND venue_id = ? AND date BETWEEN ? AND ?
	""", (supplier_id, venue_id, month_start.isoformat(), month_end.isoformat()))
	
	total_invoices = cur.fetchone()[0] or 1
	
	# Get flagged issues
	cur.execute("""
		SELECT COUNT(*) as total_issues,
		       COUNT(CASE WHEN type IN ('PRICE', 'QTY') AND status IN ('OPEN', 'ESCALATED') THEN 1 END) as mismatch_issues
		FROM flagged_issues 
		WHERE supplier_id = ? AND venue_id = ? AND created_at BETWEEN ? AND ?
	""", (supplier_id, venue_id, month_start.isoformat(), month_end.isoformat()))
	
	issues_row = cur.fetchone()
	total_issues = issues_row[0] if issues_row else 0
	mismatch_open = issues_row[1] if issues_row else 0
	
	# Calculate mismatch rate
	mismatch_rate = (mismatch_open / total_invoices * 100.0) if total_invoices > 0 else 0.0
	
	# Get delivery notes
	cur.execute("""
		SELECT COUNT(*) as total_deliveries,
		       COUNT(CASE WHEN date <= COALESCE(expected_date, date) THEN 1 END) as on_time_deliveries
		FROM delivery_notes 
		WHERE supplier_id = ? AND venue_id = ? AND date BETWEEN ? AND ?
	""", (supplier_id, venue_id, month_start.isoformat(), month_end.isoformat()))
	
	delivery_row = cur.fetchone()
	total_deliveries = delivery_row[0] if delivery_row else 1
	on_time_ok = delivery_row[1] if delivery_row else 0
	
	# Calculate on-time rate
	on_time_rate = (on_time_ok / total_deliveries * 100.0) if total_deliveries > 0 else 0.0
	
	# Calculate price volatility (simplified - median absolute deviation of unit prices)
	cur.execute("""
		SELECT unit_price_pennies
		FROM invoice_line_items ili
		JOIN invoices i ON ili.invoice_id = i.id
		WHERE i.supplier_id = ? AND i.venue_id = ? AND i.date BETWEEN ? AND ?
		AND ili.unit_price_pennies IS NOT NULL
	""", (supplier_id, venue_id, month_start.isoformat(), month_end.isoformat()))
	
	prices = [row[0] for row in cur.fetchall()]
	
	if len(prices) > 1:
		median_price = median(prices)
		abs_deviations = [abs(p - median_price) for p in prices]
		volatility = median(abs_deviations) / median_price * 100.0 if median_price > 0 else 0.0
	else:
		volatility = 0.0
	
	conn.close()
	
	return round(mismatch_rate, 2), round(on_time_rate, 2), round(volatility, 2)


def store_monthly_metrics(supplier_id: str, venue_id: str, month: date, mismatch_rate: float, on_time_rate: float, price_volatility: float):
	"""Store monthly metrics in the database."""
	from uuid import uuid4
	from datetime import datetime
	
	conn = _get_conn()
	cur = conn.cursor()
	
	# Ensure table exists
	cur.execute("""
	CREATE TABLE IF NOT EXISTS supplier_metrics_monthly (
		id TEXT PRIMARY KEY,
		supplier_id TEXT NOT NULL,
		venue_id TEXT NOT NULL,
		month DATE NOT NULL,
		mismatch_rate REAL NOT NULL DEFAULT 0,
		on_time_rate REAL NOT NULL DEFAULT 0,
		price_volatility REAL NOT NULL DEFAULT 0,
		updated_at TIMESTAMP NOT NULL,
		UNIQUE (supplier_id, venue_id, month)
	)""")
	
	cur.execute("""
		INSERT OR REPLACE INTO supplier_metrics_monthly 
		(id, supplier_id, venue_id, month, mismatch_rate, on_time_rate, price_volatility, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	""", (
		str(uuid4()),
		supplier_id,
		venue_id,
		month.isoformat(),
		mismatch_rate,
		on_time_rate,
		price_volatility,
		datetime.utcnow().isoformat()
	))
	
	conn.commit()
	conn.close()


def get_latest_metrics(supplier_id: str, venue_id: str) -> tuple[float, float, float]:
	"""Get the latest metrics for a supplier."""
	conn = _get_conn()
	cur = conn.cursor()
	
	# Ensure table exists
	cur.execute("""
	CREATE TABLE IF NOT EXISTS supplier_metrics_monthly (
		id TEXT PRIMARY KEY,
		supplier_id TEXT NOT NULL,
		venue_id TEXT NOT NULL,
		month DATE NOT NULL,
		mismatch_rate REAL NOT NULL DEFAULT 0,
		on_time_rate REAL NOT NULL DEFAULT 0,
		price_volatility REAL NOT NULL DEFAULT 0,
		updated_at TIMESTAMP NOT NULL,
		UNIQUE (supplier_id, venue_id, month)
	)""")
	
	cur.execute("""
		SELECT mismatch_rate, on_time_rate, price_volatility
		FROM supplier_metrics_monthly 
		WHERE supplier_id = ? AND venue_id = ?
		ORDER BY month DESC
		LIMIT 1
	""", (supplier_id, venue_id))
	
	row = cur.fetchone()
	conn.close()
	
	if row:
		return row[0], row[1], row[2]
	else:
		# Fallback: compute current month metrics
		from datetime import date
		today = date.today()
		month_start = date(today.year, today.month, 1)
		month_end = date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)
		
		return compute_monthly_metrics(supplier_id, venue_id, month_start, month_end) 