use std::fs;
use std::io;
use std::path::Path;

#[derive(Debug, Default, PartialEq, Eq)]
pub struct SystemEvidence {
    pub kernel: String,
    pub architecture: String,
    pub os_name: String,
    pub os_version: String,
    pub cpu_model: String,
    pub memory_bytes: Option<u64>,
    pub virtualization: Option<String>,
    pub secure_boot: Option<bool>,
}

fn read_trimmed(path: impl AsRef<Path>) -> Option<String> {
    fs::read_to_string(path).ok().map(|value| value.trim().to_string())
}

fn parse_os_release() -> (String, String) {
    let content = read_trimmed("/etc/os-release").unwrap_or_default();
    let mut name = String::from("unknown");
    let mut version = String::from("unknown");
    for line in content.lines() {
        if let Some(value) = line.strip_prefix("PRETTY_NAME=") {
            name = value.trim_matches('"').to_string();
        } else if let Some(value) = line.strip_prefix("VERSION_ID=") {
            version = value.trim_matches('"').to_string();
        }
    }
    (name, version)
}

fn parse_meminfo() -> Option<u64> {
    let content = read_trimmed("/proc/meminfo")?;
    let line = content.lines().find(|line| line.starts_with("MemTotal:"))?;
    let kb = line.split_whitespace().nth(1)?.parse::<u64>().ok()?;
    Some(kb * 1024)
}

fn cpu_model() -> String {
    read_trimmed("/proc/cpuinfo")
        .and_then(|content| {
            content.lines().find_map(|line| {
                line.strip_prefix("model name\t: ")
                    .or_else(|| line.strip_prefix("Hardware\t: "))
                    .map(str::to_string)
            })
        })
        .unwrap_or_else(|| "unknown".into())
}

fn secure_boot_state() -> Option<bool> {
    let value = fs::read("/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c").ok()?;
    Some(value.last().copied() == Some(1))
}

pub fn collect() -> io::Result<SystemEvidence> {
    let (os_name, os_version) = parse_os_release();
    Ok(SystemEvidence {
        kernel: read_trimmed("/proc/sys/kernel/osrelease").unwrap_or_else(|| "unknown".into()),
        architecture: std::env::consts::ARCH.into(),
        os_name,
        os_version,
        cpu_model: cpu_model(),
        memory_bytes: parse_meminfo(),
        virtualization: read_trimmed("/sys/devices/virtual/dmi/id/product_name"),
        secure_boot: secure_boot_state(),
    })
}

#[cfg(test)]
mod tests {
    #[test]
    fn architecture_is_known_at_compile_time() {
        assert!(!std::env::consts::ARCH.is_empty());
    }
}
