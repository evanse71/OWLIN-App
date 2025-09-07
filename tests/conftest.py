# tests/conftest.py
import sys, os
import tempfile
import shutil
import pytest
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "..", "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

@pytest.fixture(scope="session")
def temp_db_path():
    d = tempfile.mkdtemp(prefix="owlin_db_")
    p = Path(d) / "owlin.db"
    os.environ["OWLIN_DB_PATH"] = str(p)  # single source of truth for app + tests
    yield p
    shutil.rmtree(d, ignore_errors=True)

@pytest.fixture(scope="session", autouse=True)
def migrate_temp_db(temp_db_path):
    import sys; sys.path.insert(0, "backend")
    from db_manager_unified import get_db_manager
    m = get_db_manager()
    m.run_migrations()  # idempotent
    # smoke PRAGMA
    conn = m.get_conn()
    cur = conn.execute("PRAGMA foreign_keys")
    assert cur.fetchone()[0] == 1
    return m

# Optional: force a temp DB for tests to avoid clobbering real data
os.environ.setdefault("OWLIN_DB_PATH", os.path.join(ROOT, "..", "data", "owlin.db")) 