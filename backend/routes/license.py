from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
from typing import Optional

from contracts import LicenseStatus, LicenseUploadRequest, LicenseUploadResponse, LicenseVerifyResponse
from services.license_service import (
    check_license_state, store_license, get_device_fingerprint,
    canonicalize_license, verify_signature, log_license_audit
)

router = APIRouter(prefix="/license", tags=["license"])


@router.get("/status", response_model=LicenseStatus)
async def get_license_status():
    """
    Get current license status.
    
    Returns the current license state including validity, grace period,
    and summary information. Never returns 500 - degrades gracefully.
    """
    try:
        state = check_license_state()
        
        # Log audit event
        log_license_audit("license.status", state["state"], state.get("reason"))
        
        return LicenseStatus(**state)
        
    except Exception as e:
        # Degrade gracefully - return not_found state
        log_license_audit("license.status", "not_found", "LICENSE_NOT_FOUND")
        return LicenseStatus(
            valid=False,
            state="not_found",
            reason="LICENSE_NOT_FOUND",
            grace_until_utc=None,
            summary=None
        )


@router.post("/upload", response_model=LicenseUploadResponse)
async def upload_license(
    file: Optional[UploadFile] = File(None),
    license_content: Optional[str] = Form(None)
):
    """
    Upload and activate a license file.
    
    Accepts either a file upload or JSON content. Validates the license
    and stores it if valid.
    """
    try:
        # Get license content from file or form
        content = None
        
        if file:
            content = await file.read()
            content = content.decode('utf-8')
        elif license_content:
            content = license_content
        else:
            raise HTTPException(400, "No license content provided")
        
        # Store license
        if not store_license(content):
            raise HTTPException(400, "Invalid license format")
        
        # Check new state
        state = check_license_state()
        
        # Log audit event
        log_license_audit("license.upload", state["state"], state.get("reason"))
        
        return LicenseUploadResponse(
            ok=state["valid"],
            message="License uploaded successfully" if state["valid"] else f"License uploaded but invalid: {state.get('reason', 'Unknown error')}",
            status=LicenseStatus(**state)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_license_audit("license.upload", "invalid", "UPLOAD_ERROR")
        raise HTTPException(500, f"Failed to upload license: {str(e)}")


@router.get("/verify", response_model=LicenseVerifyResponse)
async def verify_license():
    """
    Detailed license verification (dev-only).
    
    Returns comprehensive verification details including signature,
    device binding, expiry, and grace period status.
    """
    # Check if dev mode is enabled
    if not os.getenv("DEV_MODE", "false").lower() == "true":
        raise HTTPException(403, "Verification endpoint requires DEV_MODE=true")
    
    try:
        from services.license_service import LICENSE_FILE
        
        # Check if license file exists
        if not LICENSE_FILE.exists():
            return LicenseVerifyResponse(
                signature_valid=False,
                device_match=False,
                expiry_check="NO_LICENSE_FILE",
                grace_period=None,
                overall_valid=False
            )
        
        # Load and verify license
        import json
        with open(LICENSE_FILE, 'r') as f:
            license_data = json.load(f)
        
        # Check signature
        signature_valid = verify_signature(license_data)
        
        # Check device binding
        device_id = license_data.get("device_id")
        current_device = get_device_fingerprint()
        device_match = device_id == current_device
        
        # Check expiry
        from datetime import datetime
        expires_utc = license_data.get("expires_utc")
        if expires_utc:
            try:
                expiry_date = datetime.fromisoformat(expires_utc.replace('Z', '+00:00'))
                now = datetime.utcnow().replace(tzinfo=expiry_date.tzinfo)
                
                if now > expiry_date:
                    from datetime import timedelta
                    grace_until = expiry_date + timedelta(hours=72)
                    if now <= grace_until:
                        expiry_check = "EXPIRED_IN_GRACE"
                        grace_period = grace_until.isoformat()
                    else:
                        expiry_check = "EXPIRED"
                        grace_period = None
                else:
                    expiry_check = "VALID"
                    grace_period = None
            except ValueError:
                expiry_check = "INVALID_DATE"
                grace_period = None
        else:
            expiry_check = "NO_EXPIRY"
            grace_period = None
        
        # Overall validity
        overall_valid = signature_valid and device_match and expiry_check in ["VALID", "EXPIRED_IN_GRACE"]
        
        return LicenseVerifyResponse(
            signature_valid=signature_valid,
            device_match=device_match,
            expiry_check=expiry_check,
            grace_period=grace_period,
            overall_valid=overall_valid
        )
        
    except Exception as e:
        raise HTTPException(500, f"Verification failed: {str(e)}")


@router.get("/device-fingerprint")
async def get_device_fingerprint():
    """
    Get current device fingerprint (dev-only).
    """
    if not os.getenv("DEV_MODE", "false").lower() == "true":
        raise HTTPException(403, "Device fingerprint endpoint requires DEV_MODE=true")
    
    try:
        fingerprint = get_device_fingerprint()
        return {"device_fingerprint": fingerprint}
    except Exception as e:
        raise HTTPException(500, f"Failed to get device fingerprint: {str(e)}") 