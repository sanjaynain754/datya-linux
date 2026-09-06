#!/usr/bin/env python3
"""Add or update the pinned official RustScan release in Datya's package manifest."""
import json
from pathlib import Path

path = Path("packages/manifest.json")
data = json.loads(path.read_text())
record = {
    "name": "rustscan",
    "binary_version": "2.4.1",
    "source_package": "rustscan",
    "source_version": "2.4.1",
    "channel": "stable",
    "architectures": ["amd64", "arm64"],
    "repository": "https://github.com/bee-san/RustScan/releases/download/2.4.1",
    "source_url": "https://github.com/bee-san/RustScan",
    "license": "GPL-3.0-only",
    "sha256": "f3a4365d939e3b81f25ba8c37852ce9ac9e938c3cc882c5b3e6fff6152c740be",
    "artifacts": {
        "amd64": {
            "filename": "x86_64-linux-rustscan.tar.gz.zip",
            "size": 2210009,
            "sha256": "f3a4365d939e3b81f25ba8c37852ce9ac9e938c3cc882c5b3e6fff6152c740be",
        },
        "arm64": {
            "filename": "aarch64-linux-rustscan.zip",
            "size": 2054366,
            "sha256": "4f49103e2dfc9e9709a36da2cd61f1f81613f8d0a203307f750439fc3ce39eae",
        },
    },
    "privileges": ["user-tool"],
    "network_behavior": "active-network-connections; explicit-authorized-scope-required; no-automatic-nmap-handoff",
    "profiles": ["security-lab"],
    "status": "catalogued",
    "verification_status": "verified",
    "tests": ["official-release-asset", "artifact-sha256", "dry-run-policy", "scope-check", "operator-confirmation", "sandbox-launch"],
    "uninstall_path": "rm /usr/local/bin/rustscan and remove the manifest record",
    "maintainer": "RustScan upstream maintainers <https://github.com/bee-san/RustScan>",
    "notes": "Pinned to official RustScan 2.4.1 release assets; checksums and sizes were retrieved from GitHub release downloads; Datya does not enable automatic Nmap chaining.",
}
packages = [item for item in data["packages"] if item.get("name") != "rustscan"]
packages.append(record)
packages.sort(key=lambda item: item["name"])
data["packages"] = packages
path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print("rustscan record written; package_count=" + str(len(packages)))
