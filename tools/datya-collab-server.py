#!/usr/bin/env python3
"""Datya collaboration transport reference server.

Prototype boundary: this server emits policy plans; it never executes shell commands.
Use TLS in every non-local deployment and provide DATYA_COLLAB_SECRET.
"""
from __future__ import annotations
import base64, fcntl, hashlib, hmac, json, os, secrets, socket, ssl, struct, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

MAX_USERS = 4
MAX_BODY_BYTES = 64 * 1024
MAX_COMMAND_ID = 128
MAX_RESULT_BYTES = 4096
MAX_TOKEN_BYTES = 512
SESSION_TTL = int(os.getenv("DATYA_SESSION_TTL", "28800"))
SECRET = os.environ.get("DATYA_COLLAB_SECRET", "")
SCOPE = {x for x in os.environ.get("DATYA_SCOPE", "127.0.0.1").split(",") if x}
PORT = int(os.getenv("DATYA_COLLAB_PORT", "9443"))
CERT = os.getenv("DATYA_TLS_CERT", "/etc/datya/tls/server.crt")
KEY = os.getenv("DATYA_TLS_KEY", "/etc/datya/tls/server.key")
EVENT_LOG = os.getenv("DATYA_EVENT_LOG", "")
REVOCATION_FILE = os.getenv("DATYA_REVOCATION_FILE", "")

class Revocations:
    def __init__(self, path):
        self.path = path; self.users = set(); self.lock = threading.RLock()
        self.lock_path = f"{path}.lock" if path else ""
        self._reload()
    def _reload(self):
        if not self.path: return
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH)
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as stream: self.users = {line.strip() for line in stream if line.strip()}
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)
    def add(self, user):
        with self.lock:
            if not self.path:
                self.users.add(user); return
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            lock_fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
                if os.path.exists(self.path):
                    with open(self.path, "r", encoding="utf-8") as stream: self.users = {line.strip() for line in stream if line.strip()}
                if user not in self.users:
                    fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                    try: os.write(fd, (user + "\n").encode()); os.fsync(fd)
                    finally: os.close(fd)
                    self.users.add(user)
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN); os.close(lock_fd)
    def contains(self, user):
        with self.lock:
            self._reload()
            return user in self.users

class PersistentEventLog:
    def __init__(self, path):
        self.path = path; self.lock_path = f"{path}.lock" if path else ""; self.previous = "0" * 64; self.sequence = 0; self.events = []
        if not path: return
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        lock_fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_SH)
            self._load()
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN); os.close(lock_fd)
    def _load(self):
        self.previous = "0" * 64; self.sequence = 0; self.events = []
        if not os.path.exists(self.path): return
        with open(self.path, "r", encoding="utf-8") as stream:
            for raw in stream:
                line = raw.rstrip("\n")
                fields = line.split("\t")
                if len(fields) != 6 or fields[0] != str(self.sequence) or fields[4] != self.previous or hashlib.sha256("\t".join(fields[:5]).encode()).hexdigest() != fields[5]:
                    raise ValueError("persistent event log hash chain is invalid")
                self.events.append(json.loads(fields[3]))
                self.previous = fields[5]; self.sequence += 1
    def append(self, event):
        if not self.path: return event["sequence"]
        lock_fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX); self._load()
            event["sequence"] = self.sequence
            payload = json.dumps(event, separators=(",", ":"), ensure_ascii=True).replace("\t", "\\t").replace("\n", "\\n")
            material = f"{self.sequence}\t{event['timestamp']}\tcollaboration\t{payload}\t{self.previous}"
            digest = hashlib.sha256(material.encode()).hexdigest(); record = f"{material}\t{digest}\n"
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try: os.write(fd, record.encode()); os.fsync(fd)
            finally: os.close(fd)
            self.previous = digest; self.sequence += 1; self.events.append(event)
            return event["sequence"]
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN); os.close(lock_fd)

