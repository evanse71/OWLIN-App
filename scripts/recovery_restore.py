#!/usr/bin/env python3
"""
Recovery restore CLI script.
Validates and applies a restore plan.
"""

import sys
import json
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.recovery_service import apply_resolve_plan


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Apply recovery restore plan")
    parser.add_argument("--snapshot", required=True, help="Snapshot ID to restore from")
    parser.add_argument("--plan", required=True, help="Path to resolve plan JSON file")
    
    args = parser.parse_args()
    
    try:
        # Load resolve plan
        with open(args.plan, 'r') as f:
            resolve_plan = json.load(f)
        
        # Validate plan structure
        if "snapshot_id" not in resolve_plan:
            raise ValueError("Resolve plan must contain 'snapshot_id'")
        if "decisions" not in resolve_plan:
            raise ValueError("Resolve plan must contain 'decisions'")
        
        # Apply the plan
        result = apply_resolve_plan(args.snapshot, resolve_plan)
        
        # Print result
        print(json.dumps(result, indent=2))
        
        # Exit with success/failure
        if result.get("ok", False):
            sys.exit(0)
        else:
            sys.exit(1)
            
    except FileNotFoundError:
        print(json.dumps({
            "error": f"Plan file not found: {args.plan}",
            "ok": False
        }, indent=2))
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(json.dumps({
            "error": f"Invalid JSON in plan file: {str(e)}",
            "ok": False
        }, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "ok": False
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main() 