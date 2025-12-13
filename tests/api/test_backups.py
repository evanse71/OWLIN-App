import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

@pytest.fixture
def mock_backup_service():
    with patch('backend.routes.backups.backup_service') as mock:
        yield mock

@pytest.fixture
def app_client():
    from backend.main_fixed import app
    return TestClient(app)

def test_list_backups_success(app_client, mock_backup_service):
    """Test successful listing of backups."""
    mock_backups = [
        {
            "id": "test-backup-123",
            "created_at": "2025-08-14T12:00:00Z",
            "path": "/backups/backup_20250814_120000.zip",
            "size_bytes": 1024000,
            "mode": "manual",
            "app_version": "1.0.0",
            "db_schema_version": 1
        }
    ]
    
    mock_backup_service.backup_list.return_value = mock_backups
    
    response = app_client.get("/api/backups")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "test-backup-123"
    assert data[0]["mode"] == "manual"

def test_create_backup_success(app_client, mock_backup_service):
    """Test successful backup creation."""
    mock_result = {
        "id": "test-backup-123",
        "created_at": "2025-08-14T12:00:00Z",
        "path": "/backups/backup_20250814_120000.zip",
        "size_bytes": 1024000
    }
    
    mock_backup_service.backup_create.return_value = mock_result
    
    response = app_client.post("/api/backups")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-backup-123"
    assert data["size_bytes"] == 1024000

def test_create_backup_failure(app_client, mock_backup_service):
    """Test backup creation failure."""
    mock_backup_service.backup_create.side_effect = Exception("Disk space error")
    
    response = app_client.post("/api/backups")
    
    assert response.status_code == 400
    data = response.json()
    assert "Backup creation failed" in data["detail"]

def test_restore_preview_success(app_client, mock_backup_service):
    """Test successful restore preview."""
    mock_preview = {
        "ok": True,
        "changes": [
            {
                "table": "invoices",
                "adds": 5,
                "updates": 2,
                "deletes": 0
            }
        ]
    }
    
    mock_backup_service.restore_preview.return_value = mock_preview
    
    response = app_client.post("/api/backups/restore?backup_id=test-backup-123&dry_run=true")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert len(data["changes"]) == 1
    assert data["changes"][0]["table"] == "invoices"

def test_restore_preview_failure(app_client, mock_backup_service):
    """Test restore preview failure."""
    mock_preview = {
        "ok": False,
        "reason": "Backup not found"
    }
    
    mock_backup_service.restore_preview.return_value = mock_preview
    
    response = app_client.post("/api/backups/restore?backup_id=invalid-id&dry_run=true")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "Backup not found" in data["reason"]

def test_restore_commit_success(app_client, mock_backup_service):
    """Test successful restore commit."""
    mock_result = {
        "ok": True,
        "pre_restore_backup_id": "pre-restore-123"
    }
    
    mock_backup_service.restore_commit.return_value = mock_result
    
    response = app_client.post("/api/backups/restore?backup_id=test-backup-123&dry_run=false")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "Restore completed successfully" in data["message"]

def test_restore_commit_failure(app_client, mock_backup_service):
    """Test restore commit failure."""
    mock_result = {
        "ok": False,
        "reason": "Database locked"
    }
    
    mock_backup_service.restore_commit.return_value = mock_result
    
    response = app_client.post("/api/backups/restore?backup_id=test-backup-123&dry_run=false")
    
    assert response.status_code == 400
    data = response.json()
    assert "Database locked" in data["detail"]
