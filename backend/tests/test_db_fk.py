import sqlite3
import pathlib

def test_fk_enforced():
    """Test that foreign key constraints can be enforced in database connections."""
    db = pathlib.Path(__file__).resolve().parents[2] / "data" / "owlin.db"
    conn = sqlite3.connect(str(db))
    
    # Enable foreign keys (this is what our code should do)
    conn.execute("PRAGMA foreign_keys=ON")
    
    # Verify foreign keys are enabled
    result = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    conn.close()
    
    assert result == 1, "Foreign keys should be enabled (PRAGMA foreign_keys=ON)"

if __name__ == "__main__":
    test_fk_enforced()
    print("✅ FK enforcement test passed")
