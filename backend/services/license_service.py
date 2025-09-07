import os
import json
import hashlib
import base64
import subprocess
import platform
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from uuid import uuid4
import sqlite3

# Ed25519 public key for signature verification (embedded constant)
LICENSE_PUBLIC_KEY = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"

# Constants
LICENSE_DIR = Path("license")
LICENSE_FILE = LICENSE_DIR / "owlin.lic"
DEVICE_FINGERPRINT_FILE = Path("data/device_fingerprint.txt")
GRACE_PERIOD_HOURS = 72

# Ensure directories exist
LICENSE_DIR.mkdir(exist_ok=True)
DEVICE_FINGERPRINT_FILE.parent.mkdir(exist_ok=True)


def get_device_fingerprint() -> str:
    """Generate or retrieve device fingerprint."""
    if DEVICE_FINGERPRINT_FILE.exists():
        return DEVICE_FINGERPRINT_FILE.read_text().strip()
    
    # Generate new fingerprint
    device_id = _generate_device_id()
    fingerprint = f"OWLIN-{device_id}"
    
    # Persist fingerprint
    DEVICE_FINGERPRINT_FILE.write_text(fingerprint)
    return fingerprint


def _generate_device_id() -> str:
    """Generate device ID from system information."""
    system_info = []
    
    try:
        if platform.system() == "Darwin":  # macOS
            # Try to get IOPlatformUUID
            try:
                result = subprocess.run(
                    ["ioreg", "-d2", "-c", "IOPlatformExpertDevice"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'IOPlatformUUID' in line:
                            uuid = line.split('"')[1]
                            system_info.append(uuid)
                            break
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
                
        elif platform.system() == "Windows":
            # Try to get WMI UUID
            try:
                result = subprocess.run(
                    ["wmic", "csproduct", "get", "UUID"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        uuid = lines[1].strip()
                        if uuid and uuid != "UUID":
                            system_info.append(uuid)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
                
        elif platform.system() == "Linux":
            # Try /sys/class/dmi/id/product_uuid
            uuid_file = Path("/sys/class/dmi/id/product_uuid")
            if uuid_file.exists():
                uuid = uuid_file.read_text().strip()
                if uuid:
                    system_info.append(uuid)
            else:
                # Try /etc/machine-id
                machine_id_file = Path("/etc/machine-id")
                if machine_id_file.exists():
                    machine_id = machine_id_file.read_text().strip()
                    if machine_id:
                        system_info.append(machine_id)
                        
    except Exception:
        pass
    
    # If no system info found, generate random UUID
    if not system_info:
        system_info.append(str(uuid4()))
    
    # Hash the first available system info
    device_string = system_info[0]
    hash_obj = hashlib.sha256(device_string.encode())
    return hash_obj.hexdigest()[:8]


def canonicalize_license(license_data: Dict[str, Any]) -> str:
    """Create canonical JSON string (sorted keys, no signature)."""
    # Remove signature field
    data_without_signature = {k: v for k, v in license_data.items() if k != "signature"}
    
    # Sort keys and serialize
    return json.dumps(data_without_signature, separators=(',', ':'), sort_keys=True)


def verify_signature(license_data: Dict[str, Any]) -> bool:
    """Verify Ed25519 signature of license."""
    try:
        # Get canonical JSON
        canonical_json = canonicalize_license(license_data)
        
        # Get signature
        signature = license_data.get("signature")
        if not signature:
            return False
        
        # For now, return True for any valid signature field (placeholder)
        # In production, verify with actual Ed25519 library
        return True
        
    except Exception:
        return False


def check_license_state() -> Dict[str, Any]:
    """Check current license state and return status."""
    try:
        if not LICENSE_FILE.exists():
            return {
                "valid": False,
                "state": "not_found",
                "reason": "LICENSE_NOT_FOUND",
                "grace_until_utc": None,
                "summary": None
            }
        
        # Load license file
        with open(LICENSE_FILE, 'r') as f:
            license_data = json.load(f)
        
        # Verify signature
        if not verify_signature(license_data):
            return {
                "valid": False,
                "state": "invalid",
                "reason": "LICENSE_INVALID_SIGNATURE",
                "grace_until_utc": None,
                "summary": None
            }
        
        # Check schema version
        schema = license_data.get("schema", 0)
        if schema != 1:
            return {
                "valid": False,
                "state": "invalid",
                "reason": "LICENSE_SCHEMA_UNSUPPORTED",
                "grace_until_utc": None,
                "summary": None
            }
        
        # Check device binding
        device_id = license_data.get("device_id")
        current_device = get_device_fingerprint()
        if device_id != current_device:
            return {
                "valid": False,
                "state": "mismatch",
                "reason": "LICENSE_DEVICE_MISMATCH",
                "grace_until_utc": None,
                "summary": _create_summary(license_data)
            }
        
        # Check expiry
        expires_utc = license_data.get("expires_utc")
        if not expires_utc:
            return {
                "valid": False,
                "state": "invalid",
                "reason": "LICENSE_INVALID_SIGNATURE",
                "grace_until_utc": None,
                "summary": None
            }
        
        try:
            expiry_date = datetime.fromisoformat(expires_utc.replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=expiry_date.tzinfo)
            
            if now > expiry_date:
                # Check grace period
                grace_until = expiry_date + timedelta(hours=GRACE_PERIOD_HOURS)
                
                if now <= grace_until:
                    return {
                        "valid": True,
                        "state": "grace",
                        "reason": None,
                        "grace_until_utc": grace_until.isoformat(),
                        "summary": _create_summary(license_data)
                    }
                else:
                    return {
                        "valid": False,
                        "state": "expired",
                        "reason": "LICENSE_EXPIRED",
                        "grace_until_utc": None,
                        "summary": _create_summary(license_data)
                    }
            else:
                return {
                    "valid": True,
                    "state": "valid",
                    "reason": None,
                    "grace_until_utc": None,
                    "summary": _create_summary(license_data)
                }
                
        except ValueError:
            return {
                "valid": False,
                "state": "invalid",
                "reason": "LICENSE_INVALID_SIGNATURE",
                "grace_until_utc": None,
                "summary": None
            }
            
    except Exception as e:
        return {
            "valid": False,
            "state": "invalid",
            "reason": "LICENSE_INVALID_SIGNATURE",
            "grace_until_utc": None,
            "summary": None
        }


def _create_summary(license_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create license summary from license data."""
    return {
        "customer": license_data.get("customer", ""),
        "license_id": license_data.get("license_id", ""),
        "expires_utc": license_data.get("expires_utc", ""),
        "device_id": license_data.get("device_id", ""),
        "venues": license_data.get("venue_ids", []),
        "roles": license_data.get("roles", {}),
        "features": license_data.get("features", {})
    }


def store_license(license_content: str) -> bool:
    """Store license file."""
    try:
        # Validate JSON format
        license_data = json.loads(license_content)
        
        # Ensure license directory exists
        LICENSE_DIR.mkdir(exist_ok=True)
        
        # Write license file
        with open(LICENSE_FILE, 'w') as f:
            json.dump(license_data, f, indent=2)
        
        return True
    except Exception:
        return False


def check_role_limit(role: str, venue_id: str) -> Tuple[bool, int, int]:
    """Check if role limit is exceeded for venue."""
    try:
        # Get current license state
        state = check_license_state()
        if not state["valid"]:
            return False, 0, 0
        
        summary = state["summary"]
        if not summary:
            return False, 0, 0
        
        # Get role limit
        role_limits = summary.get("roles", {})
        limit = role_limits.get(role, 0)
        
        if limit == 0:
            return True, 0, 0  # No limit
        
        # Count current users with this role in this venue
        conn = sqlite3.connect("data/owlin.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM user_roles 
            WHERE role_id = ? AND venue_id = ?
        """, (role, venue_id))
        
        current_count = cursor.fetchone()[0]
        conn.close()
        
        return current_count < limit, current_count, limit
        
    except Exception:
        return False, 0, 0


def log_license_audit(action: str, state: str, reason: Optional[str] = None):
    """Log license audit event."""
    try:
        conn = sqlite3.connect("data/owlin.db")
        cursor = conn.cursor()
        
        # Ensure audit_log table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS license_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                state TEXT NOT NULL,
                reason TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            INSERT INTO license_audit (action, state, reason, timestamp)
            VALUES (?, ?, ?, ?)
        """, (action, state, reason, datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()
        
    except Exception:
        pass  # Don't fail if audit logging fails


def require_license(feature: Optional[str] = None):
    """Dependency for requiring valid license."""
    def _check_license():
        state = check_license_state()
        
        if not state["valid"]:
            raise Exception(f"403 {state['reason'] or 'LICENSE_INVALID'}")
        
        if feature and state["summary"]:
            features = state["summary"].get("features", {})
            if not features.get(feature, False):
                raise Exception(f"403 LICENSE_FEATURE_NOT_ENABLED: {feature}")
        
        return state
    
    return _check_license 