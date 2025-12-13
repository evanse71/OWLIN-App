import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from enum import Enum

from contracts import SupplierScorecard, SupplierMetric, SupplierInsight

class Trend(str, Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"

def trend_from_delta(delta: float, up_threshold: float = 0.05, down_threshold: float = -0.05) -> Trend:
    if delta > up_threshold:
        return Trend.UP
    if delta < down_threshold:
        return Trend.DOWN
    return Trend.STABLE

DB_PATH = os.path.join("data", "owlin.db")

WEIGHTS = {
	"spend_share": 0.20,
	"reliability": 0.25,
	"pricing_stability": 0.20,
	"error_rate": 0.15,
	"credit_responsiveness": 0.10,
	"doc_confidence": 0.10,
}

NEUTRAL_SCORE = 70.0

def get_conn() -> sqlite3.Connection:
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	return sqlite3.connect(DB_PATH)


def _iso_week(dt: datetime) -> str:
	return f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"


def _linear_map(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
	if x <= x0:
		return y0
	if x >= x1:
		return y1
	# Linear interpolation
	return y0 + (y1 - y0) * ((x - x0) / (x1 - x0))


def _safe_avg(cursor: sqlite3.Cursor, query: str, params: tuple = ()) -> Optional[float]:
	cursor.execute(query, params)
	row = cursor.fetchone()
	if not row or row[0] is None:
		return None
	try:
		return float(row[0])
	except Exception:
		return None


def _safe_count(cursor: sqlite3.Cursor, query: str, params: tuple = ()) -> int:
	cursor.execute(query, params)
	row = cursor.fetchone()
	return int(row[0] or 0)


def _stddev(values: List[float]) -> Optional[float]:
	if not values:
		return None
	import math
	mu = sum(values)/len(values)
	if len(values) == 1:
		return 0.0
	var = sum((v-mu)**2 for v in values)/(len(values)-1)
	return math.sqrt(var)


def _median(values: List[float]) -> Optional[float]:
	if not values:
		return None
	s = sorted(values)
	n = len(s)
	m = n//2
	if n % 2 == 1:
		return s[m]
	return (s[m-1] + s[m]) / 2.0


def _get_invoice_count(cursor: sqlite3.Cursor, supplier_id: str, days: int) -> int:
	# Convert supplier_id to supplier_name for querying
	cursor.execute(
		"""
		SELECT COUNT(*) FROM invoices
		WHERE supplier_name = ? AND invoice_date >= DATE('now', ?)
		""",
		(supplier_id, f"-{days} day"),
	)
	return int(cursor.fetchone()[0] or 0)


def _get_invoice_sum(cursor: sqlite3.Cursor, supplier_id: str, days: int) -> float:
	cursor.execute(
		"""
		SELECT SUM(total_amount) FROM invoices
		WHERE supplier_name = ? AND invoice_date >= DATE('now', ?)
		""",
		(supplier_id, f"-{days} day"),
	)
	row = cursor.fetchone()
	return float(row[0] or 0.0)


def _get_total_sum(cursor: sqlite3.Cursor, days: int) -> float:
	cursor.execute(
		"""
		SELECT SUM(total_amount) FROM invoices
		WHERE invoice_date >= DATE('now', ?)
		""",
		(f"-{days} day",),
	)
	row = cursor.fetchone()
	return float(row[0] or 0.0)


def _get_reliability_pct(cursor: sqlite3.Cursor, supplier_id: str, days: int) -> Optional[float]:
	# For now, use a simplified reliability based on matched delivery notes
	# In a real system, you'd have on_time tracking
	cursor.execute(
		"""
		SELECT COUNT(*) FROM delivery_notes dn
		WHERE dn.supplier_name = ? AND dn.delivery_date >= DATE('now', ?) AND dn.status = 'matched'
		""",
		(supplier_id, f"-{days} day"),
	)
	delivered = int(cursor.fetchone()[0] or 0)
	inv = _get_invoice_count(cursor, supplier_id, days)
	if inv == 0:
		return None
	return delivered / inv


def _get_pricing_cv(cursor: sqlite3.Cursor, supplier_id: str, months: int = 6) -> Optional[float]:
	# Use invoice totals for pricing variance since line_items table doesn't exist
	end_date = datetime.utcnow()
	start_expr = f"-{months*30} day"
	cursor.execute(
		"""
		SELECT total_amount FROM invoices
		WHERE supplier_name = ? AND invoice_date >= DATE('now', ?)
		""",
		(supplier_id, start_expr),
	)
	prices = [float(r[0]) for r in cursor.fetchall() if r[0] is not None]
	if not prices:
		return None
	std = _stddev(prices)
	if std is None:
		return None
	mu = sum(prices)/len(prices)
	if mu == 0:
		return None
	return std / mu


def _get_error_rate(cursor: sqlite3.Cursor, supplier_id: str, days: int) -> Optional[float]:
	inv = _get_invoice_count(cursor, supplier_id, days)
	if inv == 0:
		return None
	cursor.execute(
		"""
		SELECT COUNT(DISTINCT fi.invoice_id) FROM flagged_issues fi
		JOIN invoices i ON fi.invoice_id = i.id
		WHERE i.supplier_name = ? AND i.invoice_date >= DATE('now', ?)
		""",
		(supplier_id, f"-{days} day"),
	)
	issues = int(cursor.fetchone()[0] or 0)
	return issues / inv


def _get_median_credit_days(cursor: sqlite3.Cursor, supplier_id: str) -> Optional[float]:
	cursor.execute(
		"""
		SELECT julianday(resolved_at) - julianday(created_at) AS d
		FROM flagged_issues fi JOIN invoices i ON fi.invoice_id = i.id
		WHERE i.supplier_name = ? AND fi.type = 'credit' AND fi.resolved_at IS NOT NULL
		AND fi.created_at >= DATE('now','-180 day')
		""",
		(supplier_id,),
	)
	diffs = [float(r[0]) for r in cursor.fetchall() if r[0] is not None]
	return _median(diffs)


def _get_avg_ocr_conf(cursor: sqlite3.Cursor, supplier_id: str, days: int) -> Optional[float]:
	cursor.execute(
		"""
		SELECT AVG(confidence) FROM invoices
		WHERE supplier_name = ? AND invoice_date >= DATE('now', ?)
		""",
		(supplier_id, f"-{days} day"),
	)
	row = cursor.fetchone()
	return float(row[0]) if row and row[0] is not None else None


def _score_spend_share(supplier_sum: Optional[float], total_sum: Optional[float]) -> float:
	if not supplier_sum or not total_sum or total_sum <= 0:
		return NEUTRAL_SCORE
	share = supplier_sum/total_sum
	if share >= 0.30:
		return 100.0
	if share <= 0.05:
		return 40.0
	return _linear_map(share, 0.05, 0.30, 40.0, 100.0)


def _score_reliability(p: Optional[float]) -> float:
	if p is None:
		return NEUTRAL_SCORE
	if p >= 0.95:
		return 100.0
	if p >= 0.80:
		return _linear_map(p, 0.80, 0.95, 80.0, 99.0)
	return min(50.0, p*100.0)


def _score_pricing_stability(cv: Optional[float]) -> float:
	if cv is None:
		return NEUTRAL_SCORE
	if cv <= 0.05:
		return 100.0
	if cv >= 0.20:
		return 40.0
	# Map inverse: lower cv is better
	return _linear_map(cv, 0.20, 0.05, 40.0, 100.0)


def _score_error_rate(r: Optional[float]) -> float:
	if r is None:
		return NEUTRAL_SCORE
	if r < 0.05:
		return 100.0
	if r <= 0.15:
		return _linear_map(r, 0.15, 0.05, 70.0, 99.0)
	return 60.0 - (max(0.0, (r-0.15))*100.0)


def _score_credit_days(d: Optional[float]) -> float:
	if d is None:
		return NEUTRAL_SCORE
	if d < 7.0:
		return 100.0
	if d <= 14.0:
		return _linear_map(d, 14.0, 7.0, 70.0, 90.0)
	return 40.0


def _score_doc_conf(c: Optional[float]) -> float:
	if c is None:
		return NEUTRAL_SCORE
	# c is 0..1
	if c >= 0.90:
		return 100.0
	if c <= 0.60:
		return 40.0
	return _linear_map(c, 0.60, 0.90, 40.0, 100.0)


def _trend(curr: Optional[float], prev: Optional[float]) -> Trend:
	if curr is None or prev is None:
		return Trend.STABLE
	if prev == 0:
		return Trend.STABLE
	delta = (curr - prev)/abs(prev)
	if delta > 0.05:
		return Trend.UP
	if delta < -0.05:
		return Trend.DOWN
	return Trend.STABLE


def _detail_spend(share_pct: Optional[float]) -> str:
	if share_pct is None:
		return "Insufficient data — using neutral score (70)."
	return f"{share_pct*100:.1f}% of total spend (90d)"


def _detail_reliability(p: Optional[float]) -> str:
	if p is None:
		return "Insufficient data — using neutral score (70)."
	return f"{p*100:.0f}% on-time"


def _detail_pricing(cv: Optional[float]) -> str:
	if cv is None:
		return "Insufficient data — using neutral score (70)."
	return f"CV={cv:.2f}"


def _detail_error(r: Optional[float]) -> str:
	if r is None:
		return "Insufficient data — using neutral score (70)."
	return f"{r*100:.1f}% invoices with issues"


def _detail_credit(d: Optional[float]) -> str:
	if d is None:
		return "Insufficient data — using neutral score (70)."
	return f"median {d:.0f}d"


def _detail_conf(c: Optional[float]) -> str:
	if c is None:
		return "Insufficient data — using neutral score (70)."
	return f"{c:.2f} avg OCR conf"


def compute_scorecard(supplier_id: str) -> Dict[str, Any]:
	conn = get_conn()
	cursor = conn.cursor()

	# Spend share
	supplier_sum = _get_invoice_sum(cursor, str(supplier_id), 90)
	total_sum = _get_total_sum(cursor, 90)
	spend_share_pct = (supplier_sum/total_sum) if total_sum>0 else None
	spend_score = _score_spend_share(supplier_sum, total_sum)
	spend_prev = None  # simplify

	# Reliability
	rel_pct = _get_reliability_pct(cursor, str(supplier_id), 90)
	rel_score = _score_reliability(rel_pct)
	rel_prev = None

	# Pricing CV
	cv = _get_pricing_cv(cursor, str(supplier_id), 6)
	cv_score = _score_pricing_stability(cv)
	cv_prev = None

	# Error rate
	err = _get_error_rate(cursor, str(supplier_id), 90)
	err_score = _score_error_rate(err)
	err_prev = None

	# Credit responsiveness
	med_days = _get_median_credit_days(cursor, str(supplier_id))
	cred_score = _score_credit_days(med_days)
	cred_prev = None

	# Document confidence
	conf = _get_avg_ocr_conf(cursor, str(supplier_id), 90)
	conf_score = _score_doc_conf(conf)
	conf_prev = None

	# Weighted overall
	scores = {
		"spend_share": spend_score,
		"reliability": rel_score,
		"pricing_stability": cv_score,
		"error_rate": err_score,
		"credit_responsiveness": cred_score,
		"doc_confidence": conf_score,
	}
	overall = 0.0
	for k,v in scores.items():
		overall += max(0.0, min(100.0, v)) * WEIGHTS[k]
	
	# Build metrics
	metrics = {
		"spend_share": SupplierMetric(name="Spend Share", score=spend_score, trend=_trend(spend_share_pct, spend_prev).value, detail=_detail_spend(spend_share_pct)),
		"reliability": SupplierMetric(name="Delivery Reliability", score=rel_score, trend=_trend(rel_pct, rel_prev).value, detail=_detail_reliability(rel_pct)),
		"pricing_stability": SupplierMetric(name="Pricing Stability", score=cv_score, trend=_trend(cv, cv_prev).value, detail=_detail_pricing(cv)),
		"error_rate": SupplierMetric(name="Error Rate", score=err_score, trend=_trend(err, err_prev).value, detail=_detail_error(err)),
		"credit_responsiveness": SupplierMetric(name="Credit Responsiveness", score=cred_score, trend=_trend(med_days, cred_prev).value, detail=_detail_credit(med_days)),
		"doc_confidence": SupplierMetric(name="Document Confidence", score=conf_score, trend=_trend(conf, conf_prev).value, detail=_detail_conf(conf)),
	}
	
	insights = list_insights(supplier_id, limit=50)
	conn.close()
	return SupplierScorecard(
		supplier_id=str(supplier_id),
		overall_score=round(overall),
		categories=metrics,
		insights=insights,
	).dict()


def list_insights(supplier_id: str, limit: int = 50) -> List[SupplierInsight]:
	conn = get_conn()
	cursor = conn.cursor()
	cursor.execute(
		"""
		CREATE TABLE IF NOT EXISTS supplier_insights_feed (
			id TEXT PRIMARY KEY,
			supplier_id TEXT NOT NULL,
			severity TEXT NOT NULL,
			message TEXT NOT NULL,
			timestamp TEXT DEFAULT (datetime('now'))
		)
		"""
	)
	cursor.execute(
		"""SELECT id, supplier_id, severity, message, timestamp FROM supplier_insights_feed
		WHERE supplier_id = ? ORDER BY timestamp DESC LIMIT ?""",
		(str(supplier_id), int(limit)),
	)
	rows = cursor.fetchall()
	conn.close()
	return [SupplierInsight(id=r[0], timestamp=datetime.fromisoformat(r[4]) if 'T' in str(r[4]) else datetime.strptime(r[4], "%Y-%m-%d %H:%M:%S"), severity=r[2], message=r[3]) for r in rows]


def recompute_metrics(supplier_id: str, window_days: int = 90) -> None:
	# For now, compute and persist weekly metric summary rows
	conn = get_conn()
	cursor = conn.cursor()
	cursor.execute(
		"""
		CREATE TABLE IF NOT EXISTS supplier_metrics (
			id INTEGER PRIMARY KEY,
			supplier_id TEXT NOT NULL,
			metric_name TEXT NOT NULL,
			metric_value REAL NOT NULL,
			metric_period TEXT NOT NULL,
			created_at TEXT DEFAULT (datetime('now'))
		)
		"""
	)
	# Example: persist last week's reliability
	rel = _get_reliability_pct(cursor, supplier_id, window_days)
	period = _iso_week(datetime.utcnow())
	if rel is not None:
		cursor.execute(
			"""INSERT INTO supplier_metrics(supplier_id, metric_name, metric_value, metric_period)
			VALUES(?,?,?,?)""",
			(supplier_id, "reliability", float(rel), period),
		)
	conn.commit()
	conn.close()

# Insight generation (simplified registry)

def _emit_insight(cursor: sqlite3.Cursor, supplier_id: str, severity: str, message: str, dedupe_key: str, cooldown_days: int) -> None:
	# Deduplicate by cooldown
	cursor.execute(
		"""SELECT timestamp FROM supplier_insights_feed WHERE supplier_id = ? AND message = ? ORDER BY timestamp DESC LIMIT 1""",
		(supplier_id, message),
	)
	row = cursor.fetchone()
	if row:
		try:
			last = datetime.fromisoformat(row[0]) if 'T' in row[0] else datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
		except Exception:
			last = datetime.utcnow()
		if datetime.utcnow() - last < timedelta(days=cooldown_days):
			return
	ins_id = f"ins_{uuid4().hex[:8]}"
	cursor.execute(
		"""INSERT OR REPLACE INTO supplier_insights_feed(id, supplier_id, severity, message, timestamp)
		VALUES(?,?,?,?, datetime('now'))""",
		(ins_id, supplier_id, severity, message),
	)


def get_minimal_supplier_metrics(supplier_id: str, days: int = 30) -> Dict[str, any]:
	"""Get minimal supplier metrics for MVP"""
	conn = get_conn()
	cursor = conn.cursor()
	cutoff_date = f"-{days} day"
	
	# Mismatch rate (PRICE_INCOHERENT + PACK_MISMATCH per lines)
	mismatch_rate = _calculate_mismatch_rate(cursor, supplier_id, cutoff_date)
	
	# Discount hit-rate (lines where solver accepted)
	discount_hit_rate = _calculate_discount_hit_rate(cursor, supplier_id, cutoff_date)
	
	# Top-3 flagged SKUs
	top_flagged_skus = _get_top_flagged_skus(cursor, supplier_id, cutoff_date)
	
	conn.close()
	
	return {
		'supplier_id': supplier_id,
		'period_days': days,
		'mismatch_rate_pct': mismatch_rate,
		'discount_hit_rate_pct': discount_hit_rate,
		'top_flagged_skus': top_flagged_skus,
		'calculated_at': datetime.now().isoformat()
	}

def _calculate_mismatch_rate(cursor: sqlite3.Cursor, supplier_id: str, cutoff_expr: str) -> float:
	"""Calculate percentage of lines with math mismatches"""
	# Total lines for supplier in period
	cursor.execute("""
		SELECT COUNT(*) FROM invoice_items ii
		JOIN invoices i ON ii.invoice_id = i.id
		WHERE i.supplier_name = ? AND i.invoice_date >= DATE('now', ?)
	""", (supplier_id, cutoff_expr))
	total_lines = cursor.fetchone()[0] or 0
	
	if total_lines == 0:
		return 0.0
	
	# Lines with math issues
	cursor.execute("""
		SELECT COUNT(*) FROM invoice_items ii
		JOIN invoices i ON ii.invoice_id = i.id
		WHERE i.supplier_name = ? AND i.invoice_date >= DATE('now', ?)
		AND (ii.line_verdict IN ('PRICE_INCOHERENT', 'PACK_MISMATCH', 'VAT_MISMATCH'))
	""", (supplier_id, cutoff_expr))
	mismatch_lines = cursor.fetchone()[0] or 0
	
	return (mismatch_lines / total_lines) * 100.0

def _calculate_discount_hit_rate(cursor: sqlite3.Cursor, supplier_id: str, cutoff_expr: str) -> float:
	"""Calculate percentage of lines where discount solver found a solution"""
	# Total lines
	cursor.execute("""
		SELECT COUNT(*) FROM invoice_items ii
		JOIN invoices i ON ii.invoice_id = i.id
		WHERE i.supplier_name = ? AND i.invoice_date >= DATE('now', ?)
	""", (supplier_id, cutoff_expr))
	total_lines = cursor.fetchone()[0] or 0
	
	if total_lines == 0:
		return 0.0
	
	# Lines with discount solutions (residual ≤ 1p)
	cursor.execute("""
		SELECT COUNT(*) FROM invoice_items ii
		JOIN invoices i ON ii.invoice_id = i.id
		WHERE i.supplier_name = ? AND i.invoice_date >= DATE('now', ?)
		AND ii.discount_residual_pennies IS NOT NULL 
		AND ii.discount_residual_pennies <= 1
	""", (supplier_id, cutoff_expr))
	discount_lines = cursor.fetchone()[0] or 0
	
	return (discount_lines / total_lines) * 100.0

def _get_top_flagged_skus(cursor: sqlite3.Cursor, supplier_id: str, cutoff_expr: str) -> List[Dict[str, any]]:
	"""Get top 3 SKUs with most flags in period"""
	cursor.execute("""
		SELECT 
			ii.sku,
			ii.description,
			COUNT(*) as flag_count,
			GROUP_CONCAT(DISTINCT ii.line_verdict) as verdicts
		FROM invoice_items ii
		JOIN invoices i ON ii.invoice_id = i.id
		WHERE i.supplier_name = ? AND i.invoice_date >= DATE('now', ?)
		AND ii.line_verdict NOT IN ('OK_ON_CONTRACT')
		GROUP BY ii.sku, ii.description
		ORDER BY flag_count DESC
		LIMIT 3
	""", (supplier_id, cutoff_expr))
	
	results = []
	for row in cursor.fetchall():
		results.append({
			'sku': row[0],
			'description': row[1],
			'flag_count': row[2],
			'verdicts': row[3].split(',') if row[3] else []
		})
	
	return results

def generate_insights_rules(supplier_id: str) -> None:
	conn = get_conn()
	cursor = conn.cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS supplier_insights_feed (id TEXT PRIMARY KEY, supplier_id TEXT NOT NULL, severity TEXT NOT NULL, message TEXT NOT NULL, timestamp TEXT DEFAULT (datetime('now'))) ")
	# Example rules (partial per spec)
	rel = _get_reliability_pct(cursor, supplier_id, 30)
	if rel is not None and rel < 0.80:
		_emit_insight(cursor, supplier_id, "warn", "Delivery reliability below 80% over the last 30 days.", f"{supplier_id}|rel_low_80", 7)
	# OCR quality low
	conf = _get_avg_ocr_conf(cursor, supplier_id, 90)
	if conf is not None and conf < 0.70:
		_emit_insight(cursor, supplier_id, "info", "Low document quality affecting OCR confidence.", f"{supplier_id}|ocr_low_conf", 14)
	conn.commit()
	conn.close() 