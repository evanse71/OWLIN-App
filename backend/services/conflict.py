from __future__ import annotations
import sqlite3
from typing import List, Dict, Any


def _table_pks(conn: sqlite3.Connection) -> Dict[str, str]:
	"""Infer PK column per table for known tables."""
	pks = {}
	cur = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
	for name, sql in cur.fetchall():
		if sql:
			# Simple parse for PRIMARY KEY
			tokens = sql.upper().split("PRIMARY KEY")
			if len(tokens) > 1 and "(" in tokens[1]:
				pk_part = tokens[1].split("(")[1].split(")")[0].split(",")[0].strip()
				pks[name] = pk_part.lower()
			elif "INTEGER PRIMARY KEY" in sql.upper():
				# SQLite auto-increment PK
				pks[name] = "rowid"
	return pks


def generate_diff_report(current_db: str, candidate_db: str) -> Dict[str, Any]:
	"""Generate diff report between current and candidate databases."""
	cur = sqlite3.connect(current_db)
	can = sqlite3.connect(candidate_db)
	
	pks_cur = _table_pks(cur)
	pks_can = _table_pks(can)
	
	# Find common tables
	tables = sorted(set(pks_cur.keys()) & set(pks_can.keys()))
	
	rows = []
	field_count = 0
	
	for table in tables:
		pk = pks_cur[table]
		
		# Get column info
		cols_cur = [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]
		cols_can = [r[1] for r in can.execute(f"PRAGMA table_info({table})")]
		
		# Common columns, excluding volatile ones
		cols = [c for c in cols_cur if c in cols_can and c not in ["updated_at", "created_at"]]
		
		# Get data from both databases
		map_cur = {}
		map_can = {}
		
		try:
			cur.execute(f"SELECT {pk}, {', '.join(cols)} FROM {table}")
			for row in cur.fetchall():
				pk_val = str(row[0])
				map_cur[pk_val] = dict(zip(cols, row[1:]))
		except Exception:
			continue
		
		try:
			can.execute(f"SELECT {pk}, {', '.join(cols)} FROM {table}")
			for row in can.fetchall():
				pk_val = str(row[0])
				map_can[pk_val] = dict(zip(cols, row[1:]))
		except Exception:
			continue
		
		# Find all keys
		keys = sorted(set(map_cur.keys()) | set(map_can.keys()))
		
		for key in keys:
			row_cur = map_cur.get(key)
			row_can = map_can.get(key)
			
			if row_cur == row_can:
				continue
			
			diffs = []
			for col in cols:
				val_cur = row_cur.get(col) if row_cur else None
				val_can = row_can.get(col) if row_can else None
				
				if val_cur != val_can:
					diffs.append({
						"column": col,
						"old": str(val_cur) if val_cur is not None else None,
						"new": str(val_can) if val_can is not None else None,
						"decision": "use_new"
					})
			
			if diffs:
				rows.append({
					"table": table,
					"pk": key,
					"diffs": diffs
				})
				field_count += len(diffs)
	
	cur.close()
	can.close()
	
	return {
		"rows": rows,
		"summary": {
			"rows": len(rows),
			"fields": field_count
		}
	}


def apply_decisions_to_db(current_db: str, candidate_db: str, decisions: List[Dict]) -> None:
	"""Apply conflict resolution decisions to current database."""
	cur = sqlite3.connect(current_db)
	can = sqlite3.connect(candidate_db)
	
	cur.execute("BEGIN")
	
	try:
		for row_decision in decisions:
			table = row_decision["table"]
			pk = row_decision["pk"]
			diffs = row_decision["diffs"]
			
			# Get candidate row
			pks = _table_pks(can)
			pk_col = pks.get(table, "rowid")
			
			try:
				can.execute(f"SELECT * FROM {table} WHERE {pk_col} = ?", (pk,))
				candidate_row = can.fetchone()
				
				if candidate_row:
					# Get column names
					can.execute(f"PRAGMA table_info({table})")
					col_info = can.fetchall()
					col_names = [col[1] for col in col_info]
					
					# Build update/insert based on decisions
					update_cols = []
					update_vals = []
					
					for diff in diffs:
						if diff.get("decision") == "use_new":
							col = diff["column"]
							if col in col_names:
								col_idx = col_names.index(col)
								update_cols.append(col)
								update_vals.append(candidate_row[col_idx])
					
					if update_cols:
						# Check if row exists in current DB
						cur.execute(f"SELECT 1 FROM {table} WHERE {pk_col} = ?", (pk,))
						exists = cur.fetchone()
						
						if exists:
							# Update existing row
							set_clause = ", ".join([f"{col} = ?" for col in update_cols])
							cur.execute(f"UPDATE {table} SET {set_clause} WHERE {pk_col} = ?", 
									   update_vals + [pk])
						else:
							# Insert new row
							cur.execute(f"INSERT INTO {table} ({', '.join(col_names)}) VALUES ({', '.join(['?'] * len(col_names))})", 
									   candidate_row)
			except Exception:
				continue  # Skip problematic rows
		
		cur.execute("COMMIT")
	except Exception:
		cur.execute("ROLLBACK")
		raise
	finally:
		cur.close()
		can.close() 