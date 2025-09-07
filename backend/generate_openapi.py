from __future__ import annotations
import json
from pathlib import Path

from backend.main import app


def main() -> None:
	spec = app.openapi()
	out_path = Path("backend/openapi.json")
	out_path.parent.mkdir(parents=True, exist_ok=True)
	out_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
	print(f"wrote {out_path}")


if __name__ == "__main__":
	main() 