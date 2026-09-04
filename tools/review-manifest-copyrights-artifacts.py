#!/usr/bin/env python3
"""Audit copyright-file presence in the exact Debian artifacts listed by the manifest."""
import json
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "packages/manifest.json").read_text())
report = []
failures = []
with tempfile.TemporaryDirectory(prefix="datya-copyright-") as tmp:
    tmp_path = Path(tmp)
    for package in manifest["packages"]:
        name = package["name"]
        artifact = package["artifacts"]["amd64"]
        base = package["repository"].rstrip("/") + "/"
        url = base + artifact["filename"]
        deb = tmp_path / (name.replace("/", "_") + ".deb")
        tree = tmp_path / (name.replace("/", "_") + ".root")
        try:
            urllib.request.urlretrieve(url, deb)
            subprocess.run(["dpkg-deb", "-x", str(deb), str(tree)], check=True, stdout=subprocess.DEVNULL)
            candidates = list(tree.glob("usr/share/doc/*/copyright"))
            if not candidates:
                raise RuntimeError("no usr/share/doc/*/copyright file")
            copyright_file = candidates[0]
            text = copyright_file.read_text(errors="replace")
            if "Copyright" not in text and "License" not in text and "license" not in text:
                raise RuntimeError("copyright file has no copyright/license marker")
            report.append({"name": name, "url": url, "copyright": str(copyright_file.relative_to(tree)), "bytes": len(text.encode())})
        except Exception as exc:
            failures.append({"name": name, "url": url, "error": str(exc)})

out = ROOT / "build" / "manifest-copyright-review.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({"packages": report, "failures": failures}, indent=2) + "\n")
print(f"audited={len(report)} failures={len(failures)} output={out}")
for failure in failures:
    print(f"FAIL {failure['name']}: {failure['error']}")
raise SystemExit(1 if failures else 0)
