#!/usr/bin/env python3
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "tools" / "datya-install-pack.py"


class InstallPackTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(INSTALLER), *args], cwd=ROOT, capture_output=True, text=True)

    def test_unverified_pack_is_blocked(self):
        result = self.run_cli("--pack", "observe")
        self.assertEqual(result.returncode, 1)
        self.assertIn("verification blocked", result.stderr)
        self.assertIn("absent from packages/manifest.json", result.stderr)

    def test_unknown_pack_is_rejected(self):
        result = self.run_cli("--pack", "unknown")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown pack", result.stderr)

    def test_install_requires_explicit_confirmation(self):
        result = self.run_cli("--pack", "observe", "--install")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--install --yes", result.stderr)

    def test_all_packs_resolve_to_json_plan(self):
        result = self.run_cli("--all")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["mode"], "dry-run")
        self.assertGreater(payload["count"], 0)


if __name__ == "__main__":
    unittest.main()
