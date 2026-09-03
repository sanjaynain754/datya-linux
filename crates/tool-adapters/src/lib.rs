use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fmt::Write as FmtWrite;
use std::fs::{self, File};
use std::io;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RunMode {
    DryRun,
    Execute,
}

#[derive(Clone, Copy, Debug)]
pub struct AdapterSpec {
    pub id: &'static str,
    pub executable: &'static str,
    pub needs_scope: bool,
    pub max_args: usize,
}

pub const ADAPTERS: &[AdapterSpec] = &[
    AdapterSpec {
        id: "socket-audit",
        executable: "/usr/bin/ss",
        needs_scope: false,
        max_args: 8,
    },
    AdapterSpec {
        id: "route-review",
        executable: "/usr/sbin/ip",
        needs_scope: false,
        max_args: 6,
    },
    AdapterSpec {
        id: "dns-inspect",
        executable: "/usr/bin/dig",
        needs_scope: true,
        max_args: 4,
    },
    AdapterSpec {
        id: "http-headers",
        executable: "/usr/bin/curl",
        needs_scope: true,
        max_args: 8,
    },
    AdapterSpec {
        id: "process-audit",
        executable: "/usr/bin/ps",
        needs_scope: false,
        max_args: 4,
    },
    AdapterSpec {
        id: "kernel-posture",
        executable: "/usr/bin/uname",
        needs_scope: false,
        max_args: 2,
    },
    AdapterSpec {
        id: "firewall-status",
        executable: "/usr/sbin/ufw",
        needs_scope: false,
        max_args: 2,
    },
    AdapterSpec {
        id: "apparmor-review",
        executable: "/usr/sbin/aa-status",
        needs_scope: false,
        max_args: 2,
    },
];

#[derive(Clone, Debug)]
pub struct ExecutionPolicy {
    pub mode: RunMode,
    pub timeout: Duration,
    pub min_interval: Duration,
    pub max_output_bytes: usize,
    pub authorized_targets: Vec<String>,
}

#[derive(Debug, PartialEq, Eq)]
pub enum Decision {
    Planned,
    Completed(i32),
    TimedOut,
    Blocked(String),
}

#[derive(Debug)]
pub struct ExecutionResult {
    pub tool: String,
    pub target: Option<String>,
    pub decision: Decision,
    pub stdout: String,
    pub stderr: String,
    pub evidence_path: Option<PathBuf>,
}

#[derive(Default)]
pub struct RateLimiter {
    last_run: Option<Instant>,
}
impl RateLimiter {
    fn allow(&mut self, interval: Duration) -> bool {
        let now = Instant::now();
        let allowed = match self.last_run {
            None => true,
            Some(last) => now.duration_since(last) >= interval,
        };
        if allowed {
            self.last_run = Some(now);
        }
        allowed
    }
}

fn spec(tool: &str) -> Option<&'static AdapterSpec> {
    ADAPTERS.iter().find(|item| item.id == tool)
}

fn safe_target(target: &str) -> bool {
    !target.is_empty()
        && target.len() <= 253
        && !target.starts_with('-')
        && target
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || ".:/_-".contains(c))
}

fn bounded(path: &Path, max: usize) -> String {
    let bytes = fs::read(path).unwrap_or_default();
    String::from_utf8_lossy(&bytes[..bytes.len().min(max)]).into_owned()
}

pub fn execute(
    tool: &str,
    args: &[String],
    target: Option<&str>,
    policy: &ExecutionPolicy,
    limiter: &mut RateLimiter,
) -> io::Result<ExecutionResult> {
    let Some(spec) = spec(tool) else {
        return Ok(blocked(
            tool,
            target,
            "tool is not in the built-in adapter allowlist",
        ));
    };
    if args.len() > spec.max_args
        || args
            .iter()
            .any(|arg| arg.starts_with('-') && arg.len() > 1 && arg == "--")
    {
        return Ok(blocked(
            tool,
            target,
            "argument policy rejected the request",
        ));
    }
    if spec.needs_scope {
        let Some(value) = target.filter(|value| safe_target(value)) else {
            return Ok(blocked(tool, target, "a valid target is required"));
        };
        if !policy.authorized_targets.iter().any(|item| item == value) {
            return Ok(blocked(
                tool,
                target,
                "target is outside the authorized scope",
            ));
        }
    }
    if !limiter.allow(policy.min_interval) {
        return Ok(blocked(tool, target, "rate limit is active"));
    }
    if policy.mode == RunMode::DryRun {
        return Ok(ExecutionResult {
            tool: tool.into(),
            target: target.map(str::to_string),
            decision: Decision::Planned,
            stdout: String::new(),
            stderr: String::new(),
            evidence_path: None,
        });
    }

    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos());
    let base = std::env::temp_dir().join(format!("datya-evidence-{}-{stamp}", std::process::id()));
    let out_path = base.with_extension("out");
    let err_path = base.with_extension("err");
    let mut command = Command::new(spec.executable);
    command
        .args(args)
        .stdout(Stdio::from(File::create(&out_path)?))
        .stderr(Stdio::from(File::create(&err_path)?));
    let mut child = command.spawn()?;
    let started = Instant::now();
    let decision = loop {
        if let Some(status) = child.try_wait()? {
            break Decision::Completed(status.code().unwrap_or(1));
        }
        if started.elapsed() >= policy.timeout {
            child.kill()?;
            let _ = child.wait();
            break Decision::TimedOut;
        }
        thread::sleep(Duration::from_millis(25));
    };
    let stdout = bounded(&out_path, policy.max_output_bytes);
    let stderr = bounded(&err_path, policy.max_output_bytes);
    let evidence_path = Some(out_path.clone());
    let _ = fs::remove_file(&err_path);
    Ok(ExecutionResult {
        tool: tool.into(),
        target: target.map(str::to_string),
        decision,
        stdout,
        stderr,
        evidence_path,
    })
}

