from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import List, Tuple, Dict, Optional
from uuid import uuid4
import math
import sqlite3
import os

from ..contracts import PricePoint, ItemForecast, ForecastBand, AggregateForecast, BudgetGuardrail, BudgetViolation


DB_PATH = os.path.join("data", "owlin.db")


def _get_conn():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	return sqlite3.connect(DB_PATH)


def ensure_tables():
	conn = _get_conn(); cur = conn.cursor()
	cur.execute("""
	CREATE TABLE IF NOT EXISTS forecast_cache (
		id TEXT PRIMARY KEY,
		key TEXT NOT NULL,
		payload TEXT NOT NULL,
		created_at TIMESTAMP NOT NULL,
		UNIQUE(key)
	)""")
	cur.execute("CREATE INDEX IF NOT EXISTS idx_forecast_cache_key ON forecast_cache(key)")
	cur.execute("""
	CREATE TABLE IF NOT EXISTS budget_guardrails (
		id TEXT PRIMARY KEY,
		scope_type TEXT NOT NULL,
		scope_id TEXT NOT NULL,
		period_start DATE NOT NULL,
		period_end DATE NOT NULL,
		amount_pennies INTEGER NOT NULL,
		hard_limit INTEGER NOT NULL,
		created_by TEXT NOT NULL,
		created_at TIMESTAMP NOT NULL
	)""")
	cur.execute("CREATE INDEX IF NOT EXISTS idx_budget_scope ON budget_guardrails(scope_type, scope_id)")
	cur.execute("""
	CREATE TABLE IF NOT EXISTS budget_violations (
		id TEXT PRIMARY KEY,
		guardrail_id TEXT NOT NULL,
		occurred_at TIMESTAMP NOT NULL,
		projected_spend_pennies INTEGER NOT NULL,
		threshold_pennies INTEGER NOT NULL,
		severity INTEGER NOT NULL,
		created_at TIMESTAMP NOT NULL
	)""")
	cur.execute("CREATE INDEX IF NOT EXISTS idx_budget_violations_guardrail ON budget_violations(guardrail_id, occurred_at)")
	# minimal market data table for offline history
	cur.execute("""
	CREATE TABLE IF NOT EXISTS item_price_history (
		item_id TEXT NOT NULL,
		date DATE NOT NULL,
		unit_price REAL NOT NULL
	)""")
	cur.execute("CREATE INDEX IF NOT EXISTS idx_item_price_hist_item_date ON item_price_history(item_id, date)")
	conn.commit(); conn.close()


def _parse_points(rows: List[Tuple[str, float]]) -> List[PricePoint]:
	out: List[PricePoint] = []
	for d, v in rows:
		dt = datetime.fromisoformat(d).date() if isinstance(d, str) else d
		out.append(PricePoint(t=dt, p=float(v or 0.0)))
	return out


def _ses_forecast(history: List[float], horizon: int) -> Tuple[List[float], float, float, Optional[float]]:
	best_alpha = None; best_mse = float('inf'); best_level = 0.0
	# grid search alpha 0.1..0.9
	for a in [x / 10.0 for x in range(1, 10)]:
		level = history[0] if history else 0.0
		reqs = []
		for v in history[1:]:
			level = a * v + (1 - a) * level
			reqs.append(level)
		mse = sum((history[i+1]-reqs[i])**2 for i in range(len(reqs))) / max(1, len(reqs))
		if mse < best_mse:
			best_mse = mse; best_alpha = a; best_level = level
	# forecast is flat level for SES
	fcast = [best_level for _ in range(horizon)] if history else [0.0 for _ in range(horizon)]
	residuals = []
	if history and best_alpha is not None:
		level = history[0]
		for v in history[1:]:
			prev = level
			level = best_alpha * v + (1 - best_alpha) * level
			residuals.append(v - prev)
	std = math.sqrt(sum(r*r for r in residuals) / max(1, len(residuals))) if residuals else 0.0
	return fcast, best_mse, std, best_alpha


