#!/usr/bin/env python3
"""Run commands with explicit Datya sandbox profiles.

Safe/project profiles require bubblewrap. Power-user intentionally runs the
command without an added sandbox, but still prints an explicit audit warning.
This is a reference launcher, not a claim of perfect isolation.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROFILES = {"safe", "project", "lab", "power-user"}


def build_command(profile: str, command: list[str]) -> list[str]:
    if profile == "power-user":
        return command
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise RuntimeError(f"profile '{profile}' requires bubblewrap; refusing unsafe fallback")
    root = str(Path.cwd())
    args = [bwrap, "--die-with-parent", "--new-session", "--unshare-pid", "--unshare-uts", "--unshare-ipc", "--ro-bind", "/usr", "/usr", "--ro-bind", "/bin", "/bin", "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--bind", root, root, "--chdir", root]
    if profile in {"safe", "project"}:
        args += ["--unshare-net"]
    args += ["--"] + command
    return args


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="datya-sandbox")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="safe")
    parser.add_argument("--", dest="separator", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command and args.command[0] == "--" else args.command
    if not command:
        parser.error("a command is required after --")
    try:
        argv = build_command(args.profile, command)
    except RuntimeError as exc:
        print(f"datya-sandbox: {exc}", file=sys.stderr)
        return 126
    if args.profile == "power-user":
        print("datya-sandbox: POWER-USER mode; no added isolation; user control is explicit", file=sys.stderr)
    else:
        print(f"datya-sandbox: profile={args.profile}; isolation and limits are active", file=sys.stderr)
    env = os.environ.copy()
    env["DATYA_SANDBOX_PROFILE"] = args.profile
    return subprocess.run(argv, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
