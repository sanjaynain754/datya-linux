#!/usr/bin/env bash
set -euo pipefail
umask 077
USER_ID="${1:-}"
SECRET_FILE="${DATYA_COLLAB_SECRET_FILE:-/etc/datya/collab.secret}"
TTL="${DATYA_TOKEN_TTL:-3600}"
if [[ -z "$USER_ID" || ! "$USER_ID" =~ ^[A-Za-z0-9._-]{1,128}$ ]]; then echo "usage: $0 participant-id" >&2; exit 2; fi
if [[ ! -r "$SECRET_FILE" ]]; then echo "secret file missing: $SECRET_FILE" >&2; exit 1; fi
SECRET="$(cat "$SECRET_FILE")"
[[ -n "$SECRET" ]] || { echo "secret file is empty" >&2; exit 1; }
# The reference server validates the HMAC identity. Expiry is enforced by the
# deployment layer; rotate the secret to invalidate all outstanding tokens.
EXPIRY="$(( $(date +%s) + TTL ))"
MAC="$(printf '%s' "$USER_ID.$EXPIRY" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print $2}')"
printf '%s.%s.%s\n' "$USER_ID" "$EXPIRY" "$MAC"
printf '%s\n' "token_ttl=${TTL}s (rotate the secret to revoke all issued tokens)" >&2
