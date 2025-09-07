import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
from backend.services import update_manager as svc

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Set the database path for the service
    original_db_path = svc.DB_PATH
    svc.DB_PATH = db_path
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    svc.DB_PATH = original_db_path

def test_emit_progress(temp_db):
    """Test emitting progress ticks."""
    job_id = "test-job-123"
    bundle_id = "test-bundle-456"
    
    # Emit a progress tick
    svc.emit_progress(job_id, "apply", bundle_id, "preflight", 10, "Test message")
    
    # Check it was stored
    ticks = svc.get_progress(job_id)
    assert len(ticks) == 1
    
    tick = ticks[0]
    assert tick["job_id"] == job_id
    assert tick["kind"] == "apply"
    assert tick["bundle_id"] == bundle_id
    assert tick["step"] == "preflight"
    assert tick["percent"] == 10
    assert tick["message"] == "Test message"

def test_get_progress_ordered(temp_db):
    """Test that progress ticks are returned in chronological order."""
    job_id = "test-job-123"
    bundle_id = "test-bundle-456"
    
    # Emit multiple ticks
    svc.emit_progress(job_id, "apply", bundle_id, "preflight", 10, "Step 1")
    svc.emit_progress(job_id, "apply", bundle_id, "snapshot", 30, "Step 2")
    svc.emit_progress(job_id, "apply", bundle_id, "apply", 70, "Step 3")
    svc.emit_progress(job_id, "apply", bundle_id, "done", 100, "Step 4")
    
    # Get progress
    ticks = svc.get_progress(job_id)
    assert len(ticks) == 4
    
    # Check order
    steps = [tick["step"] for tick in ticks]
    assert steps == ["preflight", "snapshot", "apply", "done"]
    
    # Check percentages
    percents = [tick["percent"] for tick in ticks]
    assert percents == [10, 30, 70, 100]

def test_get_progress_empty(temp_db):
    """Test getting progress for non-existent job."""
    ticks = svc.get_progress("non-existent-job")
    assert len(ticks) == 0

def test_progress_journal_persistence(temp_db):
    """Test that progress journal survives service restarts."""
    job_id = "test-job-123"
    bundle_id = "test-bundle-456"
    
    # Emit a tick
    svc.emit_progress(job_id, "apply", bundle_id, "preflight", 10, "Test message")
    
    # Simulate service restart by creating new connection
    ticks = svc.get_progress(job_id)
    assert len(ticks) == 1
    assert ticks[0]["message"] == "Test message"

def test_multiple_jobs(temp_db):
    """Test that different jobs have separate progress."""
    job1 = "job-1"
    job2 = "job-2"
    bundle_id = "test-bundle"
    
    # Emit ticks for different jobs
    svc.emit_progress(job1, "apply", bundle_id, "preflight", 10, "Job 1")
    svc.emit_progress(job2, "rollback", bundle_id, "preflight", 20, "Job 2")
    svc.emit_progress(job1, "apply", bundle_id, "done", 100, "Job 1 done")
    
    # Check job 1
    ticks1 = svc.get_progress(job1)
    assert len(ticks1) == 2
    assert all(tick["job_id"] == job1 for tick in ticks1)
    
    # Check job 2
    ticks2 = svc.get_progress(job2)
    assert len(ticks2) == 1
    assert all(tick["job_id"] == job2 for tick in ticks2)

def test_progress_validation(temp_db):
    """Test that progress percent is validated."""
    job_id = "test-job-123"
    bundle_id = "test-bundle-456"
    
    # Test valid percent
    svc.emit_progress(job_id, "apply", bundle_id, "preflight", 50, "Valid")
    ticks = svc.get_progress(job_id)
    assert len(ticks) == 1
    assert ticks[0]["percent"] == 50
    
    # Test edge cases (0 and 100 should be valid)
    svc.emit_progress(job_id, "apply", bundle_id, "start", 0, "Start")
    svc.emit_progress(job_id, "apply", bundle_id, "complete", 100, "Complete")
    
    ticks = svc.get_progress(job_id)
    assert len(ticks) == 3
    percents = [tick["percent"] for tick in ticks]
    assert 0 in percents
    assert 100 in percents
