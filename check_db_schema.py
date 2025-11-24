#!/usr/bin/env python3
"""Check database schema"""
import sqlite3

conn = sqlite3.connect('data/owlin.db')
cur = conn.cursor()

print("Documents table columns:")
cur.execute('PRAGMA table_info(documents)')
for row in cur.fetchall():
    print(f"  {row[1]}: {row[2]}")

conn.close()