def _ma_forecast(history: List[float], horizon: int, window: int = 3) -> Tuple[List[float], float, float]:
	vals = history[-window:] if history else []
	avg = (sum(vals) / len(vals)) if vals else 0.0
	fcast = [avg for _ in range(horizon)]
	res = [history[i] - (sum(history[max(0, i-window+1):i+1]) / len(history[max(0, i-window+1):i+1])) for i in range(len(history))] if history else []
	std = math.sqrt(sum(r*r for r in res) / max(1, len(res))) if res else 0.0
	mse = sum(r*r for r in res) / max(1, len(res)) if res else 0.0
	return fcast, mse, std


def _band(center: List[float], std: float, z: float = 1.28) -> ForecastBand:
	# ~80% band → z ~ 1.28
	lower = min(center) - z * std if center else 0.0
	upper = max(center) + z * std if center else 0.0
	return ForecastBand(lower=round(lower, 2), upper=round(upper, 2), confidence=80)


def forecast_item_prices(item_id: str, horizon: int = 3) -> ItemForecast:
	ensure_tables()
	conn = _get_conn(); cur = conn.cursor()
	cur.execute("SELECT date, unit_price FROM item_price_history WHERE item_id = ? ORDER BY date ASC", (item_id,))
	hist_rows = cur.fetchall()
	points = _parse_points(hist_rows)
	history = [pt.p for pt in points]
	if len(history) >= 4:
		f_ses, mse_ses, std_ses, alpha = _ses_forecast(history, horizon)
		model = "SES"; center = f_ses; std = std_ses
	else:
		f_ma, mse_ma, std_ma = _ma_forecast(history, horizon)
		model = "MA"; center = f_ma; std = std_ma; alpha = None
	# future dates monthly cadence
	start_dt = points[-1].t if points else date.today()
	future: List[PricePoint] = []
	y, m = start_dt.year, start_dt.month
	for i in range(1, horizon + 1):
		m2 = m + i
		y2 = y + (m2 - 1) // 12
		m3 = ((m2 - 1) % 12) + 1
		future_date = date(y2, m3, 1)
		future.append(PricePoint(t=future_date, p=round(center[i - 1], 2)))
	band = _band(center, std)
	conn.close()
	return ItemForecast(item_id=item_id, horizon=horizon, model=model, alpha=alpha, points=points, forecast=future, band=band)


def forecast_aggregate(scope_type: str, scope_id: str, horizon: int = 3) -> AggregateForecast:
	# aggregate by spend-weighted item forecasts for scope
	ensure_tables()
	conn = _get_conn(); cur = conn.cursor()
	if scope_type == "supplier":
		cur.execute("SELECT DISTINCT item_id FROM invoice_line_items WHERE supplier_id = ?", (scope_id,))
	elif scope_type == "category":
		cur.execute("SELECT DISTINCT item_id FROM items WHERE category_id = ?", (scope_id,))
	elif scope_type == "site":
		cur.execute("SELECT DISTINCT item_id FROM invoices WHERE site_id = ?", (scope_id,))
	else:
		raise ValueError("scope_type")
	rows = cur.fetchall()
	item_ids = [r[0] for r in rows]
	weighted: List[Tuple[List[PricePoint], float]] = []
	for iid in item_ids:
		cur.execute("SELECT SUM(quantity*unit_price) FROM invoice_line_items WHERE item_id = ?", (iid,))
		w = float(cur.fetchone()[0] or 0.0)
		try:
			it = forecast_item_prices(str(iid), horizon)
			weighted.append((it.forecast, w))
		except Exception:
			continue
	if not weighted:
		return AggregateForecast(scope_type=scope_type, scope_id=scope_id, horizon=horizon, model="MA", forecast=[], band=_band([], 0.0))
	tot_w = sum(w for _, w in weighted) or 1.0
	combined: List[PricePoint] = []
	for i in range(horizon):
		val = sum((series[i].p * w) for series, w in weighted if len(series) > i) / tot_w
		combined.append(PricePoint(t=weighted[0][0][i].t, p=round(val, 2)))
	std = 0.0  # conservative default for aggregate
	return AggregateForecast(scope_type=scope_type, scope_id=scope_id, horizon=horizon, model="SES", forecast=combined, band=_band([pp.p for pp in combined], std))


