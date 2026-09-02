#!/usr/bin/env python3
import hashlib, hmac, http.client, json, os, subprocess, tempfile, time, unittest, ssl
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tools" / "datya-collab-server.py"

class CollabServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.cert = Path(cls.tmp.name)/"cert.pem"; cls.key = Path(cls.tmp.name)/"key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(cls.key), "-out", str(cls.cert), "-subj", "/CN=localhost", "-days", "1"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.port = 19443; cls.secret = "integration-secret"
    def setUp(self):
        env = {**os.environ, "DATYA_COLLAB_SECRET":self.secret, "DATYA_TLS_CERT":str(self.cert), "DATYA_TLS_KEY":str(self.key), "DATYA_COLLAB_PORT":str(self.port), "DATYA_SCOPE":"127.0.0.1", "DATYA_SESSION_TTL":"60"}
        self.proc = subprocess.Popen(["python3", str(SERVER)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(60):
            try: self.request("GET", "/health", self.token("probe")); break
            except OSError: time.sleep(.05)
        else: raise RuntimeError("server did not start")
    def tearDown(self): self.proc.terminate(); self.proc.wait(timeout=3)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def token(self, user, expiry=None):
        expiry = expiry or int(time.time()) + 120
        mac = hmac.new(self.secret.encode(), f"{user}.{expiry}".encode(), hashlib.sha256).hexdigest()
        return f"{user}.{expiry}.{mac}"
    def request(self, method, path, token, body=None):
        context = ssl._create_unverified_context(); conn = http.client.HTTPSConnection("127.0.0.1", self.port, context=context, timeout=2)
        payload = json.dumps(body).encode() if body is not None else None
        conn.request(method, path, payload, {"Authorization":f"Bearer {token}", "Content-Type":"application/json"})
        response = conn.getresponse(); raw = response.read(); conn.close(); return response.status, json.loads(raw or b"{}")
    def join(self, user): return self.request("POST", "/sessions/current/commands", self.token(user), {"action":"join"})
    def test_invalid_token_rejected(self): self.assertEqual(self.request("GET", "/health", "bad.token")[0], 401)
    def test_four_users_and_fifth_rejected(self):
        for user in ["a","b","c","d"]: self.assertEqual(self.join(user)[0], 200)
        self.assertEqual(self.join("e")[0], 409)
    def test_scope_and_command_lifecycle(self):
        self.join("owner"); self.join("approver")
        base = lambda user, body: self.request("POST", "/sessions/current/commands", self.token(user), body)
        self.assertEqual(base("owner", {"action":"propose","command_id":"x","command":"socket-audit","target":"bad.example"})[0], 403)
        self.assertEqual(base("owner", {"action":"propose","command_id":"x","command":"socket-audit","target":"127.0.0.1"})[0], 202)
        self.assertEqual(base("approver", {"action":"approve","command_id":"x"})[0], 200)
        self.assertEqual(base("approver", {"action":"start","command_id":"x"})[0], 200)
    def test_expired_token_rejected(self): self.assertEqual(self.request("GET", "/health", self.token("late", int(time.time())-1))[0], 401)
    def test_sse_requires_join(self): self.assertEqual(self.request("GET", "/sessions/current/events", self.token("not-joined"))[0], 403)

if __name__ == "__main__": unittest.main()
