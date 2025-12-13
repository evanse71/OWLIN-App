#!/usr/bin/env python3
import os, sys, io

TEXT_EXTS = {".py",".ts",".tsx",".js",".json",".yml",".yaml",".md",".toml",".ini",".sql",".css",".scss",".sh",".bat",".ps1",".txt",".env"}
SKIP_DIRS = {".git","node_modules",".venv","venv","build","dist","__pycache__",".pytest_cache",".next",".turbo",".cache"}

def is_text(path):
    _, ext = os.path.splitext(path)
    return ext.lower() in TEXT_EXTS

def normalize_file(path):
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            data = f.read()
    except Exception:
        return False, "read-fail"

    original = data
    # Replace Unicode Line/Paragraph Separators with newline.
    data = data.replace("\u2028", "\n").replace("\u2029", "\n")
    # Normalise CRLF → LF.
    data = data.replace("\r\n", "\n")

    if data != original:
        try:
            with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(data)
            return True, "normalized"
        except Exception:
            return False, "write-fail"
    return False, "unchanged"

def main():
    root = "."
    changed = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if is_text(p):
                ok, status = normalize_file(p)
                if ok: changed += 1
    print(f"normalized_files={changed}")

if __name__ == "__main__":
    sys.exit(main() or 0)
