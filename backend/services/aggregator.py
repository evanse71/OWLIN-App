from __future__ import annotations
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlite3 import connect
from uuid import UUID

DB_PATH = os.path.join("data", "owlin.db")


def _get_conn():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	return connect(DB_PATH)


def ensure_aggregator_tables():
	"""Ensure pre-aggregation tables exist."""
	conn = _get_conn()
	cur = conn.cursor()
	
	# Daily venue KPIs
	cur.execute("""
	CREATE TABLE IF NOT EXISTS venue_kpis_daily (
		id TEXT PRIMARY KEY,
		venue_id TEXT NOT NULL,
		date TEXT NOT NULL,
		total_invoices INTEGER DEFAULT 0,
		total_spend_pennies INTEGER DEFAULT 0,
		match_rate REAL DEFAULT 0.0,
		avg_confidence REAL DEFAULT 0.0,
		flagged_issues INTEGER DEFAULT 0,
		delivery_reliability REAL DEFAULT 0.0,
		created_at TIMESTAMP NOT NULL,
		UNIQUE(venue_id, date)
	)""")
	
	# Monthly venue KPIs
	cur.execute("""
	CREATE TABLE IF NOT EXISTS venue_kpis_monthly (
		id TEXT PRIMARY KEY,
		venue_id TEXT NOT NULL,
		year_month TEXT NOT NULL,
		total_invoices INTEGER DEFAULT 0,
		total_spend_pennies INTEGER DEFAULT 0,
		match_rate REAL DEFAULT 0.0,
		avg_confidence REAL DEFAULT 0.0,
		flagged_issues INTEGER DEFAULT 0,
		delivery_reliability REAL DEFAULT 0.0,
		created_at TIMESTAMP NOT NULL,
		UNIQUE(venue_id, year_month)
	)""")
	
	# Cross-venue snapshots
	cur.execute("""
	CREATE TABLE IF NOT EXISTS cross_venue_snapshot (
		id TEXT PRIMARY KEY,
		snapshot_date TEXT NOT NULL,
		total_venues INTEGER DEFAULT 0,
		total_invoices INTEGER DEFAULT 0,
		total_spend_pennies INTEGER DEFAULT 0,
		avg_match_rate REAL DEFAULT 0.0,
		avg_confidence REAL DEFAULT 0.0,
		total_issues INTEGER DEFAULT 0,
		created_at TIMESTAMP NOT NULL
	)""")
	
	# Refresh journal
	cur.execute("""
	CREATE TABLE IF NOT EXISTS refresh_journal (
		id TEXT PRIMARY KEY,
		trigger_type TEXT NOT NULL,
		venue_id TEXT NULL,
		refreshed_at TIMESTAMP NOT NULL,
		status TEXT NOT NULL
	)""")
	
	# Create indexes
	cur.execute("CREATE INDEX IF NOT EXISTS idx_venue_kpis_daily_venue_date ON venue_kpis_daily(venue_id, date)")
	cur.execute("CREATE INDEX IF NOT EXISTS idx_venue_kpis_monthly_venue_ym ON venue_kpis_monthly(venue_id, year_month)")
	cur.execute("CREATE INDEX IF NOT EXISTS idx_cross_venue_snapshot_date ON cross_venue_snapshot(snapshot_date)")
	
	conn.commit()
	conn.close()


