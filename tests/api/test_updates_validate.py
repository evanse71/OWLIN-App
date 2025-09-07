import pytest
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Mock the update manager
@pytest.fixture
def mock_update_manager():
    with patch('backend.routes.updates.svc') as mock:
        yield mock

@pytest.fixture
def app_client():
    from backend.main_fixed import app
    return TestClient(app)

def test_validate_update_success(app_client, mock_update_manager):
    """Test successful validation of an update bundle."""
    bundle_id = "4ca7b4bf-9d77-4e10-8a9a-b55ed2a56b2a"
    
    mock_result = {
        "bundle_id": bundle_id,
        "filename": "update_1.3.0.zip",
        "version": "1.3.0",
        "build": "2025-08-10.1",
        "signature_ok": True,
        "manifest_ok": True,
        "reason": None,
        "checksum_sha256": "5d41402abc4b2a76b9719d911017c592",
        "created_at": "2025-08-10T12:34:56Z"
    }
    
    mock_update_manager.validate_bundle.return_value = mock_result
    
    response = app_client.get(f"/api/updates/validate/{bundle_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["bundle_id"] == bundle_id
    assert data["signature_ok"] is True
    assert data["manifest_ok"] is True
    assert data["filename"] == "update_1.3.0.zip"

def test_validate_update_not_found(app_client, mock_update_manager):
    """Test validation of non-existent bundle."""
    bundle_id = "non-existent-id"
    
    mock_result = {
        "bundle_id": bundle_id,
        "filename": "",
        "version": "",
        "build": "",
        "signature_ok": False,
        "manifest_ok": False,
        "reason": "Bundle not found",
        "checksum_sha256": None,
        "created_at": None
    }
    
    mock_update_manager.validate_bundle.return_value = mock_result
    
    response = app_client.get(f"/api/updates/validate/{bundle_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["signature_ok"] is False
    assert data["manifest_ok"] is False
    assert "Bundle not found" in data["reason"]

def test_validate_update_invalid_signature(app_client, mock_update_manager):
    """Test validation with invalid signature."""
    bundle_id = "4ca7b4bf-9d77-4e10-8a9a-b55ed2a56b2a"
    
    mock_result = {
        "bundle_id": bundle_id,
        "filename": "update_1.3.0.zip",
        "version": "1.3.0",
        "build": "2025-08-10.1",
        "signature_ok": False,
        "manifest_ok": True,
        "reason": "signature mismatch",
        "checksum_sha256": "5d41402abc4b2a76b9719d911017c592",
        "created_at": "2025-08-10T12:34:56Z"
    }
    
    mock_update_manager.validate_bundle.return_value = mock_result
    
    response = app_client.get(f"/api/updates/validate/{bundle_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["signature_ok"] is False
    assert data["manifest_ok"] is True
    assert "signature mismatch" in data["reason"]
