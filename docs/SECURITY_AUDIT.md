# Datya Security Audit Script

`tools/datya-security-audit.sh` is a read-only filesystem and permission audit. It detects risky configuration and observable indicators; it does not modify files, remove permissions, or prove historical unauthorized access.

## Usage

```bash
sudo ./tools/datya-security-audit.sh
sudo ./tools/datya-security-audit.sh --format json --output /var/tmp/datya-audit.json
sudo ./tools/datya-security-audit.sh --root /mnt/datya-root --min-severity 2
```

The script checks sensitive files, world-writable files and directories, SUID/SGID files, root-owned writable files, SGID directories, broken symlinks, absolute symlinks below `etc`, named ACL write access when `getfacl` is available, and authentication/permission indicators in readable logs. It uses `find -xdev` to avoid crossing filesystem boundaries.

Severity `3` is high/critical, `2` is high, `1` is informational/warning, and `0` is reserved for future low-severity records. Exit status `0` means no findings in the selected scope, `1` means warnings only, `2` means severity-2/3 findings, and `3` means invalid usage or an audit error.

A finding is a review lead, not a verdict. For example, SUID files may be legitimate system components, and a log match requires timestamp, process, user, and authorization investigation. Run from a trusted environment when auditing a potentially compromised root filesystem, preserve the JSON report as evidence, and do not treat a clean report as proof that no unauthorized access occurred.
