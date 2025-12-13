#!/usr/bin/env python3
"""
Offline CSV/ZIP exporter for supplier data.
"""
import csv
import zipfile
import io
import json
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.suppliers.timeline_builder import build_summary, build_timeline


def run(supplier_id: str, venue_id: str | None, start: str, end: str, out_zip: str):
	"""Export supplier data to ZIP file."""
	from datetime import datetime as DT
	
	start_dt = DT.fromisoformat(start)
	end_dt = DT.fromisoformat(end)
	
	# Build summary and timeline
	summary = build_summary(supplier_id, venue_id)
	events = build_timeline(supplier_id, venue_id, start_dt, end_dt)
	
	# Create CSV buffer
	buf = io.StringIO()
	writer = csv.writer(buf)
	writer.writerow(["ts", "type", "title", "summary", "severity"])
	
	for ev in events:
		writer.writerow([
			ev.ts.isoformat(),
			ev.type,
			ev.title,
			ev.summary or "",
			ev.severity or ""
		])
	
	# Create ZIP file
	with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
		# Add summary as JSON
		z.writestr("summary.json", json.dumps(summary.dict(), indent=2, default=str))
		
		# Add timeline as CSV
		z.writestr("timeline.csv", buf.getvalue())
		
		# Add metadata
		metadata = {
			"exported_at": datetime.utcnow().isoformat(),
			"supplier_id": supplier_id,
			"venue_id": venue_id,
			"start_date": start,
			"end_date": end,
			"event_count": len(events)
		}
		z.writestr("metadata.json", json.dumps(metadata, indent=2))
	
	print(f"✅ Exported supplier pack: {out_zip}")
	print(f"   Events: {len(events)}")
	print(f"   Period: {start} to {end}")


if __name__ == "__main__":
	if len(sys.argv) < 4:
		print("Usage: python export_supplier_pack.py <supplier_id> <start_date> <end_date> [venue_id] [output.zip]")
		print("Example: python export_supplier_pack.py 123e4567-e89b-12d3-a456-426614174000 2025-07-01T00:00:00 2025-07-31T23:59:59")
		sys.exit(1)
	
	supplier_id = sys.argv[1]
	start_date = sys.argv[2]
	end_date = sys.argv[3]
	venue_id = sys.argv[4] if len(sys.argv) > 4 else None
	output_file = sys.argv[5] if len(sys.argv) > 5 else "supplier_pack.zip"
	
	run(supplier_id, venue_id, start_date, end_date, output_file) 