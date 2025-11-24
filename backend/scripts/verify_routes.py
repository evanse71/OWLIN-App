"""Verify that chat routes are registered correctly."""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from backend.main import app
    routes = [r for r in app.routes if hasattr(r, 'path') and '/api/chat' in r.path]
    print(f"Found {len(routes)} chat routes:")
    for route in routes:
        print(f"  {list(route.methods)} {route.path}")
    
    # Check for POST /api/chat
    post_chat = [r for r in routes if r.path == '/api/chat' and 'POST' in r.methods]
    if post_chat:
        print("\n✓ POST /api/chat is registered")
    else:
        print("\n✗ POST /api/chat is NOT registered!")
        sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

