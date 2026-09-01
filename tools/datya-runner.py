#!/usr/bin/env python3
"""Datya local developer runner MVP.

This is a transparent local runner, not a complete sandbox. For real isolation,
use the Lab profile only on a host configured with a VM or container runtime.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path


def limits(cpu_seconds: int, memory_mb: int):
    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        memory = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_NPROC, (128, 128))

    return apply


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Datya project command with an explicit profile")
    parser.add_argument("--profile", choices=("safe", "project", "lab"), default="safe")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--memory-mb", type=int, default=1024)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--", dest="separator", nargs="?")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.command:
        parser.error("provide a command after --")
    if args.timeout < 1 or args.memory_mb < 64:
        parser.error("timeout must be positive and memory must be at least 64 MB")
    if args.profile == "safe" and args.allow_network:
        parser.error("safe profile cannot allow network; use project profile explicitly")
    if not args.cwd.is_dir():
        parser.error(f"working directory does not exist: {args.cwd}")

    command = args.command[1:] if args.command and args.command[0] == "--" else args.command
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(args.cwd),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "DATYA_PROFILE": args.profile,
        "DATYA_NETWORK": "allowed" if args.allow_network else "disabled",
    }
    if args.profile == "lab":
        print("warning: lab profile is for authorized testing only; configure VM/container isolation", file=sys.stderr)

    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=args.cwd,
            env=env,
            stdin=None,
            capture_output=True,
            text=True,
            timeout=args.timeout,
            preexec_fn=limits(args.timeout, args.memory_mb),
            check=False,
        )
        result = {
            "command": command,
            "cwd": str(args.cwd),
            "profile": args.profile,
            "network": "allowed" if args.allow_network else "disabled-by-policy",
            "exit_code": completed.returncode,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "isolation_note": "resource limits applied; network isolation requires a VM/container",
        }
    except subprocess.TimeoutExpired as exc:
        result = {
            "command": command,
            "cwd": str(args.cwd),
            "profile": args.profile,
            "network": "allowed" if args.allow_network else "disabled-by-policy",
            "exit_code": None,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
            "isolation_note": "resource limits applied; network isolation requires a VM/container",
        }

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("exit_code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
