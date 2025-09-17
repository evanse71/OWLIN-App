import sqlite3

con = sqlite3.connect("data/owlin.db")
con.row_factory = sqlite3.Row

for t in ("delivery_notes", "audit_logs", "invoices"):
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
    print(t, "->", cols)

con.close()
