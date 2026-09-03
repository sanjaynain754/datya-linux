# Datya Linux Module Repository

यह directory Datya के modular capability ecosystem का source-controlled index है। हर module को category, package identity, trust state, supported profiles, network behavior, privilege needs, tests और execution backend के साथ register किया जाएगा।

## Repository layout

```text
modules/
├── README.md
├── index/
│   ├── catalog.json
│   ├── categories/
│   │   ├── observe/
│   │   ├── defend/
│   │   ├── forensics/
│   │   ├── privacy/
│   │   ├── network/
│   │   ├── reverse-engineering/
│   │   ├── wireless/
│   │   ├── cloud-code/
│   │   ├── cryptography/
│   │   ├── learning/
│   │   └── productivity/
│   └── tools/
├── manifests/        # Per-module package and trust metadata (next phase)
├── adapters/         # Runtime policy adapters (next phase)
├── fixtures/         # Offline tests and safe lab fixtures (next phase)
└── recipes/          # Reproducible source-build recipes (next phase)
```

## Index contract

`modules/index/catalog.json` is a discoverability index, not an installation authority. A module is installed only after the package manifest, signature/checksum, dependency graph, scripts and user confirmation pass the package-manager transaction flow.

Each module entry has:

| Field | अर्थ |
|---|---|
| `id` | Stable module identifier |
| `package` | Package-manager identity |
| `category` | Discoverability category |
| `summary` | Short human-readable purpose |
| `profiles` | Explicit opt-in profiles |
| `status` | `planned`, `prototype`, `packaged-and-tested` or `enabled-by-user` |
| `requires` | Scope, confirmation, isolation or backup requirements |
| `network_behavior` | `local-only`, `network-capable` or controlled state |
| `execution` | `tool-adapter`, `daemon`, `sandbox-or-user` or future backend |

## Module lifecycle

```text
proposed → reviewed → indexed → metadata-verified → packaged → tested → profile-available → enabled-by-user → maintained → retired
```

A module is never enabled merely because it is indexed or installed. Profile enablement exposes the capability and its controls; it does not auto-run a command. Runtime actions use the existing Datya adapter policies for explicit scope, timeout, rate limit, output bounds and local evidence.

## Adding a new tool

1. Create a module directory under the appropriate category.
2. Add a package identity and canonical metadata reference.
3. Document license, source, version, architectures, checksum, privilege, network behavior and uninstall path.
4. Add an offline fixture and install/remove/runtime tests.
5. Add an adapter only when the tool needs runtime policy.
6. Run manifest, index, package, sandbox and security tests.
7. Review the diff and add the module in a focused commit.

The index is designed to grow beyond a single security distribution’s tool list while keeping the base OS small. Large or conflicting tools should be installable as isolated containers, source-build environments or user-selected packages rather than being forced into every installation.
