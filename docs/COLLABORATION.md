# Datya Collaborative Sessions

Datya's collaboration layer supports up to **four authenticated participants** in one shared session. Its purpose is coordination and visibility: every participant can see who joined, which command was proposed, who approved it, when policy execution started, and what result summary was returned.

## Shared workflow

1. A participant joins with an authenticated identity.
2. A participant proposes a command with a unique command ID.
3. Other participants can see the proposal and record an approval.
4. The proposer or an approving participant starts the command through the existing policy adapter.
5. The session broadcasts a started event and later a bounded result summary.
6. The append-only local event log retains the audit trail.

The current Rust crate is the deterministic session core. It deliberately does not provide a network listener, authentication provider, or arbitrary command executor. A production transport must use authenticated encrypted connections, server-side authorization, replay protection, participant removal, session expiry, and per-event delivery acknowledgements. Commands must continue through Datya's existing allowlist, scope, dry-run, timeout, rate-limit, and output-cap controls.

## Visibility and responsibility

A participant should never be surprised by another participant's command. The UI should show the actor, command ID, target, current state, approval history, and result summary to all four participants. Secrets and unrestricted command output must not be broadcast; redact credentials and cap result payloads before publishing.

The collaboration feature accelerates authorized teamwork; it does not grant permissions, bypass scope checks, or make an activity lawful. Each participant remains responsible for the systems they control and the authorization they hold. Datya does not support illegal activity or unauthorized access.

## Next integration steps

- Add an authenticated local/LAN transport with TLS or mutually authenticated Unix-domain sockets.
- Connect the event stream to the keyboard-first dashboard.
- Persist collaboration events through the existing hash-chained log.
- Add session timeout, explicit participant removal, and conflict handling.
- Add integration tests for reconnect, replay, duplicate approvals, and redaction.
