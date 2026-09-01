use datya_sensor::collect;

fn json_string(value: &str) -> String {
    format!("\"{}\"", value.replace('\\', "\\\\").replace('"', "\\\""))
}

fn main() {
    match collect() {
        Ok(evidence) => {
            let memory = evidence
                .memory_bytes
                .map_or_else(|| "null".into(), |value| value.to_string());
            let secure_boot = evidence
                .secure_boot
                .map_or_else(|| "null".into(), |value| value.to_string());
            let virtualization = evidence
                .virtualization
                .as_deref()
                .map_or_else(|| "null".into(), json_string);
            println!(
                "{{\"schema\":\"datya.system.v1\",\"kernel\":{},\"architecture\":{},\"os_name\":{},\"os_version\":{},\"cpu_model\":{},\"memory_bytes\":{},\"virtualization\":{},\"secure_boot\":{}}}",
                json_string(&evidence.kernel),
                json_string(&evidence.architecture),
                json_string(&evidence.os_name),
                json_string(&evidence.os_version),
                json_string(&evidence.cpu_model),
                memory,
                virtualization,
                secure_boot
            );
        }
        Err(error) => {
            eprintln!("datya-sensor: unable to collect local evidence: {error}");
            std::process::exit(1);
        }
    }
}