fn blocked(tool: &str, target: Option<&str>, reason: &str) -> ExecutionResult {
    ExecutionResult {
        tool: tool.into(),
        target: target.map(str::to_string),
        decision: Decision::Blocked(reason.into()),
        stdout: String::new(),
        stderr: String::new(),
        evidence_path: None,
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum NmapMode {
    DryRun,
    Execute,
}

#[derive(Clone, Debug)]
pub struct NmapPolicy {
    pub mode: NmapMode,
    pub authorized_targets: Vec<String>,
    pub timeout: Duration,
    pub max_output_bytes: usize,
}

impl Default for NmapPolicy {
    fn default() -> Self {
        Self {
            mode: NmapMode::DryRun,
            authorized_targets: Vec::new(),
            timeout: Duration::from_secs(30),
            max_output_bytes: 1024 * 1024,
        }
    }
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct NmapAction {
    pub schema: &'static str,
    pub tool: &'static str,
    pub target: String,
    pub mode: &'static str,
    pub status: &'static str,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct HashChainEvent {
    pub sequence: u64,
    pub action: NmapAction,
    pub previous_hash: String,
    pub hash: String,
}

#[derive(Clone, Debug, Default)]
pub struct HashChainLog {
    events: Vec<HashChainEvent>,
}

impl HashChainLog {
    pub fn append(&mut self, action: NmapAction) {
        let previous_hash = self
            .events
            .last()
            .map(|event| event.hash.clone())
            .unwrap_or_else(|| "0".repeat(64));
        let sequence = self.events.len() as u64;
        let canonical = format!(
            "{}\\n{}\\n{}\\n{}",
            sequence,
            action_json(&action),
            previous_hash,
            action.status
        );
        let hash = hex_digest(canonical.as_bytes());
        self.events.push(HashChainEvent {
            sequence,
            action,
            previous_hash,
            hash,
        });
    }

    pub fn events(&self) -> &[HashChainEvent] {
        &self.events
    }

    pub fn verify(&self) -> bool {
        let mut previous = "0".repeat(64);
        for (index, event) in self.events.iter().enumerate() {
            if event.sequence != index as u64 || event.previous_hash != previous {
                return false;
            }
            let canonical = format!(
                "{}\\n{}\\n{}\\n{}",
                event.sequence,
                action_json(&event.action),
                event.previous_hash,
                event.action.status
            );
            if hex_digest(canonical.as_bytes()) != event.hash {
                return false;
            }
            previous = event.hash.clone();
        }
        true
    }
}

fn action_json(action: &NmapAction) -> String {
    serde_json::to_string(action).expect("NmapAction serialization cannot fail")
}

fn hex_digest(data: &[u8]) -> String {
    let mut output = String::with_capacity(64);
    for byte in Sha256::digest(data) {
        write!(&mut output, "{byte:02x}").expect("writing to String cannot fail");
    }
    output
}

fn valid_nmap_target(target: &str) -> bool {
    safe_target(target) && !target.contains("..") && !target.contains('\0')
}

pub fn execute_nmap(
    target: &str,
    operator_confirmed: bool,
    policy: &NmapPolicy,
    log: &mut HashChainLog,
) -> io::Result<NmapAction> {
    let blocked = |log: &mut HashChainLog, reason: &str| {
        let _ = reason;
        let action = NmapAction {
            schema: "datya.action.v1",
            tool: "nmap",
            target: target.to_string(),
            mode: if operator_confirmed {
                "execute"
            } else {
                "dry-run"
            },
            status: "blocked",
        };
        log.append(action.clone());
        action
    };

    if !valid_nmap_target(target) || !policy.authorized_targets.iter().any(|item| item == target) {
        return Ok(blocked(log, "target is outside the authorized scope"));
    }
    if !operator_confirmed || policy.mode == NmapMode::DryRun {
        let action = NmapAction {
            schema: "datya.action.v1",
            tool: "nmap",
            target: target.to_string(),
            mode: "dry-run",
            status: "planned",
        };
        log.append(action.clone());
        return Ok(action);
    }

    let timeout = policy.timeout.min(Duration::from_secs(30));
    let max_output_bytes = policy.max_output_bytes.min(1024 * 1024);
    let output_dir = std::env::temp_dir();
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_nanos());
    let stdout_path = output_dir.join(format!("datya-nmap-{stamp}.out"));
    let stderr_path = output_dir.join(format!("datya-nmap-{stamp}.err"));
    let mut child = Command::new("/usr/bin/nmap")
        .arg("--")
        .arg(target)
        .stdout(Stdio::from(File::create(&stdout_path)?))
        .stderr(Stdio::from(File::create(&stderr_path)?))
        .spawn()?;
    let started = Instant::now();
    let mut over_limit = false;
    loop {
        if child.try_wait()?.is_some() {
            break;
        }
        let output_size = fs::metadata(&stdout_path).map_or(0, |meta| meta.len())
            + fs::metadata(&stderr_path).map_or(0, |meta| meta.len());
        if output_size > max_output_bytes as u64 || started.elapsed() >= timeout {
            over_limit = output_size > max_output_bytes as u64;
            child.kill()?;
            let _ = child.wait();
            break;
        }
        thread::sleep(Duration::from_millis(20));
    }
    let action = NmapAction {
        schema: "datya.action.v1",
        tool: "nmap",
        target: target.to_string(),
        mode: "execute",
        status: if over_limit { "blocked" } else { "completed" },
    };
    log.append(action.clone());
    let _ = fs::remove_file(stdout_path);
    let _ = fs::remove_file(stderr_path);
    Ok(action)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn policy(mode: RunMode) -> ExecutionPolicy {
        ExecutionPolicy {
            mode,
            timeout: Duration::from_secs(1),
            min_interval: Duration::ZERO,
            max_output_bytes: 1024,
            authorized_targets: vec!["example.org".into()],
        }
    }
    #[test]
    fn dry_run_never_spawns() {
        let result = execute(
            "dns-inspect",
            &[],
            Some("example.org"),
            &policy(RunMode::DryRun),
            &mut RateLimiter::default(),
        )
        .unwrap();
        assert_eq!(result.decision, Decision::Planned);
    }
    #[test]
    fn unknown_tool_is_blocked() {
        let result = execute(
            "arbitrary",
            &[],
            None,
            &policy(RunMode::DryRun),
            &mut RateLimiter::default(),
        )
        .unwrap();
        assert!(matches!(result.decision, Decision::Blocked(_)));
    }
    #[test]
    fn out_of_scope_target_is_blocked() {
        let result = execute(
            "dns-inspect",
            &[],
            Some("other.org"),
            &policy(RunMode::DryRun),
            &mut RateLimiter::default(),
        )
        .unwrap();
        assert!(matches!(result.decision, Decision::Blocked(_)));
    }

    fn nmap_policy(mode: NmapMode) -> NmapPolicy {
        NmapPolicy {
            mode,
            authorized_targets: vec!["127.0.0.1".into()],
            ..NmapPolicy::default()
        }
    }

    #[test]
    fn nmap_defaults_to_dry_run_and_emits_required_json() {
        let mut log = HashChainLog::default();
        let action = execute_nmap(
            "127.0.0.1",
            false,
            &NmapPolicy {
                authorized_targets: vec!["127.0.0.1".into()],
                ..NmapPolicy::default()
            },
            &mut log,
        )
        .unwrap();
        assert_eq!(action.mode, "dry-run");
        assert_eq!(action.status, "planned");
        assert_eq!(
            serde_json::to_string(&action).unwrap(),
            r#"{"schema":"datya.action.v1","tool":"nmap","target":"127.0.0.1","mode":"dry-run","status":"planned"}"#
        );
        assert!(log.verify());
    }

    #[test]
    fn nmap_scope_is_checked_before_execution() {
        let mut log = HashChainLog::default();
        let action =
            execute_nmap("192.0.2.1", true, &nmap_policy(NmapMode::Execute), &mut log).unwrap();
        assert_eq!(action.mode, "execute");
        assert_eq!(action.status, "blocked");
        assert!(log.verify());
    }

    #[test]
    fn nmap_hash_chain_detects_tampering() {
        let mut log = HashChainLog::default();
        let _ = execute_nmap("127.0.0.1", false, &nmap_policy(NmapMode::DryRun), &mut log);
        let _ = execute_nmap("127.0.0.1", false, &nmap_policy(NmapMode::DryRun), &mut log);
        assert_eq!(log.events().len(), 2);
        assert!(log.verify());
        log.events[1].action.status = "completed";
        assert!(!log.verify());
    }
}
