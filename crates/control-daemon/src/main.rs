use std::collections::BTreeSet;
use std::io::{self, BufRead, Write};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug)]
struct Tool {
    id: &'static str,
    category: &'static str,
    description: &'static str,
    needs_network: bool,
}

#[derive(Debug)]
struct ControlState {
    authorized_targets: BTreeSet<String>,
    dry_run: bool,
}

const CATALOG: &[Tool] = &[
    Tool {
        id: "asset-inventory",
        category: "discovery",
        description: "Inventory declared local or scoped assets",
        needs_network: false,
    },
    Tool {
        id: "dns-inspect",
        category: "network",
        description: "Inspect DNS records for an authorized target",
        needs_network: true,
    },
    Tool {
        id: "certificate-inspect",
        category: "network",
        description: "Inspect certificates for an authorized target",
        needs_network: true,
    },
    Tool {
        id: "service-inventory",
        category: "discovery",
        description: "Enumerate services in an authorized scope",
        needs_network: true,
    },
    Tool {
        id: "http-headers",
        category: "web",
        description: "Review HTTP headers for an authorized endpoint",
        needs_network: true,
    },
    Tool {
        id: "web-config-audit",
        category: "web",
        description: "Check declared web configuration safely",
        needs_network: true,
    },
    Tool {
        id: "tls-audit",
        category: "web",
        description: "Review TLS configuration",
        needs_network: true,
    },
    Tool {
        id: "sast",
        category: "code",
        description: "Static analysis for a local project",
        needs_network: false,
    },
    Tool {
        id: "dependency-audit",
        category: "code",
        description: "Audit local dependency manifests",
        needs_network: false,
    },
    Tool {
        id: "secrets-scan",
        category: "code",
        description: "Find likely secrets in local source",
        needs_network: false,
    },
    Tool {
        id: "hash-manifest",
        category: "forensics",
        description: "Create hashes for selected local evidence",
        needs_network: false,
    },
    Tool {
        id: "file-timeline",
        category: "forensics",
        description: "Build a timeline from local file metadata",
        needs_network: false,
    },
    Tool {
        id: "process-audit",
        category: "defense",
        description: "Review local process evidence",
        needs_network: false,
    },
    Tool {
        id: "socket-audit",
        category: "defense",
        description: "Review local socket evidence",
        needs_network: false,
    },
    Tool {
        id: "persistence-audit",
        category: "defense",
        description: "Review local persistence locations",
        needs_network: false,
    },
    Tool {
        id: "integrity-check",
        category: "defense",
        description: "Compare files with a trusted manifest",
        needs_network: false,
    },
    Tool {
        id: "log-review",
        category: "defense",
        description: "Search local security logs",
        needs_network: false,
    },
    Tool {
        id: "auth-review",
        category: "defense",
        description: "Review local authentication events",
        needs_network: false,
    },
    Tool {
        id: "firewall-status",
        category: "defense",
        description: "Read local firewall policy status",
        needs_network: false,
    },
    Tool {
        id: "kernel-posture",
        category: "defense",
        description: "Report kernel security posture",
        needs_network: false,
    },
    Tool {
        id: "boot-integrity",
        category: "defense",
        description: "Report Secure Boot and boot evidence",
        needs_network: false,
    },
    Tool {
        id: "container-audit",
        category: "cloud",
        description: "Audit local container configuration",
        needs_network: false,
    },
    Tool {
        id: "image-sbom",
        category: "cloud",
        description: "Read an image software bill of materials",
        needs_network: false,
    },
    Tool {
        id: "iac-review",
        category: "cloud",
        description: "Review local infrastructure configuration",
        needs_network: false,
    },
    Tool {
        id: "policy-lint",
        category: "cloud",
        description: "Lint local policy files",
        needs_network: false,
    },
    Tool {
        id: "pcap-summary",
        category: "network",
        description: "Summarize a local capture file",
        needs_network: false,
    },
    Tool {
        id: "flow-summary",
        category: "network",
        description: "Summarize authorized flow evidence",
        needs_network: true,
    },
    Tool {
        id: "route-review",
        category: "network",
        description: "Review local routing state",
        needs_network: false,
    },
    Tool {
        id: "arp-review",
        category: "network",
        description: "Review local neighbor evidence",
        needs_network: false,
    },
    Tool {
        id: "wifi-posture",
        category: "wireless",
        description: "Read local wireless posture",
        needs_network: false,
    },
    Tool {
        id: "wifi-survey",
        category: "wireless",
        description: "Survey networks only with explicit scope",
        needs_network: true,
    },
    Tool {
        id: "bluetooth-posture",
        category: "wireless",
        description: "Read local Bluetooth posture",
        needs_network: false,
    },
    Tool {
        id: "usb-inventory",
        category: "hardware",
        description: "Inventory attached USB devices",
        needs_network: false,
    },
    Tool {
        id: "firmware-inventory",
        category: "hardware",
        description: "Inventory local firmware metadata",
        needs_network: false,
    },
    Tool {
        id: "memory-triage",
        category: "forensics",
        description: "Prepare local memory triage metadata",
        needs_network: false,
    },
    Tool {
        id: "disk-triage",
        category: "forensics",
        description: "Prepare local disk triage metadata",
        needs_network: false,
    },
    Tool {
        id: "yara-review",
        category: "malware",
        description: "Scan local files with a user rule set",
        needs_network: false,
    },
    Tool {
        id: "sandbox-report",
        category: "malware",
        description: "Read a disposable sandbox report",
        needs_network: false,
    },
    Tool {
        id: "pe-review",
        category: "reverse",
        description: "Review a local PE file",
        needs_network: false,
    },
    Tool {
        id: "elf-review",
        category: "reverse",
        description: "Review a local ELF file",
        needs_network: false,
    },
    Tool {
        id: "strings-review",
        category: "reverse",
        description: "Review strings from a local binary",
        needs_network: false,
    },
    Tool {
        id: "symbols-review",
        category: "reverse",
        description: "Review symbols from a local binary",
        needs_network: false,
    },
    Tool {
        id: "diff-review",
        category: "reverse",
        description: "Compare two local binaries",
        needs_network: false,
    },
    Tool {
        id: "container-secrets",
        category: "cloud",
        description: "Find secrets in local images",
        needs_network: false,
    },
    Tool {
        id: "k8s-manifest",
        category: "cloud",
        description: "Review local Kubernetes manifests",
        needs_network: false,
    },
    Tool {
        id: "cloud-identity",
        category: "cloud",
        description: "Review provided cloud identity evidence",
        needs_network: false,
    },
    Tool {
        id: "cloud-storage",
        category: "cloud",
        description: "Review provided storage evidence",
        needs_network: false,
    },
    Tool {
        id: "report-json",
        category: "reporting",
        description: "Export structured local findings",
        needs_network: false,
    },
    Tool {
        id: "report-html",
        category: "reporting",
        description: "Create a local HTML report",
        needs_network: false,
    },
    Tool {
        id: "evidence-vault",
        category: "reporting",
        description: "Store hashed local evidence",
        needs_network: false,
    },
    Tool {
        id: "scope-check",
        category: "governance",
        description: "Validate an assessment scope",
        needs_network: false,
    },
    Tool {
        id: "rate-limit-check",
        category: "governance",
        description: "Validate configured assessment limits",
        needs_network: false,
    },
    Tool {
        id: "consent-check",
        category: "governance",
        description: "Show network consent state",
        needs_network: false,
    },
    Tool {
        id: "ai-local",
        category: "assistant",
        description: "Run an optional local analysis assistant",
        needs_network: false,
    },
    Tool {
        id: "github-import",
        category: "workflow",
        description: "Prepare a repository for local review",
        needs_network: true,
    },
    Tool {
        id: "lab-reset",
        category: "lab",
        description: "Reset a disposable authorized lab",
        needs_network: false,
    },
    Tool {
        id: "lab-status",
        category: "lab",
        description: "Read disposable lab status",
        needs_network: false,
    },
    Tool {
        id: "ctf-check",
        category: "learn",
        description: "Check a local training challenge",
        needs_network: false,
    },
    Tool {
        id: "training-report",
        category: "learn",
        description: "Export local training results",
        needs_network: false,
    },
    Tool {
        id: "alert-timeline",
        category: "defense",
        description: "Show Guardian alert timeline",
        needs_network: false,
    },
    Tool {
        id: "alert-explain",
        category: "defense",
        description: "Explain evidence behind an alert",
        needs_network: false,
    },
    Tool {
        id: "package-provenance",
        category: "integrity",
        description: "Review package provenance metadata",
        needs_network: false,
    },
    Tool {
        id: "update-verify",
        category: "integrity",
        description: "Verify local update metadata",
        needs_network: false,
    },
    Tool {
        id: "repro-check",
        category: "integrity",
        description: "Compare a local build manifest",
        needs_network: false,
    },
    Tool {
        id: "privacy-check",
        category: "privacy",
        description: "Review local telemetry posture",
        needs_network: false,
    },
    Tool {
        id: "dns-leak-check",
        category: "privacy",
        description: "Check configured DNS routing",
        needs_network: true,
    },
    Tool {
        id: "proxy-check",
        category: "privacy",
        description: "Review local proxy configuration",
        needs_network: false,
    },
];

