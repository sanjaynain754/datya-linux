#!/usr/bin/env python3
"""Collect reproducible local performance baselines for Datya Linux."""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import time
from pathlib import Path


def memory_kib() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    return -1


def cpu_count() -> int:
    return os.cpu_count() or 1


def command_latency(command: list[str], repeats: int) -> dict:
    durations = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        durations.append((time.perf_counter_ns() - start) / 1_000_000)
        if result.returncode != 0:
            raise SystemExit(f"command failed: {' '.join(command)}")
    return {"command": command, "repeats": repeats, "min_ms": min(durations), "avg_ms": sum(durations) / len(durations), "max_ms": max(durations)}


def main() -> int:
    parser = argparse.ArgumentParser(prog="datya-benchmark")
    parser.add_argument("--command", nargs="+", default=["true"])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 1 or args.repeats > 100:
        parser.error("repeats must be between 1 and 100")
    result = {
        "schema": "datya.benchmark.v1",
        "platform": platform.platform(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "cpu_count": cpu_count(),
        "mem_available_kib_before": memory_kib(),
        "tool_launch": command_latency(args.command, args.repeats),
        "mem_available_kib_after": memory_kib(),
        "boot_time_source": "systemd-analyze unavailable in generic sandbox; collect on target image",
    }
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
