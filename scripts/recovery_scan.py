#!/usr/bin/env python3
"""
Recovery scan CLI script.
Prints RecoveryStatus JSON and exits with appropriate code.
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.recovery_service import get_recovery_status


def main():
    """Main CLI function."""
    try:
        # Get recovery status
        status = get_recovery_status()
        
        # Print JSON output
        print(json.dumps(status, indent=2))
        
        # Exit with appropriate code
        if status["state"] == "normal":
            sys.exit(0)  # Normal
        elif status["state"] == "degraded":
            sys.exit(10)  # Degraded
        elif status["state"] == "recovery":
            sys.exit(20)  # Recovery
        elif status["state"] == "restore_pending":
            sys.exit(30)  # Restore pending
        else:
            sys.exit(1)  # Unknown state
            
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "state": "error"
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main() 