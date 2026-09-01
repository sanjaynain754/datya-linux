use std::fs;
use std::io;
use std::net::Ipv4Addr;

#[derive(Debug, PartialEq, Eq)]
struct SocketSignal {
    local: String,
    remote: String,
    state: String,
}

fn parse_ipv4(hex: &str) -> Option<Ipv4Addr> {
    if hex.len() != 8 {
        return None;
    }
    let bytes: Vec<u8> = (0..8)
        .step_by(2)
        .map(|i| u8::from_str_radix(&hex[i..i + 2], 16).ok())
        .collect::<Option<Vec<_>>>()?;
    Some(Ipv4Addr::new(bytes[3], bytes[2], bytes[1], bytes[0]))
}

fn parse_endpoint(value: &str) -> Option<String> {
    let (address, port) = value.split_once(':')?;
    let ip = parse_ipv4(address)?;
    let port = u16::from_str_radix(port, 16).ok()?;
    Some(format!("{ip}:{port}"))
}

fn parse_tcp_table(contents: &str) -> Vec<SocketSignal> {
    contents
        .lines()
        .skip(1)
        .filter_map(|line| {
            let fields: Vec<_> = line.split_whitespace().collect();
            let local = parse_endpoint(fields.get(1)?)?;
            let remote = parse_endpoint(fields.get(2)?)?;
            let state = fields.get(3)?.to_string();
            Some(SocketSignal { local, remote, state })
        })
        .collect()
}

fn read_tcp_signals() -> io::Result<Vec<SocketSignal>> {
    let contents = fs::read_to_string("/proc/net/tcp")?;
    Ok(parse_tcp_table(&contents))
}

fn main() -> io::Result<()> {
    for signal in read_tcp_signals()? {
        println!(
            "{{\"source\":\"procfs\",\"local\":\"{}\",\"remote\":\"{}\",\"state\":\"{}\"}}",
            signal.local, signal.remote, signal.state
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_procfs_ipv4_endpoint() {
        assert_eq!(parse_endpoint("0100007F:1F90"), Some("127.0.0.1:8080".into()));
    }

    #[test]
    fn parses_tcp_row() {
        let table = "  sl  local_address rem_address   st\n  0: 0100007F:1F90 00000000:0000 0A 00000000:0000 00:00000000 00000000   0        0 1 2";
        assert_eq!(parse_tcp_table(table), vec![SocketSignal {
            local: "127.0.0.1:8080".into(),
            remote: "0.0.0.0:0".into(),
            state: "0A".into(),
        }]);
    }
}
