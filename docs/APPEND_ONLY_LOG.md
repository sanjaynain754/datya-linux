# Append-Only Local Security Event Log

The C++ control daemon stores local events as tab-separated records with six fields: sequence, Unix timestamp, event type, payload, previous SHA-256 hash, and record SHA-256 hash. The record hash covers the first five fields, while the next record carries that hash as its previous-link. A first record uses 64 zeroes as its previous hash.

The writer opens the file with `O_APPEND|O_CLOEXEC`, restricts its mode to `0600`, rejects tabs and newlines in fields, writes one complete record, and calls `fsync` before reporting success. The verifier checks sequence continuity, previous-hash continuity, and each record hash from the beginning of the file.

This detects ordinary alteration, truncation, reordering, and insertion. It is not an absolute guarantee against a fully privileged attacker who can rewrite the file and the verifier or compromise the running host. For stronger assurance, Datya should periodically seal a digest to a TPM or export it, with explicit user consent, to a user-controlled offline destination. The original local log should be preserved for incident response.

## Example

```bash
cmake -S cpp-control -B build
cmake --build build
install -d -m 0700 /var/lib/datya
./build/datya-control /var/lib/datya/events.log
```

Inside the daemon, `verify` reports whether the chain is valid. Events remain local by default; no remote synchronization is implemented by this reference daemon.
