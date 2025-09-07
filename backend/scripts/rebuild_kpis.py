#!/usr/bin/env python3
"""
Offline CLI to rebuild KPI aggregates.
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.aggregator import ensure_aggregator_tables, refresh_venue_kpis, get_user_venue_ids


def main():
	"""Main CLI function."""
	import argparse
	
	parser = argparse.ArgumentParser(description="Rebuild KPI aggregates")
	parser.add_argument("--force", action="store_true", help="Force refresh all data")
	parser.add_argument("--venue-id", help="Refresh specific venue only")
	parser.add_argument("--user-id", help="Refresh venues accessible to specific user")
	parser.add_argument("--user-role", default="gm", choices=["gm", "finance", "shiftlead"], 
					   help="User role for venue filtering")
	parser.add_argument("--days", type=int, default=30, help="Number of days to refresh")
	
	args = parser.parse_args()
	
	print("🔧 Rebuilding KPI aggregates...")
	
	# Ensure tables exist
	ensure_aggregator_tables()
	print("✅ Database tables ready")
	
	# Determine venues to refresh
	venue_ids = None
	
	if args.venue_id:
		venue_ids = [args.venue_id]
		print(f"🎯 Refreshing specific venue: {args.venue_id}")
	elif args.user_id:
		venue_ids = get_user_venue_ids(args.user_id, args.user_role)
		print(f"👤 Refreshing venues for user {args.user_id} (role: {args.user_role})")
		print(f"   Found {len(venue_ids)} accessible venues")
	else:
		print("🌍 Refreshing all venues")
	
	# Refresh KPIs
	try:
		refresh_venue_kpis(venue_ids, args.force)
		print("✅ KPI refresh completed successfully")
		
		# Show summary
		if venue_ids:
			print(f"📊 Refreshed {len(venue_ids)} venues")
		else:
			# Count total venues
			from sqlite3 import connect
			import os
			db_path = os.path.join("data", "owlin.db")
			conn = connect(db_path)
			cur = conn.cursor()
			cur.execute("SELECT COUNT(*) FROM venues")
			total_venues = cur.fetchone()[0]
			conn.close()
			print(f"📊 Refreshed {total_venues} venues")
		
	except Exception as e:
		print(f"❌ Error refreshing KPIs: {e}")
		sys.exit(1)


if __name__ == "__main__":
	main() 