#!/usr/bin/env python3
"""
Generate a signed test update bundle for development/testing.
"""
import json
import zipfile
import hashlib
import os
from pathlib import Path
from nacl.signing import SigningKey


def make_bundle(out="updates/dummy_update.zip"):
	"""Create a signed test update bundle."""
	Path("updates").mkdir(exist_ok=True, parents=True)
	
	# Create manifest
	manifest = {
		"version": "9.9.9",
		"build": "test",
		"created_at": "2025-08-10T00:00:00Z",
		"description": "Test bundle for development",
		"requires_app": ">=0.0.1",
		"min_schema_version": 1,
		"steps": [
			{"action": "run_hook", "path": "hooks/post.py", "timeout_sec": 1}
		]
	}
	
	# Create temporary work directory
	work = Path("tmp_update")
	work.mkdir(exist_ok=True)
	
	# Write manifest
	(work / "manifest.json").write_text(json.dumps(manifest, separators=(',', ':')))
	
	# Create hooks directory and post hook
	(work / "hooks").mkdir(exist_ok=True)
	(work / "hooks/post.py").write_text("print('post hook ok')\n")
	
	# Create initial ZIP without signature
	with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
		z.write(work / "manifest.json", "manifest.json")
		z.write(work / "hooks/post.py", "hooks/post.py")
	
	# Generate signing key
	sk = SigningKey.generate()
	vk_hex = sk.verify_key.encode().hex()
	
	# Write public key
	with open("backend/updates_pubkey_ed25519.hex", "w") as f:
		f.write(vk_hex)
	
	# Create signature
	with zipfile.ZipFile(out, "a", zipfile.ZIP_DEFLATED) as z:
		# Recreate digest identical to verify() logic
		names = sorted([n for n in z.namelist() if n != "signature.sig"])
		catalog = "\n".join(f"{n}:{z.getinfo(n).file_size}" for n in names).encode()
		dig = hashlib.sha256(z.read("manifest.json") + catalog).digest()
		sig = sk.sign(dig).signature
		z.writestr("signature.sig", sig)
	
	# Cleanup
	import shutil
	shutil.rmtree(work)
	
	print(f"✅ Created signed bundle: {out}")
	print(f"✅ Public key written to: backend/updates_pubkey_ed25519.hex")
	print(f"   Key: {vk_hex[:16]}...")
	
	return out


if __name__ == "__main__":
	make_bundle() 