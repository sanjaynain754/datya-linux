#!/usr/bin/env python3
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "datya-tool-catalog.py"


class ToolCatalogTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), *args], cwd=ROOT, capture_output=True, text=True)

    def test_list_has_curated_packs(self):
        result = self.run_cli("--list")
        self.assertEqual(result.returncode, 0)
        self.assertIn("observe", result.stdout)
        self.assertIn("security-lab", result.stdout)

    def test_search_returns_json(self):
        result = self.run_cli("--search", "network", "--json")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertIn("network-lab", payload)

    def test_unknown_pack_is_an_error(self):
        result = self.run_cli("--pack", "missing")
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
