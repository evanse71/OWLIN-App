import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

@pytest.fixture
def mock_support_pack_service():
    with patch('backend.routes.support_packs.support_pack_service') as mock:
        yield mock

@pytest.fixture
def app_client():
    from backend.main_fixed import app
    return TestClient(app)

def test_list_support_packs_success(app_client, mock_support_pack_service):
    """Test successful listing of support packs."""
    mock_packs = [
        {
            "id": "test-pack-123",
            "created_at": "2025-08-14T12:00:00Z",
            "path": "/support_packs/support_pack_20250814_120000.zip",
            "size_bytes": 2048000,
            "notes": "Post-incident analysis",
            "app_version": "1.0.0"
        }
    ]
    
    mock_support_pack_service.pack_list.return_value = mock_packs
    
    response = app_client.get("/api/support-packs")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "test-pack-123"
    assert data[0]["notes"] == "Post-incident analysis"

def test_create_support_pack_success(app_client, mock_support_pack_service):
    """Test successful support pack creation."""
    mock_result = {
        "id": "test-pack-123",
        "created_at": "2025-08-14T12:00:00Z",
        "path": "/support_packs/support_pack_20250814_120000.zip",
        "size_bytes": 2048000,
        "notes": "Post-incident analysis",
        "app_version": "1.0.0"
    }
    
    mock_support_pack_service.pack_create.return_value = mock_result
    
    response = app_client.post("/api/support-packs", json={"notes": "Post-incident analysis"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-pack-123"
    assert data["size_bytes"] == 2048000
    assert data["notes"] == "Post-incident analysis"

def test_create_support_pack_failure(app_client, mock_support_pack_service):
    """Test support pack creation failure."""
    mock_support_pack_service.pack_create.side_effect = Exception("Disk space error")
    
    response = app_client.post("/api/support-packs")
    
    assert response.status_code == 400
    data = response.json()
    assert "Support pack creation failed" in data["detail"]

def test_download_support_pack_success(app_client, mock_support_pack_service):
    """Test successful support pack download."""
    mock_pack_info = {
        "id": "test-pack-123",
        "created_at": "2025-08-14T12:00:00Z",
        "path": "/support_packs/support_pack_20250814_120000.zip",
        "size_bytes": 2048000,
        "notes": "Post-incident analysis",
        "app_version": "1.0.0"
    }
    
    mock_support_pack_service.pack_get_info.return_value = mock_pack_info
    mock_support_pack_service.pack_stream.return_value = [b"fake zip content"]
    
    response = app_client.get("/api/support-packs/test-pack-123/download")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]

def test_download_support_pack_not_found(app_client, mock_support_pack_service):
    """Test support pack download when pack not found."""
    mock_support_pack_service.pack_get_info.return_value = None
    
    response = app_client.get("/api/support-packs/invalid-id/download")
    
    assert response.status_code == 404
    data = response.json()
    assert "Support pack not found" in data["detail"]

def test_list_support_packs_empty(app_client, mock_support_pack_service):
    """Test listing support packs when none exist."""
    mock_support_pack_service.pack_list.return_value = []
    
    response = app_client.get("/api/support-packs")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

def test_create_support_pack_no_notes(app_client, mock_support_pack_service):
    """Test support pack creation without notes."""
    mock_result = {
        "id": "test-pack-123",
        "created_at": "2025-08-14T12:00:00Z",
        "path": "/support_packs/support_pack_20250814_120000.zip",
        "size_bytes": 2048000,
        "notes": None,
        "app_version": "1.0.0"
    }
    
    mock_support_pack_service.pack_create.return_value = mock_result
    
    response = app_client.post("/api/support-packs")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-pack-123"
    assert data["notes"] is None
