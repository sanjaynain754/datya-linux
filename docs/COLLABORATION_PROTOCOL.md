# Collaboration Transport Protocol

The session core is transport-neutral. A production implementation should expose two read paths—WebSocket for bidirectional commands and Server-Sent Events (SSE) for a simple read-only live feed—behind an authenticated LAN endpoint.

## Security contract

- Require TLS 1.3 where available; disable plaintext LAN listeners in production.
- Authenticate every participant before a session join using short-lived signed tokens or mutual TLS certificates.
- Bind each token to `session_id`, `participant_id`, role, expiry, and a nonce.
- Reject replayed nonces and expired tokens.
- Authorize every command against participant membership, session expiry, target scope, and tool policy.
- Redact secrets before broadcast; never publish private keys, access tokens, or unrestricted command output.
- Use monotonically increasing event sequences and client acknowledgements to detect gaps.
- Close sessions on expiry and require a fresh invitation for a new session.

## WebSocket messages

Client to server:

```json
{"type":"join","session_id":"s-123","participant_id":"u-1","invite_token":"..."}
{"type":"command.propose","command_id":"cmd-7","command":"socket-audit 127.0.0.1"}
{"type":"command.approve","command_id":"cmd-7"}
{"type":"command.start","command_id":"cmd-7","mode":"dry-run"}
{"type":"presence.disconnect"}
```

Server to all participants:

```json
{"type":"session.event","sequence":12,"actor_id":"u-1","event":"command.started","command_id":"cmd-7","message":"started through policy adapter"}
```

## SSE feed

```text
GET /sessions/s-123/events
Accept: text/event-stream
Authorization: Bearer <short-lived-token>

id: 12
event: session.event
data: {"sequence":12,"actor_id":"u-1","event":"command.started","command_id":"cmd-7"}

```

SSE is for visibility, not command execution. The server must enforce per-participant filtering, heartbeat timeouts, replay-from-sequence, and an explicit `session.expired` event.

The browser dashboard uses a short-lived `token` query parameter because native `EventSource` cannot set an `Authorization` header. Production reverse proxies must disable URL query logging, enforce HTTPS, keep token TTLs short, and prefer a same-origin session cookie or a WebSocket-authenticated bootstrap when available.

The transport does not grant system privileges. Actual work continues through Datya's fixed adapter allowlist, explicit scope, dry-run default, timeout, rate-limit, output cap, and append-only event log.

## Reference server

`tools/datya-collab-server.py` is a small TLS 1.3 reference transport for local integration tests. Set a strong `DATYA_COLLAB_SECRET`, provide `DATYA_TLS_CERT` and `DATYA_TLS_KEY`, and bind to `127.0.0.1` unless the LAN exposure has been reviewed:

```bash
sudo DATYA_COLLAB_SECRET='use-a-protected-secret-store' \
  DATYA_TLS_CERT=/etc/datya/tls/server.crt \
  DATYA_TLS_KEY=/etc/datya/tls/server.key \
  ./tools/datya-collab-server.py
```

Issue a participant token with `tools/issue-collab-token.sh`; the reference server enforces its embedded expiry. Do not put the secret in shell history, Git, an ISO, or a public process listing. The Python server is a reference implementation, not a complete production identity provider; production deployments still need signed tokens, revocation, rate limiting, structured redaction, secret rotation, and security review.

## Persistent event log

Set `DATYA_EVENT_LOG=/var/lib/datya/collaboration-events.log` to enable a local append-only SHA-256 hash chain. Each record uses the same six-field format as the C++ `EventLog`: sequence, timestamp, type, JSON payload, previous hash, and current hash. The server validates the complete chain at startup, appends with `fsync`, and replays validated events to new SSE clients after a restart. A corrupt log prevents startup rather than silently continuing from an untrusted state.

The automated suite covers TLS WebSocket upgrade, masked client frames, server event frames, malformed JSON resilience, scope enforcement, four-user limits, token rejection, and hash-chain records.
