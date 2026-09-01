#include "event_log.hpp"

#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace {
struct Tool { const char* id; const char* category; bool network; };
const Tool tools[] = {
 {"asset-inventory","discovery",false},{"dns-inspect","network",true},{"certificate-inspect","network",true},{"service-inventory","discovery",true},{"http-headers","web",true},{"web-config-audit","web",true},{"tls-audit","web",true},{"sast","code",false},{"dependency-audit","code",false},{"secrets-scan","code",false},{"hash-manifest","forensics",false},{"file-timeline","forensics",false},{"process-audit","defense",false},{"socket-audit","defense",false},{"persistence-audit","defense",false},{"integrity-check","defense",false},{"log-review","defense",false},{"auth-review","defense",false},{"firewall-status","defense",false},{"kernel-posture","defense",false},{"boot-integrity","defense",false},{"container-audit","cloud",false},{"image-sbom","cloud",false},{"iac-review","cloud",false},{"policy-lint","cloud",false},{"pcap-summary","network",false},{"flow-summary","network",true},{"route-review","network",false},{"arp-review","network",false},{"wifi-posture","wireless",false},{"wifi-survey","wireless",true},{"bluetooth-posture","wireless",false},{"usb-inventory","hardware",false},{"firmware-inventory","hardware",false},{"memory-triage","forensics",false},{"disk-triage","forensics",false},{"yara-review","malware",false},{"sandbox-report","malware",false},{"pe-review","reverse",false},{"elf-review","reverse",false},{"strings-review","reverse",false},{"symbols-review","reverse",false},{"diff-review","reverse",false},{"container-secrets","cloud",false},{"k8s-manifest","cloud",false},{"cloud-identity","cloud",false},{"cloud-storage","cloud",false},{"report-json","reporting",false},{"report-html","reporting",false},{"evidence-vault","reporting",false},{"scope-check","governance",false},{"rate-limit-check","governance",false},{"consent-check","governance",false},{"ai-local","assistant",false},{"github-import","workflow",true},{"lab-reset","lab",false},{"lab-status","lab",false},{"ctf-check","learn",false},{"training-report","learn",false},{"alert-timeline","defense",false},{"alert-explain","defense",false},{"package-provenance","integrity",false},{"update-verify","integrity",false},{"repro-check","integrity",false},{"privacy-check","privacy",false},{"dns-leak-check","privacy",true},{"proxy-check","privacy",false}
};
const Tool* find_tool(const std::string& id) { for (const auto& tool : tools) if (id == tool.id) return &tool; return nullptr; }
void help() { std::cout << "help | tools [category] | scope add <target> | scope list | run <tool> <target> | verify | quit\n"; }
}

int main(int argc, char** argv) {
    const std::string log_path = argc > 1 ? argv[1] : "/var/lib/datya/events.log";
    datya::EventLog log(log_path);
    std::set<std::string> scope;
    std::cout << "Datya Control C++17 | local-only | dry-run by default\n";
    help();
    for (std::string line; std::cout << "datya> " && std::getline(std::cin, line);) {
        std::istringstream input(line); std::string command, a, b; input >> command >> a >> b;
        if (command == "help") help();
        else if (command == "tools") { for (const auto& tool : tools) if (a.empty() || a == tool.category) std::cout << tool.id << " [" << tool.category << "] network=" << (tool.network ? "yes" : "no") << '\n'; std::cout << "catalog=" << (sizeof(tools) / sizeof(tools[0])) << " tools\n"; }
        else if (command == "scope" && a == "add" && !b.empty()) { scope.insert(b); std::cout << "scope added: " << b << '\n'; log.append("scope.add", b, a); }
        else if (command == "scope" && a == "list") { for (const auto& target : scope) std::cout << "authorized: " << target << '\n'; }
        else if (command == "run") {
            const Tool* tool = find_tool(a);
            const bool allowed = tool != nullptr && (!tool->network || scope.count(b) > 0);
            std::string error;
            if (!tool) std::cout << "blocked: unknown tool\n";
            else if (!allowed) std::cout << "blocked: target is outside authorized scope\n";
            else { const std::string payload = std::string("tool=") + tool->id + ";target=" + b + ";mode=dry-run"; if (!log.append("action.plan", payload, error)) std::cerr << "log error: " << error << '\n'; std::cout << "planned (no tool execution): " << payload << '\n'; }
        }
        else if (command == "verify") { std::string error; std::cout << (log.verify(error) ? "event log: VALID\n" : "event log: INVALID - " + error + "\n"); }
        else if (command == "quit" || command == "exit") break;
        else std::cout << "unknown command; type help\n";
    }
}