def create_guardrail(scope_type: str, scope_id: str, period_start: date, period_end: date, amount_pennies: int, hard_limit: bool, created_by: str) -> BudgetGuardrail:
	ensure_tables()
	conn = _get_conn(); cur = conn.cursor()
	gid = str(uuid4())
	cur.execute(
		"INSERT INTO budget_guardrails(id, scope_type, scope_id, period_start, period_end, amount_pennies, hard_limit, created_by, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
		(gid, scope_type, scope_id, period_start.isoformat(), period_end.isoformat(), amount_pennies, 1 if hard_limit else 0, created_by, datetime.utcnow().isoformat()),
	)
	conn.commit(); conn.close()
	return BudgetGuardrail(id=gid, scope_type=scope_type, scope_id=scope_id, period_start=period_start, period_end=period_end, amount_pennies=amount_pennies, hard_limit=hard_limit, created_by=created_by, created_at=datetime.utcnow())


def list_guardrails(scope_type: Optional[str] = None, scope_id: Optional[str] = None) -> List[BudgetGuardrail]:
	ensure_tables()
	conn = _get_conn(); cur = conn.cursor()
	q = "SELECT id, scope_type, scope_id, period_start, period_end, amount_pennies, hard_limit, created_by, created_at FROM budget_guardrails"
	params: List[str] = []
	clauses = []
	if scope_type:
		clauses.append("scope_type = ?"); params.append(scope_type)
	if scope_id:
		clauses.append("scope_id = ?"); params.append(scope_id)
	if clauses:
		q += " WHERE " + " AND ".join(clauses)
	cur.execute(q, tuple(params))
	out: List[BudgetGuardrail] = []
	for row in cur.fetchall():
		out.append(BudgetGuardrail(
			id=row[0], scope_type=row[1], scope_id=row[2], period_start=datetime.fromisoformat(row[3]).date(), period_end=datetime.fromisoformat(row[4]).date(), amount_pennies=int(row[5]), hard_limit=bool(row[6]), created_by=row[7], created_at=datetime.fromisoformat(row[8])
		))
	conn.close()
	return out


def evaluate_guardrails(now: Optional[date] = None) -> List[BudgetViolation]:
	ensure_tables()
	now = now or date.today()
	conn = _get_conn(); cur = conn.cursor()
	cur.execute("SELECT id, scope_type, scope_id, period_start, period_end, amount_pennies FROM budget_guardrails")
	violations: List[BudgetViolation] = []
	for gid, st, sid, ps, pe, amt in cur.fetchall():
		ps_d = datetime.fromisoformat(ps).date(); pe_d = datetime.fromisoformat(pe).date()
		if not (ps_d <= now <= pe_d):
			continue
		# compute projected spend in period based on invoices
		if st == "supplier":
			cur.execute("SELECT SUM(total_amount) FROM invoices WHERE supplier_id = ? AND invoice_date >= ? AND invoice_date <= ?", (sid, ps_d.isoformat(), pe_d.isoformat()))
		else:
			cur.execute("SELECT SUM(total_amount) FROM invoices WHERE invoice_date >= ? AND invoice_date <= ?", (ps_d.isoformat(), pe_d.isoformat()))
		proj = int(cur.fetchone()[0] or 0)
		severity = 3 if proj >= amt * 1.2 else (2 if proj >= amt * 1.05 else (1 if proj >= amt else 0))
		if severity:
			vid = str(uuid4())
			cur.execute("INSERT OR IGNORE INTO budget_violations(id, guardrail_id, occurred_at, projected_spend_pennies, threshold_pennies, severity, created_at) VALUES (?,?,?,?,?,?,?)", (vid, gid, datetime.utcnow().isoformat(), proj, int(amt), int(severity), datetime.utcnow().isoformat()))
			violations.append(BudgetViolation(id=vid, guardrail_id=gid, occurred_at=datetime.utcnow(), projected_spend_pennies=proj, threshold_pennies=int(amt), severity=int(severity)))
	conn.commit(); conn.close()
	return violations 