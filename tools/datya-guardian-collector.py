#!/usr/bin/env python3
"""Local Guardian collector for tracefs/eBPF-compatible event streams.

The collector never opens a network socket and never executes a command. It
accepts trace lines from stdin by default or reads tracefs trace_pipe when
explicitly requested. A future eBPF producer can emit the same text contract.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EVENT = re.compile(r"datya_guardian event=(?P<kind>exec|socket)\s+(?P<body>.*)")
FIELD = re.compile(r"(?P<key>[a-z_]+)=(?P<value>\"[^\"]*\"|\S+)")
TRACE_PIPE = Path("/sys/kernel/tracing/trace_pipe")


def parse_line(line: str) -> dict | None:
    match = EVENT.search(line)
    if not match:
        return None
    fields: dict[str, str | int] = {}
    for field in FIELD.finditer(match.group("body")):
        value = field.group("value").strip('"')
        fields[field.group("key")] = int(value) if value.lstrip("-").isdigit() else value
    return {
        "schema": "datya.guardian.event.v1",
        "source": "tracefs-or-ebpf",
        "event": match.group("kind"),
        "fields": fields,
    }


def stream(source: str):
    if source == "stdin":
        yield from sys.stdin
        return
    try:
        with TRACE_PIPE.open("r", encoding="utf-8", errors="replace") as handle:
            yield from handle
    except OSError as exc:
        raise SystemExit(f"guardian-collector: cannot read {TRACE_PIPE}: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="datya-guardian-collector")
    parser.add_argument("--source", choices=("stdin", "tracefs"), default="stdin")
    parser.add_argument("--pretty", action="store_true", help="indent JSON for inspection")
    args = parser.parse_args(argv)
    for line in stream(args.source):
        event = parse_line(line)
        if event is not None:
            print(json.dumps(event, sort_keys=True, indent=2 if args.pretty else None), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
