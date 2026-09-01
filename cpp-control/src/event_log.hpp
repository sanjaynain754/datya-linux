#pragma once

#include <cstdint>
#include <filesystem>
#include <string>

namespace datya {

struct SecurityEvent {
    std::uint64_t sequence;
    std::uint64_t timestamp;
    std::string type;
    std::string payload;
    std::string previous_hash;
    std::string hash;
};

class EventLog {
public:
    explicit EventLog(std::filesystem::path path);
    bool append(const std::string& type, const std::string& payload, std::string& error);
    bool verify(std::string& error) const;
    const std::filesystem::path& path() const noexcept { return path_; }

private:
    std::filesystem::path path_;
};

std::string sha256(const std::string& input);
std::uint64_t unix_time();

} // namespace datya
