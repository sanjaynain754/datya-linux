#!/usr/bin/env python3
"""Inventory a Datya build/device lab without changing the host."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


def command_info(name: str) -> dict[str, object]:
    path = shutil.which(name)
    result: dict[str, object] = {"available": path is not None}
    if path:
        result["path"] = path
    return result


def run_version(name: str, args: list[str]) -> str | None:
    if not shutil.which(name):
        return None
    try:
        result = subprocess.run([name, *args], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0][:240] if output else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json", help="print JSON instead of a table")
    parser.add_argument("--output", type=Path, help="also write the JSON report to this path")
    parser.add_argument("--strict", action="store_true", help="fail when required build prerequisites are absent")
    args = parser.parse_args()

    kernel = platform.release()
    header_path = Path(f"/lib/modules/{kernel}/build")
    commands = {}
    for name in ("cargo", "rustc", "rustfmt", "clippy-driver", "cmake", "g++", "gcc", "make", "shellcheck", "lb", "qemu-system-x86_64", "qemu-system-aarch64", "podman", "docker", "adb", "fastboot"):
        item = command_info(name)
        version = run_version(name, ["--version"])
        if version:
            item["version"] = version
        commands[name] = item

    network_devices = sorted(p.name for p in Path("/sys/class/net").iterdir()) if Path("/sys/class/net").exists() else []
    block_devices = sorted(p.name for p in Path("/sys/class/block").iterdir()) if Path("/sys/class/block").exists() else []
    report: dict[str, object] = {
        "schema_version": "datya.device-lab.v1",
        "host": {
            "kernel": kernel,
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "architecture": "amd64" if platform.machine() == "x86_64" else "arm64" if platform.machine() == "aarch64" else platform.machine(),
        },
        "commands": commands,
        "devices": {
            "kvm": Path("/dev/kvm").exists(),
            "tun": Path("/dev/net/tun").exists(),
            "usb_bus": Path("/dev/bus/usb").exists(),
            "network_interfaces": network_devices,
            "block_devices": block_devices,
        },
        "kernel_build": {
            "headers_path": str(header_path),
            "headers_available": header_path.is_dir(),
            "target_kernel_match_required": True,
        },
    }
    required = {
        "user_space_build": all(commands[name]["available"] for name in ("cargo", "rustc", "rustfmt", "cmake", "g++", "make")),
        "shell_quality": commands["shellcheck"]["available"],
        "kernel_module_build": header_path.is_dir(),
        "iso_build": commands["lb"]["available"],
        "hardware_vm_lab": commands["qemu-system-x86_64"]["available"] and report["devices"]["kvm"],
    }
    report["readiness"] = required
    report["safe_to_claim_full_lab_build"] = all(bool(value) for value in required.values())

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.as_json or args.output:
        print(json.dumps(report, indent=2))
    else:
        print(f"host: {report['host']['machine']} / kernel {kernel}")
        for key, value in required.items():
            print(f"{key}: {'READY' if value else 'BLOCKED'}")
        print(f"full_lab_build: {'READY' if report['safe_to_claim_full_lab_build'] else 'BLOCKED'}")
    return 1 if args.strict and not report["safe_to_claim_full_lab_build"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