class Session:
    def __init__(self):
        self.lock = threading.RLock(); self.created = int(time.time()); self.events = []
        self.users = {}; self.commands = {}; self.clients = set(); self.revoked_tokens = set(); self.revocations = Revocations(REVOCATION_FILE); self.seq = 0; self.log = PersistentEventLog(EVENT_LOG)
        if EVENT_LOG and self.log.sequence: self.seq = self.log.sequence; self.events = list(self.log.events)
    def expired(self): return int(time.time()) >= self.created + SESSION_TTL
    def event(self, actor, name, command_id=None, message=""):
        with self.lock:
            item = {"type":"session.event", "sequence":self.seq, "timestamp":int(time.time()), "actor_id":actor, "event":name, "command_id":command_id, "message":message[:512]}
            item["sequence"] = self.log.append(item); self.seq = item["sequence"] + 1; self.events.append(item); clients = list(self.clients)
        payload = json.dumps(item, separators=(",", ":"))
        for client in clients:
            try: client.send_event(payload)
            except Exception: self.clients.discard(client)
        return item
    def add(self, client):
        with self.lock:
            if self.expired(): raise ValueError("session expired")
            user = client.user
            if user in self.users and self.users[user].get("removed"): raise ValueError("participant removed")
            if user in self.users: self.users[user]["connected"] = True
            elif len(self.users) >= MAX_USERS: raise ValueError("session full")
            else: self.users[user] = {"connected": True, "joined": int(time.time())}
            self.clients.add(client)
        self.event(user, "reconnected" if user in self.users and self.users[user]["joined"] != int(time.time()) else "joined", message="participant connected")
    def auth(self, token):
        if not SECRET: return None
        with self.lock:
            if token in self.revoked_tokens: return None
        try: user, mac = token.split(".", 1)
        except ValueError: return None
        try: user, expiry, mac = token.split(".", 2); expiry = int(expiry)
        except (ValueError, TypeError): return None
        material = f"{user}.{expiry}".encode()
        expected = hmac.new(SECRET.encode(), material, hashlib.sha256).hexdigest()
        return user if expiry >= int(time.time()) and not self.revocations.contains(user) and hmac.compare_digest(mac, expected) and user and len(user) <= 128 else None
    def revoke_user(self, actor, target):
        with self.lock:
            if target not in self.users: raise ValueError("unknown participant")
            self.revocations.add(target); self.users[target]["connected"] = False; self.users[target]["removed"] = True
            clients = [client for client in self.clients if getattr(client, "user", None) == target]
        for client in clients:
            try: client.close(1008, "participant revoked")
            except Exception: pass
        self.event(actor, "removed", message=f"participant {target} removed and tokens revoked")
    def active(self, user):
        with self.lock:
            return user in self.users and self.users[user].get("connected", False) and not self.users[user].get("removed", False)

SESSION = Session()

def ws_accept(key): return base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
def ws_frame(text, opcode=0x1):
    data = text.encode() if isinstance(text, str) else text; n = len(data)
    if n >= 65536: raise ValueError("frame too large")
    head = bytes([0x80 | opcode, n]) if n < 126 else bytes([0x80 | opcode,126]) + struct.pack("!H",n)
    return head + data

