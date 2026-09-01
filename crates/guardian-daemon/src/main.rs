use std::io::{self, BufRead};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, PartialEq, Eq)]
struct Alert {
    event: String,
    pid: Option<u32>,
    severity: &'static str,
    confidence: u8,
    message: String,
}

fn field<'a>(line: &'a str, key: &str) -> Option<&'a str> {
    line.split_whitespace()
        .find_map(|item| item.strip_prefix(&format!("{key}=")))
}

fn parse_event(line: &str) -> Option<Alert> {
    if !line.contains("datya_guardian") {
        return None;
    }
    let event = field(line, "event")?.to_string();
    let pid = field(line, "pid").and_then(|value| value.parse().ok());
    let (severity, confidence, message) = match event.as_str() {
        "exec" => (
            "info",
            85,
            format!("Process execution observed: {}", field(line, "path").unwrap_or("unknown")),
        ),
        "socket" => (
            "low",
            55,
            format!(
                "Socket state transition observed: {} -> {}",
                field(line, "old").unwrap_or("?"),
                field(line, "new").unwrap_or("?")
            ),
        ),
        _ => ("info", 35, "Unknown Guardian event observed".into()),
    };
    Some(Alert { event, pid, severity, confidence, message })
}

fn json_escape(value: &str) -> String {
    value.replace('\\', "\\\\").replace('"', "\\\"")
}

fn print_alert(alert: &Alert) {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or_default();
    let pid = alert.pid.map_or_else(|| "null".into(), |value| value.to_string());
    println!(
        "{{\"schema\":\"datya.alert.v1\",\"timestamp\":{},\"event\":\"{}\",\"pid\":{},\"severity\":\"{}\",\"confidence\":{},\"message\":\"{}\",\"action\":\"observe-only\"}}",
        timestamp,
        json_escape(&alert.event),
        pid,
        alert.severity,
        alert.confidence,
        json_escape(&alert.message)
    );
}

fn main() -> io::Result<()> {
    let stdin = io::stdin();
    for line in stdin.lock().lines() {
        if let Some(alert) = parse_event(&line?) {
            print_alert(&alert);
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_exec_event() {
        let alert = parse_event("datya_guardian event=exec pid=42 path=/usr/bin/ssh").unwrap();
        assert_eq!(alert.event, "exec");
        assert_eq!(alert.pid, Some(42));
        assert_eq!(alert.severity, "info");
    }

    #[test]
    fn ignores_unrelated_kernel_lines() {
        assert!(parse_event("kernel: unrelated message").is_none());
    }
}
