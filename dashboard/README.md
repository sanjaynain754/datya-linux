# Datya Real-Time Collaboration Dashboard

The dashboard is a keyboard-first, general-purpose operations view for up to four authenticated participants. It consumes the WebSocket event stream for live updates and can fall back to SSE for read-only monitoring.

## Layout

- **Top bar:** session ID, expiry countdown, TLS/authentication state, connection health.
- **Participant rail:** four slots showing display name, authenticated state, connected/disconnected state, last event time, and role.
- **Command board:** each command card shows proposer, target, tool, dry-run/execute mode, approvals, current state, start time, bounded result summary, and event sequence.
- **Event timeline:** append-only stream with actor, timestamp, event type, command ID, and sequence-gap warning.
- **Scope panel:** explicit authorized targets and expiry; network actions remain blocked outside scope.
- **Keyboard palette:** propose, approve, start, cancel, reconnect, remove participant, filter events, and export redacted evidence.

## UI state model

`connecting → authenticated → joined → live → reconnecting → expired`

A disconnected participant may reconnect with an unexpired token. An expired session is read-only for final evidence and cannot accept new commands. Removing a participant immediately blocks new actions from that identity and broadcasts `participant.removed`.

## Event handling

The client stores `last_sequence`. For every event, it checks that the next sequence is contiguous. On a gap it pauses command controls, requests replay from the last acknowledged sequence, and visibly reports the gap. It never silently invents missing events.

Result summaries are bounded and redacted server-side. The dashboard must not display private keys, tokens, passwords, or unrestricted command output. A command is never executed merely because it is visible; execution remains subject to the control daemon's scope and policy gates.

## Accessibility and privacy

Use high-contrast graphite/cyan/amber states, full keyboard navigation, clear focus indicators, screen-reader labels, and no hidden telemetry. The UI should make every participant's action visible without exposing secrets or sending data to an undisclosed remote service.
