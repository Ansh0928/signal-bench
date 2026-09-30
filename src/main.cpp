#include "controller.hpp"

#include <array>
#include <charconv>
#include <iostream>
#include <string>

namespace {
constexpr std::size_t max_line = 128;

// Consume oversized lines without retaining them. Subsequent frames remain usable.
bool read_line(std::string& line, bool& overflow) {
    line.clear();
    overflow = false;
    char c = 0;
    bool any = false;
    while (std::cin.get(c)) {
        any = true;
        if (c == '\n') break;
        if (line.size() < max_line) line.push_back(c);
        else overflow = true;
    }
    return any;
}

bool number(std::string_view value, std::uint64_t& result) {
    if (value.empty()) return false;
    // Reject signs and every non-decimal character, including embedded NULs.
    for (char c : value) if (c < '0' || c > '9') return false;
    const auto parsed = std::from_chars(value.data(), value.data() + value.size(), result);
    return parsed.ec == std::errc{} && parsed.ptr == value.data() + value.size();
}

std::size_t tokenize(std::string_view line, std::array<std::string_view, 5>& fields) {
    std::size_t count = 0;
    while (!line.empty()) {
        const auto first = line.find_first_not_of(" \t\r");
        if (first == std::string_view::npos) break;
        line.remove_prefix(first);
        if (count == fields.size()) return fields.size() + 1;
        const auto end = line.find_first_of(" \t\r");
        fields[count++] = line.substr(0, end);
        if (end == std::string_view::npos) break;
        line.remove_prefix(end);
    }
    return count;
}
} // namespace

int main(int argc, char** argv) {
    bool flawed = false;
    if (argc == 2 && std::string_view(argv[1]) == "--flawed") flawed = true;
    else if (argc != 1) {
        std::cerr << "Usage: controller [--flawed]\n";
        return 2;
    }
    bench::Controller controller;
    bench::Monitor monitor;
    std::uint64_t now_ms = 0;
    std::string line;
    line.reserve(max_line);
    bool overflow = false;
    while (read_line(line, overflow)) {
        std::string_view outcome = "invalid_frame";
        std::array<std::string_view, 5> fields{};
        const auto count = tokenize(line, fields);
        std::uint64_t a = 0, b = 0, c = 0;
        if (overflow) outcome = "frame_too_long";
        else if (count == 1 && fields[0] == "STATUS") outcome = "snapshot";
        else if (count == 2 && fields[0] == "HELLO" && number(fields[1], a)) {
            outcome = controller.hello(a);
            if (outcome == "session_opened") monitor.new_session(a);
        } else if (count == 4 && (fields[0] == "SET" || fields[0] == "SAMPLE") &&
                   number(fields[1], a) && number(fields[2], b) && number(fields[3], c)) {
            if (c > 100) outcome = "invalid_argument";
            else if (fields[0] == "SET") outcome = controller.set(a, b, static_cast<unsigned>(c), flawed);
            else outcome = monitor.observe(a, b, static_cast<unsigned>(c), now_ms);
        } else if (count == 2 && fields[0] == "CLOCK" && number(fields[1], a)) {
            if (a < now_ms) outcome = "clock_regression";
            else { now_ms = a; outcome = "clock_advanced"; }
        }
        // JSON fields are integers or fixed internal literals, never unescaped input.
        std::cout << "{\"outcome\":\"" << outcome
                  << "\",\"time_ms\":\"" << now_ms
                  << "\",\"session\":\"" << controller.session
                  << "\",\"last_id\":\"" << controller.last_id
                  << "\",\"device_level\":" << controller.level
                  << ",\"executions\":\"" << controller.executions
                  << "\",\"freshness\":\"" << monitor.freshness(now_ms)
                  << "\",\"observed_level\":";
        if (monitor.has_sample) std::cout << monitor.observed_level;
        else std::cout << "null";
        std::cout << "}" << std::endl;
    }
}
