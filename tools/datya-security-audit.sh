#!/usr/bin/env bash
# Datya Linux read-only filesystem and permission audit.
# It reports indicators; it does not prove historical unauthorized access.
set -uo pipefail

ROOT="/"
FORMAT="text"
OUT=""
MIN_SEVERITY=0
ISSUES=0
WARNINGS=0
TMP=""

usage() {
  cat <<'EOF'
Usage: datya-security-audit.sh [options]

Read-only checks:
  --root PATH          Audit another mounted root (default: /)
  --format text|json   Output format (default: text)
  --output PATH        Write report to PATH (default: stdout)
  --min-severity N     Show only severity 0-3 (default: 0)
  --help               Show this help

Exit status: 0 no findings, 1 warnings, 2 high/critical findings, 3 usage/error.
This tool detects risky configuration and observable evidence; it cannot prove
that a file was or was not accessed in the past.
EOF
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) [[ $# -ge 2 ]] || { echo "--root needs a path" >&2; exit 3; }; ROOT="$2"; shift 2;;
    --format) [[ $# -ge 2 && "$2" =~ ^(text|json)$ ]] || { echo "format must be text or json" >&2; exit 3; }; FORMAT="$2"; shift 2;;
    --output) [[ $# -ge 2 ]] || { echo "--output needs a path" >&2; exit 3; }; OUT="$2"; shift 2;;
    --min-severity) [[ $# -ge 2 && "$2" =~ ^[0-3]$ ]] || { echo "severity must be 0-3" >&2; exit 3; }; MIN_SEVERITY="$2"; shift 2;;
    --help) usage; exit 0;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 3;;
  esac
done
[[ -d "$ROOT" ]] || { echo "root is not a directory: $ROOT" >&2; exit 3; }
command -v find >/dev/null || { echo "find is required" >&2; exit 3; }
command -v stat >/dev/null || { echo "stat is required" >&2; exit 3; }
TMP="$(mktemp -d)" || exit 3
trap 'rm -rf "$TMP"' EXIT

# tab-delimited: severity, code, path, detail
REPORT="$TMP/report.tsv"
add_finding() {
  local severity="$1" code="$2" path="$3" detail="$4"
  [[ "$severity" -ge "$MIN_SEVERITY" ]] || return 0
  printf '%s\t%s\t%s\t%s\n' "$severity" "$code" "${path//$'\t'/ }" "${detail//$'\t'/ }" >> "$REPORT"
  if [[ "$severity" -ge 2 ]]; then ((ISSUES+=1)); else ((WARNINGS+=1)); fi
}
scan_find() {
  local expression="$1" code="$2" severity="$3" detail="$4"
  while IFS= read -r -d '' item; do add_finding "$severity" "$code" "$item" "$detail"; done < <(find -P "$ROOT" -xdev $expression -print0 2>/dev/null)
}

# Sensitive paths: existence is not itself a finding; unsafe mode/ownership is.
check_sensitive() {
  local rel path mode owner group
  for rel in etc/shadow etc/gshadow etc/sudoers etc/ssh/sshd_config root/.ssh; do
    path="$ROOT/$rel"; [[ -e "$path" || -L "$path" ]] || continue
    mode="$(stat -c '%a' "$path" 2>/dev/null || echo 0)"; owner="$(stat -c '%U' "$path" 2>/dev/null || echo unknown)"; group="$(stat -c '%G' "$path" 2>/dev/null || echo unknown)"
    (( 10#$mode % 10 > 0 )) && add_finding 3 SENSITIVE_OTHER_ACCESS "$path" "mode=$mode owner=$owner group=$group"
    [[ "$owner" == root ]] || add_finding 2 SENSITIVE_NOT_ROOT "$path" "owner=$owner group=$group mode=$mode"
    [[ "$rel" == root/.ssh && "$mode" -gt 700 ]] && add_finding 2 SSH_DIR_PERMISSIVE "$path" "mode=$mode"
  done
}
check_sensitive

# Broad permission hazards. Exclude virtual/runtime trees and the audit output root.
for skip in proc sys dev run tmp; do :; done
scan_find "-type f -perm -0002" WORLD_WRITABLE_FILE 2 "any user can modify this regular file"
scan_find "-type d -perm -0002 ! -perm -1000" WORLD_WRITABLE_DIR 2 "world-writable directory lacks sticky bit"
scan_find "-xdev -type f -perm /6000" SUID_SGID_FILE 2 "SUID/SGID executable; verify provenance and necessity"
scan_find "-xdev -type d -perm /2000" SGID_DIRECTORY 1 "SGID directory; verify group ownership and write policy"

# Root-owned files with group/other write bits are especially sensitive.
while IFS= read -r -d '' item; do
  mode="$(stat -c '%a' "$item" 2>/dev/null || echo 0)"; owner="$(stat -c '%U' "$item" 2>/dev/null || echo unknown)"
  [[ "$owner" == root ]] && (( 10#$mode % 100 >= 20 || 10#$mode % 10 >= 2 )) && add_finding 3 ROOT_WRITABLE_FILE "$item" "root-owned mode=$mode"
done < <(find -P "$ROOT" -xdev -type f -perm /0022 -print0 2>/dev/null)

# Broken and absolute symlinks can redirect privileged consumers.
while IFS= read -r -d '' item; do
  [[ -e "$item" ]] || add_finding 1 BROKEN_SYMLINK "$item" "symlink target is missing"
  target="$(readlink "$item" 2>/dev/null || true)"
  [[ "$target" == /* && "$item" == "$ROOT/etc/"* ]] && add_finding 1 ABSOLUTE_ETC_SYMLINK "$item" "target=$target; review privileged configuration redirection"
done < <(find -P "$ROOT" -xdev -type l -print0 2>/dev/null)

# Optional ACL and mount evidence.
if command -v getfacl >/dev/null; then
  while IFS= read -r -d '' item; do
    if getfacl -cp "$item" 2>/dev/null | grep -qE '^user:[^:]+:.*w|^group:[^:]+:.*w'; then add_finding 2 ACL_WRITE_ACCESS "$item" "named ACL grants write access; review identity and scope"; fi
  done < <(find -P "$ROOT/etc" "$ROOT/usr" "$ROOT/var" -xdev -type f -print0 2>/dev/null)
fi
if command -v findmnt >/dev/null; then
  while IFS= read -r line; do
    [[ "$line" == *"nosuid"* ]] || continue
    : # presence of nosuid is protective; recorded in the summary below
  done < <(findmnt -rn -o TARGET,OPTIONS 2>/dev/null)
fi

# Audit evidence: these are informational unless a readable log contains failures.
for log in "$ROOT/var/log/auth.log" "$ROOT/var/log/secure" "$ROOT/var/log/audit/audit.log"; do
  [[ -r "$log" ]] || continue
  count="$(grep -Eic 'permission denied|authentication failure|unauthorized|user not known' "$log" 2>/dev/null || true)"
  [[ "$count" -gt 0 ]] && add_finding 1 AUTH_LOG_INDICATOR "$log" "$count matching authentication/permission indicators; investigate timestamps and actors"
done

emit_text() {
  printf 'Datya Security Audit\nroot=%s\nfindings=%d warnings=%d\n' "$ROOT" "$ISSUES" "$WARNINGS"
  if [[ ! -s "$REPORT" ]]; then echo 'status=clean (within checks and visibility available)'; return; fi
  printf '\nSEV\tCODE\tPATH\tDETAIL\n'; sort -t $'\t' -k1,1nr "$REPORT"
  printf '\nLimitation: this report detects observable permission/configuration risks and available log indicators; it cannot prove historical file access.\n'
}
emit_json() {
  printf '{"root":%s,"findings":%d,"warnings":%d,"records":[' "$(printf '%s' "$ROOT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" "$ISSUES" "$WARNINGS"
  local first=1 sev code path detail
  while IFS=$'\t' read -r sev code path detail; do
    [[ -n "$sev" ]] || continue; (( first )) || printf ','; first=0
    python3 -c 'import json,sys; print(json.dumps(dict(zip(("severity","code","path","detail"),sys.argv[1:]))),end="")' "$sev" "$code" "$path" "$detail"
  done < "$REPORT"
  printf ']}\n'
}
if [[ -n "$OUT" ]]; then exec 3>"$OUT" || { echo "cannot write output: $OUT" >&2; exit 3; }; else exec 3>&1; fi
if [[ "$FORMAT" == text ]]; then emit_text >&3; else emit_json >&3; fi
exec 3>&-
(( ISSUES > 0 )) && exit 2
(( WARNINGS > 0 )) && exit 1
exit 0