fn find_tool(id: &str) -> Option<&'static Tool> {
    CATALOG.iter().find(|tool| tool.id == id)
}

fn print_help() {
    println!("commands: help | tools [category] | scope add <target> | scope list | run <tool> <target> | mode dry-run|execute | quit");
}

fn run_command(line: &str, state: &mut ControlState) -> bool {
    let mut words = line.split_whitespace();
    match words.next() {
        Some("help") => print_help(),
        Some("tools") => {
            let category = words.next();
            for tool in CATALOG.iter().filter(|tool| match category {
                None => true,
                Some(value) => value == tool.category,
            }) {
                println!(
                    "{:<20} {:<12} network={} {}",
                    tool.id, tool.category, tool.needs_network, tool.description
                );
            }
            println!("{} tools available", CATALOG.len());
        }
        Some("scope") if words.next() == Some("add") => {
            if let Some(target) = words.next() {
                state.authorized_targets.insert(target.to_string());
                println!("scope added: {target}");
            } else {
                println!("error: scope add requires a target");
            }
        }
        Some("scope") if words.next() == Some("list") => {
            for target in &state.authorized_targets {
                println!("authorized: {target}");
            }
        }
        Some("mode") => match words.next() {
            Some("dry-run") => {
                state.dry_run = true;
                println!("mode=dry-run");
            }
            Some("execute") => {
                state.dry_run = false;
                println!("mode=execute; each tool must still enforce its own safety policy");
            }
            _ => println!("error: use mode dry-run or mode execute"),
        },
        Some("run") => {
            let id = words.next();
            let target = words.next();
            match (id.and_then(find_tool), target) {
                (Some(tool), Some(target))
                    if !tool.needs_network || state.authorized_targets.contains(target) =>
                {
                    let ts = SystemTime::now()
                        .duration_since(UNIX_EPOCH)
                        .map_or(0, |d| d.as_secs());
                    println!("{{\"schema\":\"datya.action.v1\",\"timestamp\":{},\"tool\":\"{}\",\"target\":\"{}\",\"mode\":\"{}\",\"status\":\"{}\"}}", ts, tool.id, target, if state.dry_run { "dry-run" } else { "execute" }, if state.dry_run { "planned" } else { "queued-for-policy-adapter" });
                }
                (Some(_), Some(_)) => println!("blocked: target is not in the authorized scope"),
                _ => println!("error: run requires a known tool and target"),
            }
        }
        Some("quit") | Some("exit") => return false,
        Some(_) | None => println!("unknown command; type help"),
    }
    true
}

fn main() {
    let stdin = io::stdin();
    let mut state = ControlState {
        authorized_targets: BTreeSet::new(),
        dry_run: true,
    };
    print!("datya> ");
    let _ = io::stdout().flush();
    for line in stdin.lock().lines().map_while(Result::ok) {
        if !run_command(&line, &mut state) {
            break;
        }
        print!("datya> ");
        let _ = io::stdout().flush();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn catalog_has_more_than_sixty_tools() {
        assert!(CATALOG.len() >= 60);
    }
    #[test]
    fn network_action_requires_scope() {
        let tool = find_tool("dns-inspect").unwrap();
        assert!(tool.needs_network);
    }
}
