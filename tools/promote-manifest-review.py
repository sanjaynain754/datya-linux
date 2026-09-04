#!/usr/bin/env python3
"""Promote manifest entries after exact-artifact copyright-file audit."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest_path = root / "packages/manifest.json"
audit_path = root / "build/manifest-copyright-review.json"
manifest = json.loads(manifest_path.read_text())
audit = json.loads(audit_path.read_text())
if audit["failures"]:
    raise SystemExit("refusing promotion while copyright audit has failures")
audited = {item["name"] for item in audit["packages"]}
changed = 0
for package in manifest["packages"]:
    if package["name"] not in audited:
        raise SystemExit(f"package not audited: {package['name']}")
    package["license"] = "SEE-DEBIAN-COPYRIGHT"
    package["verification_status"] = "verified"
    old = package.get("notes", "")
    package["notes"] = old.replace(
        "Debian copyright/license review remains required before release verification.",
        "Exact artifact copyright file retrieved and reviewed; license terms are maintained in the Debian copyright file."
    )
    if "Exact artifact copyright file retrieved and reviewed" not in package["notes"]:
        package["notes"] += " Exact artifact copyright file retrieved and reviewed; license terms are maintained in the Debian copyright file."
    changed += 1
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print(f"promoted={changed}")
