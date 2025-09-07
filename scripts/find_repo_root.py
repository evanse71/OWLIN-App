#!/usr/bin/env python3
import os, json, sys
from pathlib import Path

SKIP_DIRS = {".git","node_modules",".venv","venv","build","dist","__pycache__",".pytest_cache",".next",".turbo",".cache",".idea",".vscode"}
SENTINELS = [
    # (relative_path_glob, weight)
    ("backend", 3),
    ("frontend", 3),
    ("app", 2),
    ("app/ui", 2),
    ("ocr", 2),
    ("backend/ocr", 3),
    ("requirements.txt", 2),
    ("pyproject.toml", 2),
    ("package.json", 2),
    ("data/owlin.db", 4),
    ("owlin.db", 3),
    ("license", 2),
    ("license/*.lic", 4),
    ("scripts", 1),
    ("start_owlin.bat", 2),
    ("start_owlin.sh", 2),
    ("README.md", 1),
    ("Dockerfile", 1),
]
# Bonus: known Owlin components
HINT_FILES = [
    "backend/services/pairing_service.py",
    "backend/ocr/unified_ocr_engine.py",
    "frontend/components/InvoiceCardsPanel.tsx",
    "frontend/components/InvoiceDetailBox.tsx",
    "frontend/components/DocumentPairingSuggestionCard.tsx",
    "frontend/components/UniversalTrendGraph.tsx",
    "backend/services/price_forecasting.py",
    "backend/app.py",
    "app/main.py",
]

def score_dir(root: Path) -> dict:
    score = 0
    found = []
    for rel, w in SENTINELS:
        if any(root.glob(rel)) if any(ch in rel for ch in "*?[]") else (root / rel).exists():
            score += w
            found.append(rel)
    # Bonus for hint files
    hints = []
    for hf in HINT_FILES:
        if (root / hf).exists():
            score += 2
            hints.append(hf)
    return {"path": str(root.resolve()), "score": score, "found": found, "hints": hints}

def discover_candidates(start: Path, max_depth: int = 4):
    # If current folder already looks like a root, prioritise it
    candidates = set([start.resolve()])
    # Walk breadth-first up to max_depth to catch ZIP-unpacked top-level folder patterns
    queue = [start.resolve()]
    seen = set()
    depth = 0
    while queue and depth <= max_depth:
        next_q = []
        for d in queue:
            if d in seen: continue
            seen.add(d)
            try:
                for child in d.iterdir():
                    if child.is_dir() and child.name not in SKIP_DIRS:
                        candidates.add(child.resolve())
                        next_q.append(child.resolve())
            except Exception:
                pass
        queue = next_q
        depth += 1
    return sorted(candidates)

def main():
    start = Path(".").resolve()
    cands = discover_candidates(start)
    scored = []
    for c in cands:
        scored.append(score_dir(c))
    # Keep only plausible roots (score > threshold)
    plausible = [x for x in scored if x["score"] >= 6]
    # Fallback: choose best even if low score
    chosen = None
    if plausible:
        plausible.sort(key=lambda x: x["score"], reverse=True)
        chosen = plausible[0]
    else:
        scored.sort(key=lambda x: x["score"], reverse=True)
        chosen = scored[0] if scored else None
    out = {
        "start_dir": str(start),
        "candidates_considered": len(scored),
        "top5": sorted(scored, key=lambda x: x["score"], reverse=True)[:5],
        "chosen": chosen,
    }
    print(json.dumps(out, indent=2))
    # Exit codes: 0 ok, 2 no candidates
    if not chosen:
        sys.exit(2)

if __name__ == "__main__":
    main()
