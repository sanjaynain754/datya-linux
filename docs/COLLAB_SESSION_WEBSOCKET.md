# Datya collaboration WebSocket transport

The `datya-collab-session` crate provides a Tokio WebSocket transport for one collaboration session with a maximum of four connected operators. Every connection must begin with a `join` message containing an operator identifier, display name, and invite token. The session core validates participant capacity, reconnects, expiry, and command input before a message is broadcast.

The transport broadcasts a structured `session_event` to all currently connected operators, including the operator who generated it. Therefore, when operator A sends a command proposal, operators B, C, and D receive the same event in real time. The transport does not execute shell commands. A separate policy adapter must authorize and execute an accepted command, then record its result through the session core.

## Starting the listener

```rust,no_run
use datya_collab_session::{websocket, CollaborationSession};
use tokio::net::TcpListener;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let listener = TcpListener::bind("127.0.0.1:9443").await?;
    websocket::run(listener, CollaborationSession::new()).await?;
    Ok(())
}
```

The example binds to loopback intentionally. A non-local deployment must put the listener behind TLS 1.3 or use a TLS-enabled listener integration, authenticate invite tokens through the deployment's token issuer, and restrict network access with an explicit scope policy. The crate does not provide certificate management or public-network authorization by itself.

## Client messages

A client first sends a text frame like this:

```json
{"type":"join","operator_id":"operator-a","display_name":"Operator A","invite_token":"issued-token"}
```

After joining, a client may propose a visible command:

```json
{"type":"command","command_id":"cmd-001","command":"nmap --version"}
```

The command is validated by the session core. It must have a unique identifier, must not contain a carriage return or newline, and must be no longer than 512 bytes. The transport only records and broadcasts the proposal. It does not run the command, grant privileges, bypass scope controls, or hide output.

A client may send a heartbeat request:

```json
{"type":"ping"}
```

The server responds with:

```json
{"type":"pong"}
```

A client may leave deliberately with:

```json
{"type":"disconnect"}
```

## Server messages

A successful join receives a capacity acknowledgement:

```json
{"type":"joined","operator_id":"operator-a","max_operators":4}
```

All connected clients receive lifecycle and command events in the following shape:

```json
{"type":"event","event":{"sequence":4,"timestamp":0,"actor_id":"operator-a","kind":"CommandProposed","command_id":"cmd-001","message":"command proposed: nmap --version"}}
```

A rejected operation is returned as an error message. A fifth operator, a removed participant, an invalid invite token, an expired session, a duplicate command identifier, or an invalid command is rejected rather than silently downgraded.

## Build and test

```bash
cargo fmt --all -- --check
cargo build --workspace --locked
cargo test -p datya-collab-session
```

For an end-to-end test, connect four clients to a disposable loopback listener, join with four issued invite tokens, send one command from the first client, and assert that the other three clients receive the same `event.sequence`, `actor_id`, `command_id`, and message. Do not use a production key, real target, or unrestricted network scope during this test.
