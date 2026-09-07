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
        import importlib.util

        spec = importlib.util.spec_from_file_location("datya_install_pack", INSTALLER)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        names, errors = module.resolve(
            "unverified",
            False,
            {"unverified": {"tools": ["demo-tool"]}},
            {"demo-tool": {"name": "demo-tool", "verification_status": "pending", "sha256": "a" * 64, "architectures": ["amd64"], "repository": "https://example.invalid"}},
        )
        self.assertEqual(names, ["demo-tool"])
        self.assertTrue(any("verification_status" in error for error in errors))
        self.assertTrue(any("real SHA-256 checksum" in error for error in errors))

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