def read_frame(rfile):
    head = rfile.read(2)
    if len(head) != 2: return (0, None)
    first, second = head; opcode = first & 0x0f; length = second & 127; masked = bool(second & 128)
    if first & 0x70 or not masked: raise ValueError("protocol error: RSV or client masking")
    if opcode >= 8 and (not (first & 0x80) or length > 125): raise ValueError("protocol error: invalid control frame")
    if length == 126: length = struct.unpack("!H", rfile.read(2))[0]
    elif length == 127: length = struct.unpack("!Q", rfile.read(8))[0]
    if length > 1024 * 1024: raise ValueError("message too large")
    mask = rfile.read(4); data = bytearray(rfile.read(length))
    if len(mask) != 4 or len(data) != length: return (0, None)
    if masked:
        for i in range(len(data)): data[i] ^= mask[i % 4]
    return opcode, bytes(data)

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def token_user(self):
        value = self.headers.get("Authorization", "")
        if value.startswith("Bearer "):
            token = value[7:]
            return SESSION.auth(token) if len(token) <= MAX_TOKEN_BYTES else None
        # Query tokens are retained only for the WebSocket handshake because
        # browsers cannot set Authorization during a native WebSocket upgrade.
        if self.headers.get("Upgrade", "").lower() != "websocket":
            return None
        query = parse_qs(urlparse(self.path).query)
        token = query.get("token", [""])[0]
        return SESSION.auth(token) if len(token) <= MAX_TOKEN_BYTES else None
    def send_json(self, code, data):
        raw = json.dumps(data).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.headers.get("Upgrade", "").lower() == "websocket":
            return self.do_UPGRADE()
        user = self.token_user()
        if not user: return self.send_json(401, {"error":"authentication required"})
        path = urlparse(self.path).path
        if path == "/health": return self.send_json(200, {"ok":True,"expired":SESSION.expired(),"participants":len(SESSION.users)})
        if path == "/sessions/current/events":
            if not SESSION.active(user): return self.send_json(403, {"error":"join the session first"})
            self.send_response(200); self.send_header("Content-Type","text/event-stream"); self.send_header("Cache-Control","no-cache"); self.send_header("Connection","keep-alive"); self.end_headers()
            with SESSION.lock: history = list(SESSION.events); SESSION.clients.add(SSEClient(self.wfile, user))
            try:
                for item in history[-256:]: self.wfile.write((f"id: {item['sequence']}\nevent: session.event\ndata: {json.dumps(item)}\n\n").encode()); self.wfile.flush()
                while not SESSION.expired(): self.wfile.write(b": heartbeat\n\n"); self.wfile.flush(); time.sleep(15)
            except (BrokenPipeError, ConnectionResetError): pass
            return
        self.send_json(404, {"error":"not found"})
    def do_POST(self):
        user = self.token_user()
        if not user: return self.send_json(401, {"error":"authentication required"})
        if urlparse(self.path).path != "/sessions/current/commands": return self.send_json(404,{"error":"not found"})
        if SESSION.expired(): return self.send_json(410,{"error":"session expired"})
        try:
            content_length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            return self.send_json(400, {"error": "invalid content length"})
        if content_length < 0 or content_length > MAX_BODY_BYTES:
            return self.send_json(413, {"error": "request body too large"})
        try:
            body = json.loads(self.rfile.read(content_length))
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "invalid json"})
        if not isinstance(body, dict):
            return self.send_json(400, {"error": "json object required"})
        action, cid = body.get("action"), body.get("command_id")
        if cid is not None and (not isinstance(cid, str) or len(cid) > MAX_COMMAND_ID or "\n" in cid or "\r" in cid):
            return self.send_json(400, {"error": "invalid command_id"})
        if action == "join":
            try: SESSION.add(HTTPClient(user))
            except ValueError as exc: return self.send_json(409,{"error":str(exc)})
            return self.send_json(200,{"ok":True,"participant_id":user,"max_participants":MAX_USERS})
        if not SESSION.active(user): return self.send_json(403,{"error":"join the session first"})
        if action == "disconnect":
            if user in SESSION.users: SESSION.users[user]["connected"] = False
            SESSION.event(user, "left", message="participant disconnected")
            return self.send_json(200, {"status":"disconnected"})
        if action == "remove":
            target = str(body.get("participant_id", ""))
            try: SESSION.revoke_user(user, target)
            except ValueError as exc: return self.send_json(404, {"error":str(exc)})
            return self.send_json(200, {"status":"removed", "participant_id":target})
        if action == "propose":
            command, target = body.get("command", ""), body.get("target", "")
            if not isinstance(command, str) or not isinstance(target, str) or not cid or len(command) > 512 or "\n" in command or "\r" in command or target not in SCOPE:
                return self.send_json(403, {"error": "invalid command or target outside explicit scope"})
            with SESSION.lock:
                if cid in SESSION.commands:
                    return self.send_json(409, {"error": "command_id already exists"})
                SESSION.commands[cid] = {"proposer": user, "command": command, "target": target, "approvals": set()}
            SESSION.event(user, "command.proposed", cid, f"dry-run proposal: {command} {target}")
            return self.send_json(202, {"status": "proposed"})
        with SESSION.lock:
            request = SESSION.commands.get(cid)
        if request is None: return self.send_json(404,{"error":"unknown command"})
        if action == "approve":
            with SESSION.lock:
                request["approvals"].add(user)
            SESSION.event(user,"command.approved",cid,"approval recorded"); return self.send_json(200,{"status":"approved"})
        if action == "start":
            if user != request["proposer"] and user not in request["approvals"]: return self.send_json(403,{"error":"proposer or approver required"})
            SESSION.event(user,"command.started",cid,"dry-run plan emitted; no command executed"); return self.send_json(200,{"status":"planned","command":request["command"],"target":request["target"]})
        if action == "finish":
            result = body.get("result", "")
            if not isinstance(result, str) or len(result.encode("utf-8")) > MAX_RESULT_BYTES:
                return self.send_json(413, {"error": "result too large"})
            SESSION.event(user,"command.finished",cid,result); return self.send_json(200,{"status":"finished"})
        return self.send_json(400,{"error":"unsupported action"})
    def do_UPGRADE(self):
        user = self.token_user()
        if not user or self.headers.get("Upgrade","").lower() != "websocket": return self.send_json(401,{"error":"websocket authentication required"})
        key = self.headers.get("Sec-WebSocket-Key");
        if not key: return self.send_json(400,{"error":"websocket key required"})
        client = WSClient(self.connection, self.rfile, self.wfile, user)
        self.send_response(101); self.send_header("Upgrade","websocket"); self.send_header("Connection","Upgrade"); self.send_header("Sec-WebSocket-Accept",ws_accept(key)); self.end_headers()
        try: SESSION.add(client)
        except ValueError:
            self.connection.close()
            return
        try:
            while not SESSION.expired():
                opcode, raw = read_frame(self.rfile)
                if opcode == 0: break
                if opcode == 0x8:
                    code = raw[:2] if len(raw) >= 2 else struct.pack("!H", 1000)
                    client.send_control(0x8, code); break
                if opcode == 0x9: client.send_control(0xA, raw); continue
                if opcode != 0x1: client.close(1003, "text frames required"); break
                try: msg=json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError): client.close(1007, "invalid text"); break
                if msg.get("action") == "ping": client.send_control(0xA, b"ping")
        except (ValueError, BrokenPipeError, ConnectionResetError, OSError):
            try: client.close(1002, "protocol error")
            except Exception: pass
        finally: SESSION.clients.discard(client)
    def log_message(self, *_): pass

