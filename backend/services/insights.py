from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import List, Dict
from statistics import median
import math

from ..contracts import TimeSeriesPoint, MetricSeries, InsightBadge


def _bucketize(d: date, bucket: str) -> date:
	if bucket == "day":
		return d
	if bucket == "week":
		return d - timedelta(days=d.weekday())
	if bucket == "month":
		return date(d.year, d.month, 1)
	raise ValueError("bucket")


def _series_range(start: date, end: date, bucket: str) -> List[date]:
	out: List[date] = []
	cur = _bucketize(start, bucket)
	while cur <= end:
		out.append(cur)
		if bucket == "day":
			cur += timedelta(days=1)
		elif bucket == "week":
			cur += timedelta(days=7)
		else:
			y, m = cur.year, cur.month
			m2 = 1 if m == 12 else m + 1
			y2 = y + 1 if m == 12 else y
			cur = date(y2, m2, 1)
	return out


# The following helpers expect a DB API cursor (sqlite3). We keep them pure and deterministic.

def _sum_spend(cur, supplier_name: str, start: date, end: date, bucket: str) -> MetricSeries:
	cur.execute(
		"SELECT invoice_date, total_amount FROM invoices WHERE supplier_name = ? AND invoice_date >= ? AND invoice_date <= ?",
		(supplier_name, start.isoformat(), end.isoformat()),
	)
	rows = cur.fetchall()
	buckets: Dict[date, float] = {b: 0.0 for b in _series_range(start, end, bucket)}
	for (inv_date, total) in rows:
		try:
			d = datetime.fromisoformat(inv_date).date() if isinstance(inv_date, str) else inv_date
		except Exception:
			d = start
		b = _bucketize(d or start, bucket)
		buckets[b] += float(total or 0.0)
	pts = [TimeSeriesPoint(t=b, v=round(v, 2)) for b, v in sorted(buckets.items())]
	return MetricSeries(metric="spend", bucket=bucket, points=pts)


def _confidence_median(cur, supplier_name: str, start: date, end: date, bucket: str) -> MetricSeries:
	cur.execute(
		"SELECT invoice_date, confidence FROM invoices WHERE supplier_name = ? AND invoice_date >= ? AND invoice_date <= ?",
		(supplier_name, start.isoformat(), end.isoformat()),
	)
	rows = cur.fetchall()
	buckets: Dict[date, List[int]] = {b: [] for b in _series_range(start, end, bucket)}
	for (inv_date, conf) in rows:
		try:
			d = datetime.fromisoformat(inv_date).date() if isinstance(inv_date, str) else inv_date
		except Exception:
			d = start
		if conf is not None:
			buckets[_bucketize(d or start, bucket)].append(int(conf))
	pts = [TimeSeriesPoint(t=b, v=float(median(v)) if v else 0.0, n=len(v)) for b, v in sorted(buckets.items())]
	return MetricSeries(metric="confidence_median", bucket=bucket, points=pts)


def _mismatch_rate(cur, supplier_id: str, start: date, end: date, bucket: str) -> MetricSeries:
	cur.execute(
		"SELECT created_at FROM flagged_issues WHERE supplier_id = ? AND created_at >= ? AND created_at <= ? AND type IN ('PRICE_MISMATCH','MISSING_ITEM','EXTRA_ITEM')",
		(supplier_id, start.isoformat(), end.isoformat()),
	)
	issue_rows = cur.fetchall()
	cur.execute(
		"SELECT invoice_date FROM invoices WHERE supplier_name IN (SELECT supplier_name FROM invoices) AND invoice_date >= ? AND invoice_date <= ?",
		(start.isoformat(), end.isoformat()),
	)
	inv_rows = cur.fetchall()
	by_bucket_issues: Dict[date, int] = {b: 0 for b in _series_range(start, end, bucket)}
	by_bucket_invoices: Dict[date, int] = {b: 0 for b in _series_range(start, end, bucket)}
	for (ts,) in issue_rows:
		try:
			d = datetime.fromisoformat(ts).date() if isinstance(ts, str) else ts
		except Exception:
			d = start
		by_bucket_issues[_bucketize(d, bucket)] += 1
	for (ts,) in inv_rows:
		try:
			d = datetime.fromisoformat(ts).date() if isinstance(ts, str) else ts
		except Exception:
			d = start
		by_bucket_invoices[_bucketize(d, bucket)] += 1
	pts: List[TimeSeriesPoint] = []
	for b in sorted(by_bucket_invoices.keys()):
		den = by_bucket_invoices[b] or 1
		rate = by_bucket_issues[b] / den
		pts.append(TimeSeriesPoint(t=b, v=round(rate * 100.0, 2), n=den))
	return MetricSeries(metric="mismatch_rate", bucket=bucket, points=pts)


