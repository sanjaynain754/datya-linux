#!/usr/bin/env python3
"""Browse Datya's source-controlled modular capability index."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "modules" / "index" / "catalog.json"


def load() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="datya-index")
    parser.add_argument("command", choices=("list", "search", "info"))
    parser.add_argument("query", nargs="?")
    args = parser.parse_args(argv)
    data = load()
    modules = data.get("modules", [])
    if args.command == "list":
        result = {"schema": data["schema"], "categories": data["categories"], "modules": modules}
    elif args.command == "search":
        query = (args.query or "").lower()
        result = [m for m in modules if query in json.dumps(m).lower()]
    else:
        if not args.query:
            parser.error("info requires a module id")
        matches = [m for m in modules if m.get("id") == args.query]
        if not matches:
            parser.error(f"unknown module: {args.query}")
        result = matches[0]
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
