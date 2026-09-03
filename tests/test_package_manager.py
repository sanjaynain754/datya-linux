import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_tool(name):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackageManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = load_tool("datya-pkg")
        cls.sandbox = load_tool("datya-sandbox")

    def test_nmap_plan_is_non_executing_and_verified(self):
        plan = self.pkg.install_plan("nmap")
        self.assertEqual(plan["schema"], "datya.transaction.plan.v1")
        self.assertFalse(plan["auto_execute"])
        self.assertTrue(plan["requires_confirmation"])
        self.assertTrue(plan["verification"]["passed"])
        self.assertTrue(plan["profile_opt_in_required"])

    def test_remove_requires_typed_double_confirmation(self):
        plan = self.pkg.remove_plan("nmap", purge=True)
        self.assertTrue(plan["double_confirmation"])
        self.assertEqual(plan["typed_acknowledgement"], "nmap")
        self.assertFalse(plan["auto_execute"])
        self.assertEqual(plan["operation"], "purge")

    def test_unknown_package_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.pkg.find_package("not-a-real-package")

    def test_cli_outputs_json(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/datya-pkg.py"), "info", "nmap"], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(data["name"], "nmap")
        self.assertEqual(data["network_behavior"], "network-capable")

    def test_safe_sandbox_fails_closed_without_bwrap(self):
        if self.sandbox.shutil.which("bwrap"):
            self.skipTest("bubblewrap is installed in this environment")
        with self.assertRaises(RuntimeError):
            self.sandbox.build_command("safe", ["true"])

    def test_power_user_is_explicitly_unrestricted(self):
        self.assertEqual(self.sandbox.build_command("power-user", ["true"]), ["true"])

    def test_sandbox_policy_contains_limits_when_available(self):
        if not self.sandbox.shutil.which("bwrap"):
            self.skipTest("bubblewrap is not installed in this environment")
        command = self.sandbox.build_command("safe", ["true"])
        self.assertIn("--cap-drop", command)
        self.assertIn("--rlimit-nproc", command)
        self.assertIn("--rlimit-fsize", command)


if __name__ == "__main__":
    unittest.main()

    def test_record_only_transaction_and_rollback(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            plan = self.pkg.install_plan("nmap")
            record = self.pkg.commit_record(plan, state_path, "nmap")
            self.assertEqual(record["backend"], "record-only")
            self.assertIn("nmap", self.pkg.load_state(state_path)["installed"])
            self.pkg.rollback(state_path, record["id"])
            self.assertNotIn("nmap", self.pkg.load_state(state_path)["installed"])

    def test_wrong_acknowledgement_cannot_commit(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit):
                self.pkg.commit_record(self.pkg.remove_plan("nmap", False), Path(directory) / "state.json", "not-nmap")
