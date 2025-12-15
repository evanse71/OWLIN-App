#!/usr/bin/env python3
"""Test backend startup to find where it hangs"""
import sys
import os
from pathlib import Path

# Set environment before any imports
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

# Add project root to path
_BACKEND_DIR = Path(__file__).resolve().parent / "backend"
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

print("=" * 60)
print("Testing Backend Startup")
print("=" * 60)
print()

steps = [
    ("Setting environment", lambda: None),
    ("Importing sys/pathlib", lambda: None),
    ("Importing FastAPI", lambda: __import__("fastapi")),
    ("Importing backend.config", lambda: __import__("backend.config")),
    ("Importing backend.app.db", lambda: __import__("backend.app.db")),
    ("Calling init_db()", lambda: __import__("backend.app.db").init_db()),
    ("Importing backend.main", lambda: __import__("backend.main")),
]

for i, (step_name, step_func) in enumerate(steps, 1):
    print(f"[{i}/{len(steps)}] {step_name}...", end=" ", flush=True)
    try:
        step_func()
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nHUNG at step:", step_name)
        print("This is where the backend is hanging!")
        sys.exit(1)

print()
print("=" * 60)
print("All startup steps completed successfully!")
print("=" * 60)