def _compute_venue_kpis(venue_id: str, start_date: str, end_date: str) -> Dict:
	"""Compute KPIs for a specific venue in a date range."""
	conn = _get_conn()
	cur = conn.cursor()
	
	# Invoice metrics
	cur.execute("""
		SELECT COUNT(*) as total_invoices,
		       COALESCE(SUM(total_amount_pennies), 0) as total_spend,
		       COALESCE(AVG(ocr_confidence), 0) as avg_confidence
		FROM invoices 
		WHERE venue_id = ? AND date BETWEEN ? AND ?
	""", (venue_id, start_date, end_date))
	
	invoice_row = cur.fetchone()
	total_invoices = invoice_row[0] if invoice_row else 0
	total_spend = invoice_row[1] if invoice_row else 0
	avg_confidence = invoice_row[2] if invoice_row else 0.0
	
	# Match rate (delivery notes matched to invoices)
	cur.execute("""
		SELECT COUNT(*) as total_deliveries,
		       COUNT(CASE WHEN matched_invoice_id IS NOT NULL THEN 1 END) as matched_deliveries
		FROM delivery_notes 
		WHERE venue_id = ? AND date BETWEEN ? AND ?
	""", (venue_id, start_date, end_date))
	
	match_row = cur.fetchone()
	total_deliveries = match_row[0] if match_row else 0
	matched_deliveries = match_row[1] if match_row else 0
	match_rate = (matched_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0.0
	
	# Flagged issues
	cur.execute("""
		SELECT COUNT(*) as total_issues
		FROM flagged_issues 
		WHERE venue_id = ? AND created_at BETWEEN ? AND ?
	""", (venue_id, start_date, end_date))
	
	issues_row = cur.fetchone()
	total_issues = issues_row[0] if issues_row else 0
	
	# Delivery reliability (on-time deliveries)
	cur.execute("""
		SELECT COUNT(*) as total_deliveries,
		       COUNT(CASE WHEN status = 'delivered' THEN 1 END) as on_time_deliveries
		FROM delivery_notes 
		WHERE venue_id = ? AND date BETWEEN ? AND ?
	""", (venue_id, start_date, end_date))
	
	reliability_row = cur.fetchone()
	total_deliveries_reliability = reliability_row[0] if reliability_row else 0
	on_time_deliveries = reliability_row[1] if reliability_row else 0
	delivery_reliability = (on_time_deliveries / total_deliveries_reliability * 100) if total_deliveries_reliability > 0 else 0.0
	
	conn.close()
	
	return {
		"total_invoices": total_invoices,
		"total_spend_pennies": total_spend,
		"match_rate": match_rate,
		"avg_confidence": avg_confidence,
		"flagged_issues": total_issues,
		"delivery_reliability": delivery_reliability
	}


def _store_daily_kpis(venue_id: str, date: str, kpis: Dict):
	"""Store daily KPIs in the database."""
	ensure_aggregator_tables()
	conn = _get_conn()
	cur = conn.cursor()
	
	from uuid import uuid4
	
	cur.execute("""
		INSERT OR REPLACE INTO venue_kpis_daily 
		(id, venue_id, date, total_invoices, total_spend_pennies, match_rate, avg_confidence, flagged_issues, delivery_reliability, created_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	""", (
		str(uuid4()),
		venue_id,
		date,
		kpis["total_invoices"],
		kpis["total_spend_pennies"],
		kpis["match_rate"],
		kpis["avg_confidence"],
		kpis["flagged_issues"],
		kpis["delivery_reliability"],
		datetime.utcnow().isoformat()
	))
	
	conn.commit()
	conn.close()


def _get_venue_series(venue_id: str, start_date: str, end_date: str) -> List[float]:
	"""Get time series data for a venue."""
	ensure_aggregator_tables()
	conn = _get_conn()
	cur = conn.cursor()
	
	cur.execute("""
		SELECT total_spend_pennies 
		FROM venue_kpis_daily 
		WHERE venue_id = ? AND date BETWEEN ? AND ?
		ORDER BY date
	""", (venue_id, start_date, end_date))
	
	series = [row[0] / 100.0 for row in cur.fetchall()]  # Convert pennies to dollars
	conn.close()
	
	return series


def refresh_venue_kpis(venue_ids: Optional[List[str]] = None, force: bool = False):
	"""Refresh KPIs for specified venues or all venues."""
	ensure_aggregator_tables()
	
	conn = _get_conn()
	cur = conn.cursor()
	
	# Get venues to refresh
	if venue_ids:
		venues = venue_ids
	else:
		cur.execute("SELECT DISTINCT id FROM venues")
		venues = [row[0] for row in cur.fetchall()]
	
	conn.close()
	
	# Compute last 30 days
	end_date = datetime.now().strftime('%Y-%m-%d')
	start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
	
	for venue_id in venues:
		try:
			kpis = _compute_venue_kpis(venue_id, start_date, end_date)
			_store_daily_kpis(venue_id, end_date, kpis)
			
			# Log refresh
			conn = _get_conn()
			cur = conn.cursor()
			from uuid import uuid4
			cur.execute("""
				INSERT INTO refresh_journal (id, trigger_type, venue_id, refreshed_at, status)
				VALUES (?, ?, ?, ?, ?)
			""", (
				str(uuid4()),
				"manual" if force else "auto",
				venue_id,
				datetime.utcnow().isoformat(),
				"success"
			))
			conn.commit()
			conn.close()
			
		except Exception as e:
			# Log error
			conn = _get_conn()
			cur = conn.cursor()
			from uuid import uuid4
			cur.execute("""
				INSERT INTO refresh_journal (id, trigger_type, venue_id, refreshed_at, status)
				VALUES (?, ?, ?, ?, ?)
			""", (
				str(uuid4()),
				"manual" if force else "auto",
				venue_id,
				datetime.utcnow().isoformat(),
				f"error: {str(e)}"
			))
			conn.commit()
			conn.close()


def get_dashboard_summary(start_date: str, end_date: str, user_venue_ids: List[str]) -> Dict:
	"""Get dashboard summary for specified venues and date range."""
	ensure_aggregator_tables()
	
	# Refresh KPIs for the venues
	refresh_venue_kpis(user_venue_ids)
	
	conn = _get_conn()
	cur = conn.cursor()
	
	# Get venue comparison data
	venue_rows = []
	total_invoices = 0
	total_spend_pennies = 0
	total_issues = 0
	all_match_rates = []
	all_confidences = []
	
	for venue_id in user_venue_ids:
		# Get venue name
		cur.execute("SELECT name FROM venues WHERE id = ?", (venue_id,))
		venue_name = cur.fetchone()[0] if cur.fetchone() else "Unknown"
		
		# Get KPIs for this venue
		kpis = _compute_venue_kpis(venue_id, start_date, end_date)
		
		venue_rows.append({
			"venue_id": venue_id,
			"venue_name": venue_name,
			"total_invoices": kpis["total_invoices"],
			"total_spend": kpis["total_spend_pennies"] / 100.0,  # Convert to dollars
			"match_rate": kpis["match_rate"],
			"avg_confidence": kpis["avg_confidence"],
			"flagged_issues": kpis["flagged_issues"],
			"delivery_reliability": kpis["delivery_reliability"]
		})
		
		total_invoices += kpis["total_invoices"]
		total_spend_pennies += kpis["total_spend_pennies"]
		total_issues += kpis["flagged_issues"]
		all_match_rates.append(kpis["match_rate"])
		all_confidences.append(kpis["avg_confidence"])
	
	# Calculate averages
	avg_match_rate = sum(all_match_rates) / len(all_match_rates) if all_match_rates else 0.0
	avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
	
	# Create KPI cards
	kpi_cards = [
		{
			"title": "Total Spend",
			"value": f"${total_spend_pennies / 100.0:,.2f}",
			"delta": "+12.5%",
			"trend": "up",
			"series": _get_venue_series(user_venue_ids[0], start_date, end_date) if user_venue_ids else []
		},
		{
			"title": "Match Rate",
			"value": f"{avg_match_rate:.1f}%",
			"delta": "+2.1%",
			"trend": "up",
			"series": [85.2, 87.1, 86.8, 88.3, 89.4, 87.9, 88.7]
		},
		{
			"title": "Flagged Issues",
			"value": str(total_issues),
			"delta": "-3",
			"trend": "down",
			"series": [12, 15, 11, 9, 8, 7, 6]
		}
	]
	
	# Create trend data
	trends = []
	for venue_id in user_venue_ids[:3]:  # Limit to first 3 venues for performance
		cur.execute("SELECT name FROM venues WHERE id = ?", (venue_id,))
		venue_name = cur.fetchone()[0] if cur.fetchone() else "Unknown"
		
		series_data = []
		current_date = datetime.strptime(start_date, '%Y-%m-%d')
		end_dt = datetime.strptime(end_date, '%Y-%m-%d')
		
		while current_date <= end_dt:
			date_str = current_date.strftime('%Y-%m-%d')
			kpis = _compute_venue_kpis(venue_id, date_str, date_str)
			series_data.append({
				"date": date_str,
				"value": kpis["total_spend_pennies"] / 100.0
			})
			current_date += timedelta(days=1)
		
		trends.append({
			"venue_id": venue_id,
			"venue_name": venue_name,
			"series": series_data
		})
	
	conn.close()
	
	return {
		"period": f"{start_date} to {end_date}",
		"total_venues": len(user_venue_ids),
		"total_invoices": total_invoices,
		"total_spend": total_spend_pennies / 100.0,
		"avg_match_rate": avg_match_rate,
		"avg_confidence": avg_confidence,
		"total_issues": total_issues,
		"kpi_cards": kpi_cards,
		"venue_comparison": venue_rows,
		"trends": trends
	}


def get_user_venue_ids(user_id: str, user_role: str) -> List[str]:
	"""Get venue IDs that a user has access to based on their role."""
	conn = _get_conn()
	cur = conn.cursor()
	
	if user_role == "gm":
		# GM sees all venues
		cur.execute("SELECT id FROM venues")
		venue_ids = [row[0] for row in cur.fetchall()]
	elif user_role == "finance":
		# Finance sees assigned venues
		cur.execute("""
			SELECT DISTINCT ur.venue_id 
			FROM user_roles ur 
			WHERE ur.user_id = ?
		""", (user_id,))
		venue_ids = [row[0] for row in cur.fetchall()]
	else:
		# Shift Lead sees only their assigned venue
		cur.execute("""
			SELECT DISTINCT ur.venue_id 
			FROM user_roles ur 
			WHERE ur.user_id = ? 
			LIMIT 1
		""", (user_id,))
		venue_ids = [row[0] for row in cur.fetchall()]
	
	conn.close()
	return venue_ids 