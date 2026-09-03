import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_collector():
    path = ROOT / "tools/datya-guardian-collector.py"
    spec = importlib.util.spec_from_file_location("datya_guardian_collector", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GuardianCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collector = load_collector()

    def test_parses_exec_event(self):
        event = self.collector.parse_line(
            'datya_guardian event=exec pid=42 uid=1000 path="/usr/bin/nmap"\n'
        )
        self.assertEqual(event["schema"], "datya.guardian.event.v1")
        self.assertEqual(event["event"], "exec")
        self.assertEqual(event["fields"]["pid"], 42)
        self.assertEqual(event["fields"]["path"], "/usr/bin/nmap")

    def test_parses_socket_event(self):
        event = self.collector.parse_line(
            "datya_guardian event=socket family=10 pid=9 proto=6 old=1 new=2\n"
        )
        self.assertEqual(event["event"], "socket")
        self.assertEqual(event["fields"]["family"], 10)
        self.assertEqual(event["fields"]["new"], 2)

    def test_ignores_unrelated_lines(self):
        self.assertIsNone(self.collector.parse_line("random kernel line\n"))

    def test_output_is_json_serializable(self):
        event = self.collector.parse_line("datya_guardian event=exec pid=1 uid=0 path=/bin/true")
        self.assertEqual(json.loads(json.dumps(event))["source"], "tracefs-or-ebpf")


if __name__ == "__main__":
    unittest.main()
