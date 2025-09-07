import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

@pytest.fixture
def mock_update_manager():
    with patch('backend.routes.updates.svc') as mock:
        yield mock

@pytest.fixture
def app_client():
    from backend.main_fixed import app
    return TestClient(app)

def test_get_progress_success(app_client, mock_update_manager):
    """Test successful progress retrieval."""
    job_id = "f7e7b4bf-9d77-4e10-8a9a-b55ed2a56b2a"
    
    mock_ticks = [
        {
            "job_id": job_id,
            "kind": "apply",
            "step": "preflight",
            "percent": 10,
            "message": "Disk & license OK",
            "occurred_at": "2025-08-14T10:00:00Z"
        },
        {
            "job_id": job_id,
            "kind": "apply",
            "step": "snapshot",
            "percent": 30,
            "message": "Snapshot saved: backups/rollback_...zip",
            "occurred_at": "2025-08-14T10:00:02Z"
        },
        {
            "job_id": job_id,
            "kind": "apply",
            "step": "apply",
            "percent": 70,
            "message": "Copy files + alembic head",
            "occurred_at": "2025-08-14T10:00:07Z"
        },
        {
            "job_id": job_id,
            "kind": "apply",
            "step": "finalise",
            "percent": 90,
            "message": "Vacuum & changelog",
            "occurred_at": "2025-08-14T10:00:10Z"
        },
        {
            "job_id": job_id,
            "kind": "apply",
            "step": "done",
            "percent": 100,
            "message": "Done",
            "occurred_at": "2025-08-14T10:00:12Z"
        }
    ]
    
    mock_update_manager.get_progress.return_value = mock_ticks
    
    response = app_client.get(f"/api/updates/progress/{job_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    
    # Check order
    steps = [tick["step"] for tick in data]
    assert steps == ["preflight", "snapshot", "apply", "finalise", "done"]
    
    # Check first tick
    first_tick = data[0]
    assert first_tick["job_id"] == job_id
    assert first_tick["kind"] == "apply"
    assert first_tick["step"] == "preflight"
    assert first_tick["percent"] == 10
    assert "Disk & license OK" in first_tick["message"]

def test_get_progress_error(app_client, mock_update_manager):
    """Test progress retrieval with error step."""
    job_id = "f7e7b4bf-9d77-4e10-8a9a-b55ed2a56b2a"
    
    mock_ticks = [
        {
            "job_id": job_id,
            "kind": "apply",
            "step": "preflight",
            "percent": 10,
            "message": "Disk & license OK",
            "occurred_at": "2025-08-14T10:00:00Z"
        },
        {
            "job_id": job_id,
            "kind": "apply",
            "step": "error",
            "percent": 100,
            "message": "Update failed: Insufficient disk space",
            "occurred_at": "2025-08-14T10:00:05Z"
        }
    ]
    
    mock_update_manager.get_progress.return_value = mock_ticks
    
    response = app_client.get(f"/api/updates/progress/{job_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    
    # Check error tick
    error_tick = data[1]
    assert error_tick["step"] == "error"
    assert error_tick["percent"] == 100
    assert "Update failed" in error_tick["message"]

def test_get_progress_empty(app_client, mock_update_manager):
    """Test progress retrieval with no ticks."""
    job_id = "f7e7b4bf-9d77-4e10-8a9a-b55ed2a56b2a"
    
    mock_update_manager.get_progress.return_value = []
    
    response = app_client.get(f"/api/updates/progress/{job_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

def test_get_progress_rollback(app_client, mock_update_manager):
    """Test progress retrieval for rollback operation."""
    job_id = "f7e7b4bf-9d77-4e10-8a9a-b55ed2a56b2a"
    
    mock_ticks = [
        {
            "job_id": job_id,
            "kind": "rollback",
            "step": "preflight",
            "percent": 10,
            "message": "Checking rollback point",
            "occurred_at": "2025-08-14T10:00:00Z"
        },
        {
            "job_id": job_id,
            "kind": "rollback",
            "step": "apply",
            "percent": 50,
            "message": "Restoring from backup",
            "occurred_at": "2025-08-14T10:00:02Z"
        },
        {
            "job_id": job_id,
            "kind": "rollback",
            "step": "done",
            "percent": 100,
            "message": "Rollback completed",
            "occurred_at": "2025-08-14T10:00:05Z"
        }
    ]
    
    mock_update_manager.get_progress.return_value = mock_ticks
    
    response = app_client.get(f"/api/updates/progress/{job_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    
    # Check rollback kind
    for tick in data:
        assert tick["kind"] == "rollback"
    
    # Check steps
    steps = [tick["step"] for tick in data]
    assert steps == ["preflight", "apply", "done"]
