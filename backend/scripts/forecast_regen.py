from __future__ import annotations
from backend.services.forecasting import ensure_tables, forecast_item_prices
from backend.services.forecasting import _get_conn
from uuid import uuid4
import json
import sys


def main():
	ensure_tables()
	conn = _get_conn(); cur = conn.cursor()
	cur.execute("SELECT DISTINCT item_id FROM item_price_history")
	items = [r[0] for r in cur.fetchall()]
	for iid in items:
		try:
			f = forecast_item_prices(str(iid), horizon=3)
			key = f"item:{iid}:h=3"
			cur.execute("INSERT OR REPLACE INTO forecast_cache(id, key, payload, created_at) VALUES (?,?,?,datetime('now'))", (str(uuid4()), key, json.dumps(f.dict(), default=str)))
		except Exception:
			continue
	conn.commit(); conn.close()
	print(f"Regenerated {len(items)} item forecasts")


if __name__ == "__main__":
	main() 