#!/usr/bin/env python3
"""List and search Datya's curated, profile-aware tool packs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "profiles" / "tool-packs.toml"


def load_catalog() -> dict:
    with CATALOG.open("rb") as stream:
        return tomllib.load(stream)


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover Datya Linux curated security tool packs")
    parser.add_argument("--list", action="store_true", help="list all packs")
    parser.add_argument("--pack", help="show one pack and its tools")
    parser.add_argument("--search", help="search pack names, summaries, and tools")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()
    if not (args.list or args.pack or args.search):
        parser.error("choose --list, --pack, or --search")

    packs = load_catalog().get("pack", {})
    if args.pack:
        selected = {args.pack: packs[args.pack]} if args.pack in packs else {}
    elif args.search:
        query = args.search.casefold()
        selected = {
            name: pack for name, pack in packs.items()
            if query in name.casefold()
            or query in str(pack.get("summary", "")).casefold()
            or any(query in tool.casefold() for tool in pack.get("tools", []))
        }
    else:
        selected = packs

    if args.json:
        print(json.dumps(selected, indent=2, sort_keys=True))
    else:
        for name, pack in selected.items():
            print(f"{name} [{pack['profile']}] - {pack['summary']}")
            print("  " + ", ".join(pack.get("tools", [])))
    if args.pack and not selected:
        print(f"unknown pack: {args.pack}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
