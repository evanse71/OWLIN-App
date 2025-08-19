import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from uuid import uuid4

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.license_service import (
    get_device_fingerprint, canonicalize_license, verify_signature,
    check_license_state, store_license, check_role_limit, log_license_audit
)


@pytest.fixture
def temp_license_dir():
    """Create temporary license directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create license subdirectory
        license_dir = Path(temp_dir) / "license"
        license_dir.mkdir()
        
        # Create data subdirectory
        data_dir = Path(temp_dir) / "data"
        data_dir.mkdir()
        
        yield temp_dir, license_dir, data_dir


@pytest.fixture
def sample_license_data():
    """Create sample license data."""
    return {
        "customer": "Test Customer Ltd",
        "device_id": "OWLIN-test123",
        "expires_utc": "2026-12-31T23:59:59Z",
        "features": {
            "ocr": True,
            "forecasting": True,
            "updates": True
        },
        "license_id": str(uuid4()),
        "roles": {
            "gm": 2,
            "finance": 4,
            "shift_lead": 12
        },
        "schema": 1,
        "venue_ids": ["VENUE-ALPHA", "VENUE-BETA"],
        "signature": "test_signature_base64"
    }


@pytest.fixture
def expired_license_data(sample_license_data):
    """Create expired license data."""
    expired_data = sample_license_data.copy()
    expired_data["expires_utc"] = "2020-01-01T00:00:00Z"
    return expired_data


@pytest.fixture
def grace_period_license_data(sample_license_data):
    """Create license data in grace period."""
    grace_data = sample_license_data.copy()
    # Set expiry to 24 hours ago (within 72-hour grace period)
    grace_data["expires_utc"] = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
    return grace_data


def test_get_device_fingerprint_new(temp_license_dir):
    """Test generating new device fingerprint."""
    temp_dir, license_dir, data_dir = temp_license_dir
    
    with patch('services.license_service.DEVICE_FINGERPRINT_FILE', data_dir / "device_fingerprint.txt"):
        fingerprint = get_device_fingerprint()
        
        assert fingerprint.startswith("OWLIN-")
        assert len(fingerprint) == 14  # "OWLIN-" + 8 hex chars
        
        # Check that fingerprint was persisted
        fingerprint_file = data_dir / "device_fingerprint.txt"
        assert fingerprint_file.exists()
        assert fingerprint_file.read_text().strip() == fingerprint


def test_get_device_fingerprint_existing(temp_license_dir):
    """Test retrieving existing device fingerprint."""
    temp_dir, license_dir, data_dir = temp_license_dir
    
    # Create existing fingerprint
    fingerprint_file = data_dir / "device_fingerprint.txt"
    fingerprint_file.write_text("OWLIN-existing123")
    
    with patch('services.license_service.DEVICE_FINGERPRINT_FILE', fingerprint_file):
        fingerprint = get_device_fingerprint()
        assert fingerprint == "OWLIN-existing123"


def test_canonicalize_license(sample_license_data):
    """Test license canonicalization."""
    canonical = canonicalize_license(sample_license_data)
    
    # Should not contain signature
    assert "signature" not in canonical
    
    # Should be valid JSON
    parsed = json.loads(canonical)
    assert "customer" in parsed
    assert "device_id" in parsed
    assert "signature" not in parsed


def test_verify_signature_valid(sample_license_data):
    """Test signature verification (placeholder)."""
    # This is a placeholder test since we're not implementing actual Ed25519 verification
    # The current implementation returns True for any valid JSON with signature
    result = verify_signature(sample_license_data)
    assert result is True


def test_verify_signature_missing(sample_license_data):
    """Test signature verification with missing signature."""
    license_data = sample_license_data.copy()
    del license_data["signature"]
    
    result = verify_signature(license_data)
    assert result is False


def test_check_license_state_not_found(temp_license_dir):
    """Test license state when no license file exists."""
    temp_dir, license_dir, data_dir = temp_license_dir
    
    with patch('services.license_service.LICENSE_FILE', license_dir / "nonexistent.lic"):
        state = check_license_state()
        
        assert state["valid"] is False
        assert state["state"] == "not_found"
        assert state["reason"] == "LICENSE_NOT_FOUND"
        assert state["summary"] is None


def test_check_license_state_valid(temp_license_dir, sample_license_data):
    """Test license state with valid license."""
    temp_dir, license_dir, data_dir = temp_license_dir
    
    # Create license file
    license_file = license_dir / "owlin.lic"
    with open(license_file, 'w') as f:
        json.dump(sample_license_data, f)
    
    with patch('services.license_service.LICENSE_FILE', license_file):
        with patch('services.license_service.get_device_fingerprint', return_value="OWLIN-test123"):
            state = check_license_state()
            
            assert state["valid"] is True
            assert state["state"] == "valid"
            assert state["reason"] is None
            assert state["summary"] is not None
            assert state["summary"]["customer"] == "Test Customer Ltd"


def test_check_license_state_device_mismatch(temp_license_dir, sample_license_data):
    """Test license state with device mismatch."""
    temp_dir, license_dir, data_dir = temp_license_dir
    
    # Create license file
    license_file = license_dir / "owlin.lic"
    with open(license_file, 'w') as f:
        json.dump(sample_license_data, f)
    
    with patch('services.license_service.LICENSE_FILE', license_file):
        with patch('services.license_service.get_device_fingerprint', return_value="OWLIN-different"):
            state = check_license_state()
            
            assert state["valid"] is False
            assert state["state"] == "mismatch"
            assert state["reason"] == "LICENSE_DEVICE_MISMATCH"
            assert state["summary"] is not None


def test_check_license_state_expired(temp_license_dir, expired_license_data):
    """Test license state with expired license."""
    temp_dir, license_dir, data_dir = temp_license_dir
    
    # Create license file
    license_file = license_dir / "owlin.lic"
    with open(license_file, 'w') as f:
        json.dump(expired_license_data, f)
    
    with patch('services.license_service.LICENSE_FILE', license_file):
        with patch('services.license_service.get_device_fingerprint', return_value="OWLIN-test123"):
            state = check_license_state()
            
            assert state["valid"] is False
            assert state["state"] == "expired"
            assert state["reason"] == "LICENSE_EXPIRED"
            assert state["summary"] is not None


def test_check_license_state_grace_period(temp_license_dir, grace_period_license_data):
    """Test license state with license in grace period."""
    temp_dir, license_dir, data_dir = temp_license_dir
    
    # Create license file
    license_file = license_dir / "owlin.lic"
    with open(license_file, 'w') as f:
        json.dump(grace_period_license_data, f)
    
    with patch('services.license_service.LICENSE_FILE', license_file):
        with patch('services.license_service.get_device_fingerprint', return_value="OWLIN-test123"):
            state = check_license_state()
            
            assert state["valid"] is True
            assert state["state"] == "grace"
            assert state["reason"] is None
            assert state["grace_until_utc"] is not None
            assert state["summary"] is not None


def test_store_license_valid(temp_license_dir, sample_license_data):
    """Test storing valid license."""
    temp_dir, license_dir, data_dir = temp_license_dir
    
    with patch('services.license_service.LICENSE_FILE', license_dir / "owlin.lic"):
        result = store_license(json.dumps(sample_license_data))
        
        assert result is True
        
        # Check that file was created
        license_file = license_dir / "owlin.lic"
        assert license_file.exists()
        
        # Check content
        with open(license_file, 'r') as f:
            stored_data = json.load(f)
        assert stored_data["customer"] == sample_license_data["customer"]


def test_store_license_invalid_json(temp_license_dir):
    """Test storing invalid JSON license."""
    temp_dir, license_dir, data_dir = temp_license_dir
    
    with patch('services.license_service.LICENSE_FILE', license_dir / "owlin.lic"):
        result = store_license("invalid json")
        
        assert result is False


@patch('services.license_service.sqlite3.connect')
def test_check_role_limit_valid(mock_connect, temp_license_dir, sample_license_data):
    """Test role limit check when within limits."""
    temp_dir, license_dir, data_dir = temp_license_dir
    
    # Mock database connection
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = (1,)  # 1 user with role
    mock_connect.return_value.cursor.return_value = mock_cursor
    
    # Create license file
    license_file = license_dir / "owlin.lic"
    with open(license_file, 'w') as f:
        json.dump(sample_license_data, f)
    
    with patch('services.license_service.LICENSE_FILE', license_file):
        with patch('services.license_service.get_device_fingerprint', return_value="OWLIN-test123"):
            result, current, limit = check_role_limit("gm", "VENUE-ALPHA")
            
            assert result is True
            assert current == 1
            assert limit == 2


@patch('services.license_service.sqlite3.connect')
def test_check_role_limit_exceeded(mock_connect, temp_license_dir, sample_license_data):
    """Test role limit check when limit exceeded."""
    temp_dir, license_dir, data_dir = temp_license_dir
    
    # Mock database connection
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = (3,)  # 3 users with role (exceeds limit of 2)
    mock_connect.return_value.cursor.return_value = mock_cursor
    
    # Create license file
    license_file = license_dir / "owlin.lic"
    with open(license_file, 'w') as f:
        json.dump(sample_license_data, f)
    
    with patch('services.license_service.LICENSE_FILE', license_file):
        with patch('services.license_service.get_device_fingerprint', return_value="OWLIN-test123"):
            result, current, limit = check_role_limit("gm", "VENUE-ALPHA")
            
            assert result is False
            assert current == 3
            assert limit == 2


@patch('services.license_service.sqlite3.connect')
def test_log_license_audit(mock_connect):
    """Test license audit logging."""
    mock_cursor = Mock()
    mock_connect.return_value.cursor.return_value = mock_cursor
    
    log_license_audit("test.action", "valid", "test_reason")
    
    # Verify table creation (check that it was called with the right pattern)
    create_table_calls = [call for call in mock_cursor.execute.call_args_list if 'CREATE TABLE IF NOT EXISTS license_audit' in str(call)]
    assert len(create_table_calls) > 0
    
    # Verify insert (check that it was called with the right pattern)
    insert_calls = [call for call in mock_cursor.execute.call_args_list if 'INSERT INTO license_audit' in str(call)]
    assert len(insert_calls) > 0
    
    mock_connect.return_value.commit.assert_called_once()
    mock_connect.return_value.close.assert_called_once()


def test_require_license_dependency():
    """Test license requirement dependency."""
    from services.license_service import require_license
    
    # Test with valid license
    with patch('services.license_service.check_license_state') as mock_check:
        mock_check.return_value = {
            "valid": True,
            "state": "valid",
            "summary": {
                "features": {"ocr": True}
            }
        }
        
        dependency = require_license("ocr")
        result = dependency()
        
        assert result["valid"] is True
        assert result["state"] == "valid"
    
    # Test with invalid license
    with patch('services.license_service.check_license_state') as mock_check:
        mock_check.return_value = {
            "valid": False,
            "state": "expired",
            "reason": "LICENSE_EXPIRED"
        }
        
        dependency = require_license()
        
        with pytest.raises(Exception) as exc_info:
            dependency()
        
        assert "403 LICENSE_EXPIRED" in str(exc_info.value) 