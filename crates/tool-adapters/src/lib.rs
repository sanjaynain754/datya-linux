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

pub struct RateLimiter {
    last_run: Option<Instant>,
}
impl Default for RateLimiter {
    fn default() -> Self {
        Self { last_run: None }
    }
}
impl RateLimiter {
    fn allow(&mut self, interval: Duration) -> bool {
        let now = Instant::now();
        let allowed = self
            .last_run
            .map_or(true, |last| now.duration_since(last) >= interval);
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
}
