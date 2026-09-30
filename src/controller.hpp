#pragma once

#include <cstdint>
#include <string_view>

namespace bench {

// A virtual indicator, not a physiological model or medical-device controller.
// State storage is fixed size; the core does not allocate or depend on an OS.
struct Controller {
    std::uint64_t session = 0;
    std::uint64_t last_id = 0;
    unsigned last_level = 0;
    unsigned level = 0;
    std::uint64_t executions = 0;

    std::string_view hello(std::uint64_t proposed) {
        if (proposed == 0 || proposed < session) return "invalid_session";
        if (proposed == session) return "session_resumed";
        session = proposed;
        last_id = 0;
        last_level = 0;
        return "session_opened";
    }

    std::string_view set(std::uint64_t epoch, std::uint64_t id,
                         unsigned requested, bool flawed) {
        if (id == 0 || requested > 100) return "invalid_argument";
        if (session == 0) return "no_session";
        // Deliberately flawed mode removes two guards for the demonstration.
        if (!flawed && epoch != session) return "wrong_session";
        if (id < last_id) return "old_command";
        if (id == last_id && !flawed) {
            return requested == last_level ? "duplicate" : "id_conflict";
        }
        last_id = id;
        last_level = requested;
        level = requested;
        ++executions;
        return "applied";
    }
};

struct Monitor {
    static constexpr std::uint64_t stale_after_ms = 1000;
    std::uint64_t session = 0;
    std::uint64_t last_sequence = 0;
    std::uint64_t received_at_ms = 0;
    unsigned observed_level = 0;
    bool has_sample = false;

    void new_session(std::uint64_t epoch) {
        session = epoch;
        last_sequence = 0;
        has_sample = false;
    }

    std::string_view observe(std::uint64_t epoch, std::uint64_t sequence,
                             unsigned value, std::uint64_t now_ms) {
        if (epoch == 0 || epoch != session) return "wrong_session";
        if (sequence == 0 || value > 100) return "invalid_argument";
        if (sequence <= last_sequence) return "old_sample";
        last_sequence = sequence;
        received_at_ms = now_ms;
        observed_level = value;
        has_sample = true;
        return "sample_accepted";
    }

    std::string_view freshness(std::uint64_t now_ms) const {
        if (!has_sample) return "unknown";
        return now_ms - received_at_ms >= stale_after_ms ? "stale" : "fresh";
    }
};

} // namespace bench
