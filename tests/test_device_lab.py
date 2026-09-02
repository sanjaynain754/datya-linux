import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "datya-device-lab.py"


class DeviceLabTests(unittest.TestCase):
    def test_json_report_is_machine_readable(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--json"], capture_output=True, text=True, check=True)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema_version"], "datya.device-lab.v1")
        self.assertIn("readiness", report)
        self.assertIn("kernel_module_build", report["readiness"])

    def test_report_can_be_written_without_mutating_host(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "lab.json"
            result = subprocess.run([sys.executable, str(SCRIPT), "--output", str(target)], capture_output=True, text=True, check=True)
            self.assertTrue(target.exists())
            self.assertEqual(json.loads(target.read_text())["schema_version"], "datya.device-lab.v1")
            self.assertIn("safe_to_claim_full_lab_build", result.stdout)


if __name__ == "__main__":
    unittest.main()