def _on_time_rate(cur, supplier_name: str, start: date, end: date, bucket: str) -> MetricSeries:
	cur.execute(
		"SELECT date, expected_date FROM delivery_notes WHERE supplier_name = ? AND date >= ? AND date <= ?",
		(supplier_name, start.isoformat(), end.isoformat()),
	)
	dn_rows = cur.fetchall()
	by_bucket_total: Dict[date, int] = {b: 0 for b in _series_range(start, end, bucket)}
	by_bucket_ok: Dict[date, int] = {b: 0 for b in _series_range(start, end, bucket)}
	for (dt, expected) in dn_rows:
		try:
			d = datetime.fromisoformat(dt).date() if isinstance(dt, str) else dt
		except Exception:
			d = start
		b = _bucketize(d or start, bucket)
		by_bucket_total[b] += 1
		exp = None
		try:
			exp = datetime.fromisoformat(expected).date() if isinstance(expected, str) else expected
		except Exception:
			exp = d
		if exp and d and (d - exp).days <= 0:
			by_bucket_ok[b] += 1
	pts: List[TimeSeriesPoint] = []
	for b in sorted(by_bucket_total.keys()):
		tot = by_bucket_total[b] or 1
		pts.append(TimeSeriesPoint(t=b, v=round(by_bucket_ok[b] / tot * 100.0, 2), n=tot))
	return MetricSeries(metric="on_time_rate", bucket=bucket, points=pts)


def _price_volatility(cur, supplier_name: str, start: date, end: date, bucket: str) -> MetricSeries:
	pts: List[TimeSeriesPoint] = []
	for b in _series_range(start, end, bucket):
		# compute bucket end
		if bucket == "day":
			b_end = b
		elif bucket == "week":
			b_end = b + timedelta(days=6)
		else:
			y, m = b.year, b.month
			m2 = 1 if m == 12 else m + 1
			y2 = y + 1 if m == 12 else y
			b_end = date(y2, m2, 1) - timedelta(days=1)
		cur.execute(
			"SELECT i.id, i.invoice_date FROM invoices i WHERE i.supplier_name = ? AND i.invoice_date >= ? AND i.invoice_date <= ?",
			(supplier_name, b.isoformat(), b_end.isoformat()),
		)
		inv_rows = cur.fetchall()
		# collect SKU/unit prices
		sku_prices: Dict[str, List[float]] = {}
		for (inv_id, inv_date) in inv_rows:
			cur.execute("SELECT sku, description, unit_price FROM invoice_line_items WHERE invoice_id = ?", (inv_id,))
			for sku, desc, up in cur.fetchall():
				name = sku or (desc or "").lower()
				if up is None:
					continue
				sku_prices.setdefault(name, []).append(float(up))
		cvs: List[float] = []
		for _, arr in sku_prices.items():
			arr = [x for x in arr if x > 0]
			if len(arr) >= 2:
				mean = sum(arr) / len(arr)
				var = sum((x - mean) ** 2 for x in arr) / (len(arr) - 1)
				sd = math.sqrt(var)
				cv = sd / mean if mean > 0 else 0.0
				cvs.append(cv)
		val = round(min(100.0, (sum(cvs) / len(cvs)) * 100.0 if cvs else 0.0), 2)
		pts.append(TimeSeriesPoint(t=b, v=val, n=len(cvs)))
	return MetricSeries(metric="price_volatility", bucket=bucket, points=pts)


def build_summary(cur, supplier_name: str, supplier_id: str, start: date, end: date, bucket: str = "month"):
	spend = _sum_spend(cur, supplier_name, start, end, bucket)
	conf = _confidence_median(cur, supplier_name, start, end, bucket)
	mismatch = _mismatch_rate(cur, supplier_id, start, end, bucket)
	ontime = _on_time_rate(cur, supplier_name, start, end, bucket)
	vol = _price_volatility(cur, supplier_name, start, end, bucket)
	last_spend = spend.points[-1].v if spend.points else 0.0
	last_ontime = ontime.points[-1].v if ontime.points else 0.0
	last_mismatch = mismatch.points[-1].v if mismatch.points else 0.0
	badges = [
		InsightBadge(label="Spend (latest)", value=f"£{last_spend:,.2f}", tone="neutral"),
		InsightBadge(label="On-time", value=f"{last_ontime:.0f}%", tone=("ok" if last_ontime >= 90 else "warn")),
		InsightBadge(label="Mismatch", value=f"{last_mismatch:.1f}%", tone=("warn" if last_mismatch >= 5 else "ok")),
	]
	return {"top_badges": badges, "series": [spend, vol, ontime, mismatch, conf]} 