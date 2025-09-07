#!/usr/bin/env python3
"""
Deterministic bundle generator for testing
"""

import json
import zipfile
import tempfile
from pathlib import Path
import sys

def create_test_bundle(manifest_path: str, output_path: str):
    """Create a test bundle from manifest."""
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
        # Add manifest
        z.writestr('manifest.json', json.dumps(manifest, indent=2))
        
        # Add fake signature (for testing)
        z.writestr('signature.sig', b'fake_signature_for_testing')
        
        # Add minimal files structure
        z.writestr('files/backend/test.py', '# Test file\nprint("Hello from test bundle")\n')
        z.writestr('hooks/post.py', '# Post-update hook\nprint("Post-update hook executed")\n')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python make_bundle.py <manifest.json> <output.zip>")
        sys.exit(1)
    
    manifest_path = sys.argv[1]
    output_path = sys.argv[2]
    
    create_test_bundle(manifest_path, output_path)
    print(f"Created test bundle: {output_path}")
