import pytest
import tempfile
import zipfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
from backend.services import backup as backup_service

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Set the database path for the service
    original_db_path = backup_service.DB_PATH
    backup_service.DB_PATH = Path(db_path)
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    backup_service.DB_PATH = original_db_path

@pytest.fixture
def temp_backup_dir():
    """Create a temporary backup directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_backup_dir = backup_service.BACKUPS_DIR
        backup_service.BACKUPS_DIR = Path(temp_dir)
        
        yield temp_dir
        
        backup_service.BACKUPS_DIR = original_backup_dir

def test_backup_create_success(temp_db, temp_backup_dir):
    """Test successful backup creation."""
    # Create a simple database
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    cur.execute("INSERT INTO test_table (name) VALUES ('test')")
    conn.commit()
    conn.close()
    
    # Create backup
    result = backup_service.backup_create('manual')
    
    assert result["id"] is not None
    assert result["path"] is not None
    assert result["size_bytes"] > 0
    assert result["created_at"] is not None
    
    # Check backup file exists
    backup_path = Path(result["path"])
    assert backup_path.exists()
    
    # Check backup contains database
    with zipfile.ZipFile(backup_path, 'r') as z:
        assert 'data/owlin.db' in z.namelist()
        assert 'version.json' in z.namelist()
        assert 'system_report.txt' in z.namelist()

def test_backup_list_empty(temp_db):
    """Test listing backups when none exist."""
    backups = backup_service.backup_list()
    assert len(backups) == 0

def test_backup_list_with_backups(temp_db, temp_backup_dir):
    """Test listing backups when they exist."""
    # Create a backup first
    backup_service.backup_create('manual')
    
    # List backups
    backups = backup_service.backup_list()
    assert len(backups) == 1
    
    backup = backups[0]
    assert backup["id"] is not None
    assert backup["mode"] == "manual"
    assert backup["app_version"] is not None
    assert backup["db_schema_version"] is not None

def test_restore_preview_success(temp_db, temp_backup_dir):
    """Test successful restore preview."""
    # Create a backup
    backup_result = backup_service.backup_create('manual')
    
    # Modify the database
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE new_table (id INTEGER PRIMARY KEY)")
    cur.execute("INSERT INTO new_table (id) VALUES (1)")
    conn.commit()
    conn.close()
    
    # Preview restore
    preview = backup_service.restore_preview(backup_result["id"])
    
    assert preview["ok"] is True
    assert "changes" in preview
    assert len(preview["changes"]) > 0

def test_restore_preview_backup_not_found(temp_db):
    """Test restore preview with non-existent backup."""
    preview = backup_service.restore_preview("non-existent-id")
    
    assert preview["ok"] is False
    assert "Backup not found" in preview["reason"]

def test_restore_preview_corrupt_backup(temp_db, temp_backup_dir):
    """Test restore preview with corrupt backup."""
    # Create a backup
    backup_result = backup_service.backup_create('manual')
    
    # Corrupt the backup file
    backup_path = Path(backup_result["path"])
    with open(backup_path, 'wb') as f:
        f.write(b"corrupt data")
    
    # Preview restore
    preview = backup_service.restore_preview(backup_result["id"])
    
    assert preview["ok"] is False
    assert "corrupt" in preview["reason"].lower()

def test_restore_commit_success(temp_db, temp_backup_dir):
    """Test successful restore commit."""
    # Create initial database
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE original_table (id INTEGER PRIMARY KEY, name TEXT)")
    cur.execute("INSERT INTO original_table (name) VALUES ('original')")
    conn.commit()
    conn.close()
    
    # Create backup
    backup_result = backup_service.backup_create('manual')
    
    # Modify database
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("DROP TABLE original_table")
    cur.execute("CREATE TABLE modified_table (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    
    # Restore
    result = backup_service.restore_commit(backup_result["id"])
    
    assert result["ok"] is True
    assert "pre_restore_backup_id" in result
    
    # Check that original table is restored
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='original_table'")
    assert cur.fetchone() is not None
    conn.close()

def test_backup_create_insufficient_disk_space(temp_db, temp_backup_dir):
    """Test backup creation with insufficient disk space."""
    with patch('backend.services.backup._check_disk_space', return_value=False):
        with pytest.raises(Exception) as exc_info:
            backup_service.backup_create('manual')
        
        assert "Insufficient disk space" in str(exc_info.value)

def test_backup_create_different_modes(temp_db, temp_backup_dir):
    """Test backup creation with different modes."""
    manual_result = backup_service.backup_create('manual')
    scheduled_result = backup_service.backup_create('scheduled')
    
    assert manual_result["id"] != scheduled_result["id"]
    
    # Check both are recorded
    backups = backup_service.backup_list()
    modes = [b["mode"] for b in backups]
    assert "manual" in modes
    assert "scheduled" in modes
