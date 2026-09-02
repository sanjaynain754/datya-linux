#!/usr/bin/env python3
"""Datya collaboration transport reference server.

Prototype boundary: this server emits policy plans; it never executes shell commands.
Use TLS in every non-local deployment and provide DATYA_COLLAB_SECRET.
"""
from __future__ import annotations
import base64, hashlib, hmac, json, os, secrets, ssl, struct, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

MAX_USERS = 4
SESSION_TTL = int(os.getenv("DATYA_SESSION_TTL", "28800"))
SECRET = os.environ.get("DATYA_COLLAB_SECRET", "")
SCOPE = {x for x in os.environ.get("DATYA_SCOPE", "127.0.0.1").split(",") if x}
PORT = int(os.getenv("DATYA_COLLAB_PORT", "9443"))
CERT = os.getenv("DATYA_TLS_CERT", "/etc/datya/tls/server.crt")
KEY = os.getenv("DATYA_TLS_KEY", "/etc/datya/tls/server.key")
EVENT_LOG = os.getenv("DATYA_EVENT_LOG", "")

class PersistentEventLog:
    def __init__(self, path):
        self.path = path; self.previous = "0" * 64; self.sequence = 0; self.events = []
        if not path: return
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if not os.path.exists(path): return
        with open(path, "r", encoding="utf-8") as stream:
            for raw in stream:
                line = raw.rstrip("\n")
                fields = line.split("\t")
                if len(fields) != 6 or fields[0] != str(self.sequence) or fields[4] != self.previous or hashlib.sha256("\t".join(fields[:5]).encode()).hexdigest() != fields[5]:
                    raise ValueError("persistent event log hash chain is invalid")
                self.events.append(json.loads(fields[3]))
                self.previous = fields[5]; self.sequence += 1
    def append(self, event):
        if not self.path: return
        payload = json.dumps(event, separators=(",", ":"), ensure_ascii=True).replace("\t", "\\t").replace("\n", "\\n")
        material = f"{self.sequence}\t{event['timestamp']}\tcollaboration\t{payload}\t{self.previous}"
        digest = hashlib.sha256(material.encode()).hexdigest(); record = f"{material}\t{digest}\n"
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        fd = os.open(self.path, flags, 0o600)
        try:
            os.write(fd, record.encode()); os.fsync(fd)
        finally: os.close(fd)
        self.previous = digest; self.sequence += 1

class Session:
    def __init__(self):
        self.lock = threading.RLock(); self.created = int(time.time()); self.events = []
        self.users = {}; self.commands = {}; self.clients = set(); self.seq = 0; self.log = PersistentEventLog(EVENT_LOG)
        if EVENT_LOG and self.log.sequence: self.seq = self.log.sequence; self.events = list(self.log.events)
    def expired(self): return int(time.time()) >= self.created + SESSION_TTL
    def event(self, actor, name, command_id=None, message=""):
        with self.lock:
            item = {"type":"session.event", "sequence":self.seq, "timestamp":int(time.time()), "actor_id":actor, "event":name, "command_id":command_id, "message":message[:512]}
            self.log.append(item); self.seq += 1; self.events.append(item); clients = list(self.clients)
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
        try: user, mac = token.split(".", 1)
        except ValueError: return None
        try: user, expiry, mac = token.split(".", 2); expiry = int(expiry)
        except (ValueError, TypeError): return None
        material = f"{user}.{expiry}".encode()
        expected = hmac.new(SECRET.encode(), material, hashlib.sha256).hexdigest()
        return user if expiry >= int(time.time()) and hmac.compare_digest(mac, expected) and user and len(user) <= 128 else None
    def active(self, user):
        with self.lock:
            return user in self.users and self.users[user].get("connected", False) and not self.users[user].get("removed", False)

SESSION = Session()

def ws_accept(key): return base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
def ws_frame(text):
    data = text.encode(); n = len(data)
    head = bytes([0x81, n]) if n < 126 else bytes([0x81,126]) + struct.pack("!H",n)
    return head + data

def read_frame(rfile):
    head = rfile.read(2)
    if len(head) != 2: return None
    length = head[1] & 127; masked = bool(head[1] & 128)
    if length == 126: length = struct.unpack("!H", rfile.read(2))[0]
    elif length == 127: length = struct.unpack("!Q", rfile.read(8))[0]
    mask = rfile.read(4) if masked else b""; data = bytearray(rfile.read(length))
    if masked:
        for i in range(len(data)): data[i] ^= mask[i % 4]
    return bytes(data).decode("utf-8", "replace")

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def token_user(self):
        value = self.headers.get("Authorization", "")
        if value.startswith("Bearer "): return SESSION.auth(value[7:])
        query = parse_qs(urlparse(self.path).query)
        return SESSION.auth(query.get("token", [""])[0])
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
        try: body = json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))))
        except (ValueError, json.JSONDecodeError): return self.send_json(400,{"error":"invalid json"})
        action, cid = body.get("action"), body.get("command_id")
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
            if target not in SESSION.users: return self.send_json(404, {"error":"unknown participant"})
            SESSION.users[target]["connected"] = False; SESSION.users[target]["removed"] = True
            SESSION.event(user, "removed", message=f"participant {target} removed")
            return self.send_json(200, {"status":"removed", "participant_id":target})
        if action == "propose":
            command, target = str(body.get("command","")), str(body.get("target",""))
            if not cid or len(command)>512 or "\n" in command or target not in SCOPE: return self.send_json(403,{"error":"invalid command or target outside explicit scope"})
            SESSION.commands[cid] = {"proposer":user,"command":command,"target":target,"approvals":set()}; SESSION.event(user,"command.proposed",cid,f"dry-run proposal: {command} {target}"); return self.send_json(202,{"status":"proposed"})
        if cid not in SESSION.commands: return self.send_json(404,{"error":"unknown command"})
        request = SESSION.commands[cid]
        if action == "approve": request["approvals"].add(user); SESSION.event(user,"command.approved",cid,"approval recorded"); return self.send_json(200,{"status":"approved"})
        if action == "start":
            if user != request["proposer"] and user not in request["approvals"]: return self.send_json(403,{"error":"proposer or approver required"})
            SESSION.event(user,"command.started",cid,"dry-run plan emitted; no command executed"); return self.send_json(200,{"status":"planned","command":request["command"],"target":request["target"]})
        if action == "finish": SESSION.event(user,"command.finished",cid,str(body.get("result",""))); return self.send_json(200,{"status":"finished"})
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
                raw = read_frame(self.rfile)
                if not raw: break
                try: msg=json.loads(raw)
                except json.JSONDecodeError: continue
                if msg.get("action") == "ping": client.send_event(json.dumps({"type":"pong"}))
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

def main():
    if not SECRET: raise SystemExit("DATYA_COLLAB_SECRET is required")
    server = ThreadingHTTPServer((os.getenv("DATYA_COLLAB_BIND","127.0.0.1"), PORT), Handler)
    if not (os.path.exists(CERT) and os.path.exists(KEY)): raise SystemExit(f"TLS certificate/key missing: {CERT} / {KEY}")
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.minimum_version=ssl.TLSVersion.TLSv1_3; context.load_cert_chain(CERT,KEY); server.socket=context.wrap_socket(server.socket,server_side=True)
    print(f"Datya collaboration server listening on TLS port {PORT}", flush=True); server.serve_forever()
if __name__ == "__main__": main()
