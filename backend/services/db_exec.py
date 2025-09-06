from __future__ import annotations
import sqlite3
from typing import Any, Mapping, Sequence, Optional, List, Union

Params = Union[Sequence[Any], Mapping[str, Any]]

def ensure_row_factory(conn: sqlite3.Connection) -> None:
    if conn.row_factory is None:
        conn.row_factory = sqlite3.Row

def exec_one(conn: sqlite3.Connection, sql: str, params: Params = ()) -> int:
    ensure_row_factory(conn)
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    return cur.rowcount

def query_all(conn: sqlite3.Connection, sql: str, params: Params = ()) -> List[sqlite3.Row]:
    ensure_row_factory(conn)
    cur = conn.cursor()
    cur.execute(sql, params)
    return list(cur.fetchall())

def query_one(conn: sqlite3.Connection, sql: str, params: Params = ()) -> Optional[sqlite3.Row]:
    ensure_row_factory(conn)
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur.fetchone() 