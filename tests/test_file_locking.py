#!/usr/bin/env python3
import importlib.util, multiprocessing, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("datya_collab_server", ROOT / "tools/datya-collab-server.py")
server = importlib.util.module_from_spec(spec); spec.loader.exec_module(server)

def append_worker(path, worker):
    log = server.PersistentEventLog(path)
    for index in range(8):
        log.append({"type":"session.event", "sequence":0, "timestamp":index, "actor_id":f"w{worker}", "event":"notice", "command_id":None, "message":"concurrent"})

def revoke_worker(path, worker): server.Revocations(path).add(f"user-{worker}")

class FileLockingTests(unittest.TestCase):
    def test_event_log_multi_process_append_is_contiguous(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "events.log")
            processes = [multiprocessing.Process(target=append_worker, args=(path, worker)) for worker in range(6)]
            for process in processes: process.start()
            for process in processes: process.join(timeout=10); self.assertEqual(process.exitcode, 0)
            log = server.PersistentEventLog(path); self.assertEqual(log.sequence, 48); self.assertEqual(len(log.events), 48)
    def test_revocation_file_multi_process_append_is_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "revoked")
            processes = [multiprocessing.Process(target=revoke_worker, args=(path, worker)) for worker in range(12)]
            for process in processes: process.start()
            for process in processes: process.join(timeout=10); self.assertEqual(process.exitcode, 0)
            revoked = server.Revocations(path); self.assertEqual(revoked.users, {f"user-{worker}" for worker in range(12)})

if __name__ == "__main__": unittest.main()
