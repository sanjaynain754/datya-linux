from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports"

items = [
    ("Repository baseline / CI", "partial", "CI and policy checks exist; Rust/kernel builds remain environment-dependent"),
    ("Nmap policy adapter", "complete", "Implemented, unit-tested, policy-controlled"),
    ("Package manager planning CLI", "prototype", "Search, info, verify, install/remove plans; no transaction executor yet"),
    ("Sandbox launcher", "prototype", "Safe/project/lab profiles; fail-closed without Bubblewrap"),
    ("Kernel Guardian sensor", "prototype", "Read-only exec/socket tracepoints; exact-kernel .ko build pending"),
    ("Explicit root-control API", "prototype", "Rust validation/audit boundary; no privilege escalation"),
    ("Indexed module repository", "prototype", "Catalog structure and index CLI with initial modules"),
    ("Security Center dashboard", "prototype", "Interactive local dashboard UI; backend event wiring pending"),
    ("Collaboration sessions", "partial", "Four-operator transport and access-control tests exist; hardening continues"),
    ("Privacy / cryptographic customization", "design", "Architecture and policy defined; implementation roadmap item"),
    ("Bootable ISO / Secure Boot", "partial", "Build/release scripts and validation plans exist; hardware verification pending"),
    ("Hardware / CPU optimization", "planned", "Benchmark matrix and platform tuning are next-phase work"),
]
order = {"complete": 0, "prototype": 1, "partial": 2, "design": 3, "planned": 4}
items.sort(key=lambda x: (order[x[1]], x[0]))
colors = {"complete": "#36d399", "prototype": "#31b8ff", "partial": "#f6c453", "design": "#b18cff", "planned": "#6c7894"}
labels = {"complete": "Complete / tested", "prototype": "Working prototype", "partial": "Partial / validation pending", "design": "Design documented", "planned": "Planned"}

fig, ax = plt.subplots(figsize=(14, 8), facecolor="#07111f")
ax.set_facecolor("#07111f")
ys = list(range(len(items)))
for y, (name, status, note) in enumerate(items):
    ax.barh(y, 1.85, color=colors[status], height=0.58, edgecolor="#0d2035", linewidth=1.2)
    ax.text(0.05, y, labels[status], va="center", ha="left", color="#06101b", fontsize=9.5, fontweight="bold")
    ax.text(1.98, y, name, va="center", ha="left", color="#e6f1ff", fontsize=10)

ax.set_xlim(0, 7.2)
ax.set_ylim(-1, len(items))
ax.set_yticks([])
ax.set_xticks([])
for spine in ax.spines.values():
    spine.set_visible(False)
ax.invert_yaxis()
fig.text(0.06, 0.95, "DATYA LINUX — CURRENT COVERAGE", color="#31d7ff", fontsize=12, fontweight="bold")
fig.text(0.06, 0.905, "What is covered today, and what still needs implementation", color="#f2f7ff", fontsize=22, fontweight="bold")
fig.text(0.06, 0.875, "Repository assessment at the current main branch; status is capability maturity, not a percentage claim.", color="#91a6bd", fontsize=10)
legend = [Patch(facecolor=colors[s], label=labels[s]) for s in ["complete", "prototype", "partial", "design", "planned"]]
ax.legend(handles=legend, loc="lower left", bbox_to_anchor=(0, -0.10), ncol=3, frameon=False, labelcolor="#c9d7e8", fontsize=9)
fig.text(0.06, 0.018, "Priority next: locked Rust/kernel validation → package transaction engine → event wiring → hardware benchmark matrix", color="#91a6bd", fontsize=9)
fig.savefig(OUT / "datya-progress.png", dpi=180, facecolor=fig.get_facecolor(), bbox_inches="tight")
plt.close(fig)

summary = OUT / "datya-progress.md"
counts = {}
for _, status, _ in items:
    counts[status] = counts.get(status, 0) + 1
lines = ["# Datya Linux progress graph data", "", "Status is a repository-grounded maturity assessment, not a percentage completion claim.", "", "| Status | Count |", "|---|---:|"]
for status in ["complete", "prototype", "partial", "design", "planned"]:
    lines.append(f"| {labels[status]} | {counts.get(status, 0)} |")
lines += ["", "| Workstream | Status | Evidence / next gap |", "|---|---|---|"]
for name, status, note in items:
    lines.append(f"| {name} | {labels[status]} | {note} |")
summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
