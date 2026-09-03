//! Explicit root execution boundary.
//!
//! This crate does not elevate privileges, bypass Linux policy, or interpret a
//! shell string. A caller must already have the requested UID and must provide
//! an absolute executable path, explicit argv, and a confirmation token.

use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RootRequest {
    pub executable: PathBuf,
    pub args: Vec<String>,
    pub confirmation: String,
    pub audit_reason: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AuditRecord {
    pub schema: &'static str,
    pub operation: &'static str,
    pub executable: String,
    pub args: Vec<String>,
    pub reason: String,
    pub timestamp: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RootExecutionError {
    RelativeExecutable,
    MissingConfirmation,
    MissingReason,
    UnapprovedExecutable(String),
    ShellInvocationRejected,
    Io(String),
}

pub fn validate(request: &RootRequest, allowed: &[PathBuf]) -> Result<(), RootExecutionError> {
    if !request.executable.is_absolute() {
        return Err(RootExecutionError::RelativeExecutable);
    }
    if request.confirmation != confirmation_token(request) {
        return Err(RootExecutionError::MissingConfirmation);
    }
    if request.audit_reason.trim().is_empty() {
        return Err(RootExecutionError::MissingReason);
    }
    if request.executable.file_name().and_then(|v| v.to_str()) == Some("sh")
        || request.executable.file_name().and_then(|v| v.to_str()) == Some("bash")
    {
        return Err(RootExecutionError::ShellInvocationRejected);
    }
    if !allowed.iter().any(|path| path == &request.executable) {
        return Err(RootExecutionError::UnapprovedExecutable(
            request.executable.display().to_string(),
        ));
    }
    Ok(())
}

pub fn confirmation_token(request: &RootRequest) -> String {
    format!("RUN {}", request.executable.display())
}

pub fn audit_record(request: &RootRequest) -> AuditRecord {
    AuditRecord {
        schema: "datya.root-action.v1",
        operation: "execute",
        executable: request.executable.display().to_string(),
        args: request.args.clone(),
        reason: request.audit_reason.clone(),
        timestamp: SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs(),
    }
}

pub fn execute(request: &RootRequest, allowed: &[PathBuf]) -> Result<Output, RootExecutionError> {
    validate(request, allowed)?;
    Command::new(&request.executable)
        .args(&request.args)
        .env("DATYA_ROOT_ACTION", "explicit")
        .output()
        .map_err(|error| RootExecutionError::Io(error.to_string()))
}

pub fn is_under(path: &Path, root: &Path) -> bool {
    path.strip_prefix(root).is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request() -> RootRequest {
        let mut request = RootRequest {
            executable: PathBuf::from("/usr/bin/true"),
            args: vec![],
            confirmation: String::new(),
            audit_reason: "operator requested system check".into(),
        };
        request.confirmation = confirmation_token(&request);
        request
    }

    #[test]
    fn requires_existing_allowlist_and_confirmation() {
        let request = request();
        assert!(validate(&request, &[PathBuf::from("/usr/bin/true")]).is_ok());
        assert!(matches!(validate(&request, &[]), Err(RootExecutionError::UnapprovedExecutable(_))));
    }

    #[test]
    fn rejects_shell_interpretation() {
        let mut request = request();
        request.executable = PathBuf::from("/bin/sh");
        request.confirmation = confirmation_token(&request);
        assert_eq!(validate(&request, &[PathBuf::from("/bin/sh")]), Err(RootExecutionError::ShellInvocationRejected));
    }

    #[test]
    fn audit_has_stable_schema() {
        assert_eq!(audit_record(&request()).schema, "datya.root-action.v1");
    }
}
