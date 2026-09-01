#include "event_log.hpp"

#include <openssl/evp.h>
#include <fcntl.h>
#include <unistd.h>

#include <fstream>
#include <iomanip>
#include <sstream>
#include <vector>

namespace datya {

std::string sha256(const std::string& input) {
    EVP_MD_CTX* context = EVP_MD_CTX_new();
    if (context == nullptr) return {};
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int length = 0;
    const bool ok = EVP_DigestInit_ex(context, EVP_sha256(), nullptr) == 1 &&
                    EVP_DigestUpdate(context, input.data(), input.size()) == 1 &&
                    EVP_DigestFinal_ex(context, digest, &length) == 1;
    EVP_MD_CTX_free(context);
    if (!ok) return {};
    std::ostringstream output;
    for (unsigned int i = 0; i < length; ++i) output << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(digest[i]);
    return output.str();
}

std::uint64_t unix_time() { return static_cast<std::uint64_t>(std::time(nullptr)); }

EventLog::EventLog(std::filesystem::path path) : path_(std::move(path)) {}

bool EventLog::append(const std::string& type, const std::string& payload, std::string& error) {
    if (type.find('\t') != std::string::npos || payload.find_first_of("\t\n\r") != std::string::npos) { error = "event fields contain a forbidden delimiter"; return false; }
    std::uint64_t sequence = 0;
    std::string previous(64, '0');
    std::ifstream input(path_);
    std::string line;
    while (std::getline(input, line)) { if (!line.empty()) ++sequence; }
    if (sequence > 0) {
        std::ifstream tail(path_);
        std::string last_line;
        while (std::getline(tail, line)) { last_line = line; }
        std::istringstream fields(last_line);
        std::string ignored, timestamp, type_field, payload_field;
        std::getline(fields, ignored, '\t'); std::getline(fields, timestamp, '\t'); std::getline(fields, type_field, '\t'); std::getline(fields, payload_field, '\t'); std::getline(fields, previous, '\t'); std::getline(fields, previous, '\t');
    }
    const std::uint64_t timestamp = unix_time();
    const std::string material = std::to_string(sequence) + "\t" + std::to_string(timestamp) + "\t" + type + "\t" + payload + "\t" + previous;
    const std::string hash = sha256(material);
    if (hash.empty()) { error = "SHA-256 failed"; return false; }
    const std::string record = material + "\t" + hash + "\n";
    std::filesystem::create_directories(path_.parent_path());
    const int fd = ::open(path_.c_str(), O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0600);
    if (fd < 0) { error = "cannot open event log"; return false; }
    const ssize_t written = ::write(fd, record.data(), record.size());
    const bool synced = written == static_cast<ssize_t>(record.size()) && ::fsync(fd) == 0;
    ::close(fd);
    if (!synced) { error = "append or fsync failed"; return false; }
    return true;
}

bool EventLog::verify(std::string& error) const {
    std::ifstream input(path_);
    if (!input) { error = "event log does not exist"; return false; }
    std::string line, previous(64, '0');
    std::uint64_t expected_sequence = 0;
    while (std::getline(input, line)) {
        std::vector<std::string> fields; std::size_t start = 0;
        for (std::size_t end = 0; (end = line.find('\t', start)) != std::string::npos; start = end + 1) fields.push_back(line.substr(start, end - start));
        fields.push_back(line.substr(start));
        if (fields.size() != 6 || fields[0] != std::to_string(expected_sequence) || fields[4] != previous || sha256(line.substr(0, line.rfind('\t'))) != fields[5]) { error = "hash chain verification failed at sequence " + std::to_string(expected_sequence); return false; }
        previous = fields[5]; ++expected_sequence;
    }
    return true;
}

} // namespace datya