class HTTPClient:
    def __init__(self,user): self.user=user
    def send_event(self,_): pass
class SSEClient:
    def __init__(self,wfile,user): self.wfile=wfile; self.user=user
    def send_event(self,payload): self.wfile.write((f"id: {json.loads(payload)['sequence']}\nevent: session.event\ndata: {payload}\n\n").encode()); self.wfile.flush()
class WSClient:
    def __init__(self,conn,rfile,wfile,user): self.conn=conn; self.rfile=rfile; self.wfile=wfile; self.user=user
    def send_event(self,payload): self.wfile.write(ws_frame(payload)); self.wfile.flush()
    def send_control(self, opcode, payload): self.wfile.write(ws_frame(payload, opcode)); self.wfile.flush()
    def close(self, code=1000, reason=""):
        data = struct.pack("!H", code) + reason.encode()[:123]
        self.send_control(0x8, data)
        try: self.conn.shutdown(socket.SHUT_RDWR)
        except OSError: pass

def main():
    if not SECRET: raise SystemExit("DATYA_COLLAB_SECRET is required")
    server = ThreadingHTTPServer((os.getenv("DATYA_COLLAB_BIND","127.0.0.1"), PORT), Handler)
    if not (os.path.exists(CERT) and os.path.exists(KEY)): raise SystemExit(f"TLS certificate/key missing: {CERT} / {KEY}")
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.minimum_version=ssl.TLSVersion.TLSv1_3; context.load_cert_chain(CERT,KEY); server.socket=context.wrap_socket(server.socket,server_side=True)
    print(f"Datya collaboration server listening on TLS port {PORT}", flush=True); server.serve_forever()
if __name__ == "__main__": main()
