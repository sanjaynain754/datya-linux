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

The transport does not grant system privileges. Actual work continues through Datya's fixed adapter allowlist, explicit scope, dry-run default, timeout, rate-limit, output cap, and append-only event log.
