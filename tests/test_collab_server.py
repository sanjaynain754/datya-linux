#!/usr/bin/env python3
import hashlib, hmac, http.client, json, os, socket, ssl, struct, subprocess, tempfile, time, unittest
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
        self.log = Path(self.tmp.name) / f"events-{time.time_ns()}.log"
        env = {**os.environ, "DATYA_COLLAB_SECRET":self.secret, "DATYA_TLS_CERT":str(self.cert), "DATYA_TLS_KEY":str(self.key), "DATYA_COLLAB_PORT":str(self.port), "DATYA_SCOPE":"127.0.0.1", "DATYA_SESSION_TTL":"60", "DATYA_EVENT_LOG":str(self.log)}
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
    def ws_connect(self, user):
        raw = socket.create_connection(("127.0.0.1", self.port), timeout=2); ctx = ssl._create_unverified_context(); conn = ctx.wrap_socket(raw, server_hostname="localhost")
        key = "dGhlIHNhbXBsZSBub25jZQ=="; request = f"GET /sessions/current?token={self.token(user)} HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        conn.sendall(request.encode()); response = b""
        while b"\r\n\r\n" not in response: response += conn.recv(1)
        return conn, response
    @staticmethod
    def read_ws_frame(conn):
        head = conn.recv(2); length = head[1] & 127
        if length == 126: length = struct.unpack("!H", conn.recv(2))[0]
        elif length == 127: length = struct.unpack("!Q", conn.recv(8))[0]
        data = b""
        while len(data) < length: data += conn.recv(length - len(data))
        return data[:length]
    @staticmethod
    def masked_frame(text):
        data = text.encode(); mask = b"abcd"; head = bytes([0x81, 0x80 | len(data)])
        return head + mask + bytes(value ^ mask[index % 4] for index, value in enumerate(data))
    @staticmethod
    def masked_control(opcode, payload=b""):
        mask = b"wxyz"; return bytes([0x80 | opcode, 0x80 | len(payload)]) + mask + bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
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
    def test_websocket_handshake_and_masked_frames(self):
        conn, response = self.ws_connect("ws-user"); self.assertIn(b"101 Switching Protocols", response); first = json.loads(self.read_ws_frame(conn)); self.assertEqual(first["event"], "joined")
        conn.sendall(self.masked_control(0x9, b"health")); self.assertEqual(self.read_ws_frame(conn), b"health"); conn.close()
    def test_websocket_malformed_json_does_not_break_connection(self):
        conn, response = self.ws_connect("bad-frame"); self.assertIn(b"101 Switching Protocols", response); self.read_ws_frame(conn)
        conn.sendall(self.masked_frame("not-json")); self.assertEqual(struct.unpack("!H", self.read_ws_frame(conn)[:2])[0], 1007); conn.close()
    def test_remove_revokes_participant_tokens(self):
        self.assertEqual(self.join("owner")[0], 200); self.assertEqual(self.join("target")[0], 200)
        status, _ = self.request("POST", "/sessions/current/commands", self.token("owner"), {"action":"remove", "participant_id":"target"}); self.assertEqual(status, 200)
        self.assertEqual(self.request("GET", "/health", self.token("target"))[0], 401)
    def test_persistent_event_log_is_hash_chained(self):
        self.assertEqual(self.join("logged")[0], 200); lines = self.log.read_text().splitlines(); self.assertGreaterEqual(len(lines), 1); previous = "0" * 64
        for sequence, line in enumerate(lines):
            fields = line.split("\t"); self.assertEqual(len(fields), 6); self.assertEqual(fields[0], str(sequence)); self.assertEqual(fields[4], previous); self.assertEqual(hashlib.sha256("\t".join(fields[:5]).encode()).hexdigest(), fields[5]); previous = fields[5]

if __name__ == "__main__": unittest.main()
