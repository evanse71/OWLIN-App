#!/usr/bin/env python3
"""
Check audit logs
"""
import sqlite3

con = sqlite3.connect('data/owlin.db')
con.row_factory = sqlite3.Row
rows = con.execute('SELECT id, action, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 5').fetchall()
print('Recent audit logs:')
for row in rows:
    print(f'  - {row["id"]}: {row["action"]} at {row["timestamp"]}')
con.close()
