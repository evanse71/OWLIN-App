import json
import sqlite3
from pathlib import Path

DB_PATH = Path("data/owlin.db")

def audit_log(actor: str, action: str, entity: str, entity_id: str, details: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_log (
                 id INTEGER PRIMARY KEY,
                 ts TEXT NOT NULL DEFAULT (datetime('now')),
                 actor TEXT NOT NULL,
                 action TEXT NOT NULL,
                 entity TEXT NOT NULL,
                 entity_id TEXT NOT NULL,
                 details_json TEXT NOT NULL
               )"""
        )
        conn.execute(
            "INSERT INTO audit_log (actor, action, entity, entity_id, details_json) VALUES (?,?,?,?,?)",
            (actor, action, entity, entity_id, json.dumps(details, ensure_ascii=False)),
        )
        conn.commit()