#!/usr/bin/env python3
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "datya-runner.py"


class RunnerTests(unittest.TestCase):
    def run_runner(self, *args):
        return subprocess.run(
            [sys.executable, str(RUNNER), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_lab_profile_runs_command_with_json_result(self):
        result = self.run_runner(
            "--profile", "lab", "--timeout", "3", "--", sys.executable, "-c", "print('ok')"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["stdout"], "ok\n")
        self.assertIn("resource limits only", payload["isolation_note"])

    def test_safe_profile_fails_closed_without_bubblewrap(self):
        result = self.run_runner("--profile", "safe", "--", "true")
        if result.returncode == 0:
            payload = json.loads(result.stdout)
            self.assertIn("disabled by network namespace", payload["isolation_note"])
        else:
            payload = json.loads(result.stdout)
            self.assertIn("bubblewrap is required", payload["error"])

    def test_timeout_returns_structured_result(self):
        result = self.run_runner(
            "--profile", "lab", "--timeout", "1", "--", sys.executable, "-c", "import time; time.sleep(3)"
        )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["timed_out"])
        self.assertIsNone(payload["exit_code"])

    def test_limits_are_bounded(self):
        result = self.run_runner("--profile", "lab", "--timeout", "3601", "--", "true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("timeout must be between", result.stderr)


if __name__ == "__main__":
    unittest.main()
