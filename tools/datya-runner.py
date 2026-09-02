#!/usr/bin/env python3
"""Datya local command runner with explicit safety profiles.

The safe/project profiles require bubblewrap for real network and filesystem
isolation. The runner fails closed when the requested isolation primitive is not
available instead of claiming that an environment variable disabled networking.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

MAX_TIMEOUT_SECONDS = 3600
MAX_MEMORY_MB = 16 * 1024
MAX_OUTPUT_MB = 64


def limits(cpu_seconds: int, memory_mb: int):
    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        memory = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_NPROC, (128, 128))
        resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))

    return apply


def build_command(command: list[str], cwd: Path, profile: str, allow_network: bool) -> tuple[list[str], str]:
    """Return the actual command and a truthful isolation description."""
    if profile == "lab":
        return command, "resource limits only; lab isolation requires an external VM/container"

    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise RuntimeError("bubblewrap is required for safe/project profiles; install bwrap or use --profile lab")

    wrapped = [
        bwrap,
        "--die-with-parent",
        "--new-session",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/bin", "/bin",
        "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64",
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--bind", str(cwd), "/workspace",
        "--chdir", "/workspace",
        "--setenv", "HOME", "/workspace",
        "--setenv", "PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    ]
    if not allow_network:
        wrapped.append("--unshare-net")
    wrapped.extend(["--"] + command)
    network = "allowed inside filesystem sandbox" if allow_network else "disabled by network namespace"
    return wrapped, network


def as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def trim_output(value: str | bytes | None, limit: int) -> tuple[str, bool]:
    text = as_text(value)
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return text, False
    return encoded[:limit].decode("utf-8", errors="ignore") + "\n[output truncated by datya-runner]\n", True


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Datya project command with an explicit profile")
    parser.add_argument("--profile", choices=("safe", "project", "lab"), default="safe")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--memory-mb", type=int, default=1024)
    parser.add_argument("--output-mb", type=int, default=8)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--", dest="separator", nargs="?")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.command:
        parser.error("provide a command after --")
    if args.timeout < 1 or args.timeout > MAX_TIMEOUT_SECONDS:
        parser.error(f"timeout must be between 1 and {MAX_TIMEOUT_SECONDS} seconds")
    if args.memory_mb < 64 or args.memory_mb > MAX_MEMORY_MB:
        parser.error(f"memory must be between 64 and {MAX_MEMORY_MB} MB")
    if args.output_mb < 1 or args.output_mb > MAX_OUTPUT_MB:
        parser.error(f"output must be between 1 and {MAX_OUTPUT_MB} MB")
    if args.profile == "safe" and args.allow_network:
        parser.error("safe profile cannot allow network; use project profile explicitly")
    cwd = args.cwd.resolve()
    if not cwd.is_dir():
        parser.error(f"working directory does not exist: {cwd}")

    command = args.command[1:] if args.command and args.command[0] == "--" else args.command
    env = {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME": str(cwd),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "DATYA_PROFILE": args.profile,
        "DATYA_NETWORK": "allowed" if args.allow_network else "disabled",
    }
    if args.profile == "lab":
        print("warning: lab profile has resource limits only; use a disposable VM/container", file=sys.stderr)

    try:
        actual_command, isolation = build_command(command, cwd, args.profile, args.allow_network)
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc), "profile": args.profile}, ensure_ascii=False))
        return 2

    started = time.monotonic()
    limit = args.output_mb * 1024 * 1024
    try:
        process = subprocess.Popen(
            actual_command,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=limits(args.timeout, args.memory_mb),
            start_new_session=True,
        )
    except OSError as exc:
        print(json.dumps({"error": f"cannot start command: {exc}", "command": command}, ensure_ascii=False))
        return 127

    try:
        raw_stdout, raw_stderr = process.communicate(timeout=args.timeout)
        stdout, stdout_truncated = trim_output(raw_stdout, limit)
        stderr, stderr_truncated = trim_output(raw_stderr, limit)
        result = {
            "command": command,
            "cwd": str(cwd),
            "profile": args.profile,
            "network": "allowed" if args.allow_network else "disabled-by-policy",
            "exit_code": process.returncode,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": stdout,
            "stderr": stderr,
            "output_truncated": stdout_truncated or stderr_truncated,
            "isolation_note": isolation,
        }
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        raw_stdout, raw_stderr = process.communicate()
        stdout, _ = trim_output(raw_stdout or exc.stdout, limit)
        stderr, _ = trim_output(raw_stderr or exc.stderr, limit)
        result = {
            "command": command,
            "cwd": str(cwd),
            "profile": args.profile,
            "network": "allowed" if args.allow_network else "disabled-by-policy",
            "exit_code": None,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": True,
            "isolation_note": isolation,
        }

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("exit_code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
