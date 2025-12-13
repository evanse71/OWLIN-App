#!/usr/bin/env python3
"""
License verification CLI script.
Prints JSON status and exits with appropriate code.
"""

import sys
import json
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.license_service import check_license_state, get_device_fingerprint


def main():
    """Main CLI function."""
    try:
        # Get license state
        state = check_license_state()
        
        # Get device fingerprint
        device_fingerprint = get_device_fingerprint()
        
        # Prepare output
        output = {
            "state": state["state"],
            "reason": state.get("reason"),
            "grace_until": state.get("grace_until_utc"),
            "summary": state.get("summary"),
            "device_fingerprint": device_fingerprint
        }
        
        # Print JSON output
        print(json.dumps(output, indent=2))
        
        # Exit with appropriate code
        if state["valid"]:
            sys.exit(0)  # Valid
        elif state["state"] == "grace":
            sys.exit(10)  # Grace period
        elif state["state"] == "expired":
            sys.exit(20)  # Expired
        else:
            sys.exit(30)  # Invalid/mismatch/not_found
            
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "state": "error"
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main() 