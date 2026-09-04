#!/usr/bin/env python3
"""Check Debian copyright-file presence for every curated package in the built ISO chroot."""
import json
from pathlib import Path

ROOT = Path("iso/chroot")
manifest = json.loads(Path("packages/manifest.json").read_text())
missing = []
found = []
for package in manifest["packages"]:
    name = package["name"]
    candidates = [ROOT / "usr/share/doc" / name / "copyright"]
    if name == "python3-requests":
        candidates.append(ROOT / "usr/share/doc/python3-requests/copyright")
    match = next((p for p in candidates if p.is_file()), None)
    if match:
        found.append((name, str(match.relative_to(ROOT))))
    else:
        missing.append(name)
print(f"copyright_files_found={len(found)}")
for name, path in found:
    print(f"FOUND {name} {path}")
print(f"copyright_files_missing={len(missing)}")
for name in missing:
    print(f"MISSING {name}")
raise SystemExit(1 if missing else 0)

def unused() -> None:
    pass

def main() -> None:
    pass
