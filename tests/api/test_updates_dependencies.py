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

def test_get_dependencies_success(app_client, mock_update_manager):
    """Test successful dependency check."""
    bundle_id = "4ca7b4bf-9d77-4e10-8a9a-b55ed2a56b2a"
    
    mock_result = {
        "bundle_id": bundle_id,
        "items": [
            {
                "id": "app",
                "version": ">=1.2.0",
                "satisfied": True,
                "reason": "current 1.2.3"
            },
            {
                "id": "schema",
                "version": ">=9",
                "satisfied": True,
                "reason": "current 10"
            }
        ],
        "all_satisfied": True
    }
    
    mock_update_manager.compute_dependencies.return_value = mock_result
    
    response = app_client.get(f"/api/updates/dependencies/{bundle_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["bundle_id"] == bundle_id
    assert data["all_satisfied"] is True
    assert len(data["items"]) == 2
    assert data["items"][0]["id"] == "app"
    assert data["items"][0]["satisfied"] is True

def test_get_dependencies_missing_deps(app_client, mock_update_manager):
    """Test dependency check with missing dependencies."""
    bundle_id = "4ca7b4bf-9d77-4e10-8a9a-b55ed2a56b2a"
    
    mock_result = {
        "bundle_id": bundle_id,
        "items": [
            {
                "id": "app",
                "version": ">=1.2.0",
                "satisfied": True,
                "reason": "current 1.2.3"
            },
            {
                "id": "schema",
                "version": ">=12",
                "satisfied": False,
                "reason": "current 10 < required 12"
            }
        ],
        "all_satisfied": False
    }
    
    mock_update_manager.compute_dependencies.return_value = mock_result
    
    response = app_client.get(f"/api/updates/dependencies/{bundle_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["bundle_id"] == bundle_id
    assert data["all_satisfied"] is False
    assert len(data["items"]) == 2
    assert data["items"][1]["id"] == "schema"
    assert data["items"][1]["satisfied"] is False
    assert "current 10 < required 12" in data["items"][1]["reason"]

def test_get_dependencies_empty(app_client, mock_update_manager):
    """Test dependency check with no dependencies."""
    bundle_id = "4ca7b4bf-9d77-4e10-8a9a-b55ed2a56b2a"
    
    mock_result = {
        "bundle_id": bundle_id,
        "items": [],
        "all_satisfied": True
    }
    
    mock_update_manager.compute_dependencies.return_value = mock_result
    
    response = app_client.get(f"/api/updates/dependencies/{bundle_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["bundle_id"] == bundle_id
    assert data["all_satisfied"] is True
    assert len(data["items"]) == 0
