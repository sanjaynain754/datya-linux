# Datya Developer Environment

## Purpose

After installation, Datya Linux should offer an optional **Developer Workspace**: a proper graphical window containing a terminal, editor, project browser, logs, and a result panel. The user can write code, run it locally, inspect errors, and build projects without needing a cloud account or hidden remote service.

The workspace is optional and modular. A user installing only the desktop profile should not automatically receive compilers, language servers, containers, or offensive-security tools.

## User experience

The workspace will provide a terminal with searchable history, an editor with syntax highlighting, a project directory, and one-click commands for format, test, build, and run. Each run should show the exact command, working directory, environment profile, exit code, duration, stdout, and stderr. The user can export results locally.

A first-run setup should let the user choose language packs such as Rust, C/C++, Go, Python, JavaScript, or shell. Toolchains should be pinned and verified. The workspace must work offline after packages are installed; network access is opt-in per project.

## Privacy model

The workspace must not send source code, terminal history, diagnostics, telemetry, crash dumps, or results to a remote service by default. It should show every process that opens a network connection, including the workspace itself and package managers. DNS and proxy configuration must be visible and editable.

No operating system can promise that a user is impossible to track. Local malware, compromised firmware, a hostile network, a remote website, or a modified hardware stack can defeat endpoint assumptions. Datya should instead minimize exposure, make activity observable, and provide recovery and verification paths.

## Execution profiles

| Profile | Intended use | Default network | Isolation |
|---|---|---:|---|
| Safe run | Learning and ordinary code | Disabled | Dedicated temporary directory, resource limits |
| Project run | Normal development | Ask per project | User-owned project sandbox |
| Lab run | Authorized security testing | Disabled until enabled | Disposable VM/container, test fixtures only |
| System run | Administration | Restricted | Explicit privilege escalation and audit entry |

The default runner should use an unprivileged user, a temporary filesystem, CPU/memory/process limits, a timeout, and a clean environment. It should never execute pasted commands automatically. Dangerous operations such as raw sockets, kernel modules, device access, credential stores, or unrestricted host mounts require an explicit profile change and clear warning.

## Reproducibility and results

Each run should record a local manifest containing the toolchain versions, dependency lockfile hash, command, profile, and result. Logs are stored locally under user-selected retention settings. The user can disable retention or delete a project's logs. A result is useful only when it is reproducible; the UI should distinguish a compiler/test result from a heuristic security finding.

## Customization

The workspace is built from packages and declarative configuration. Communities can publish themes, language packs, editor integrations, policy profiles, and downstream images. Datya does not lock users into one editor or language. Security defaults should be easy to understand and hard to change accidentally, but never hidden from advanced users.
