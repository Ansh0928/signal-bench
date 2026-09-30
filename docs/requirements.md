# Requirements and protocol

These are educational project requirements, not BiVACOR specifications.

| ID | Requirement | Scenarios |
| --- | --- | --- |
| R1 | A valid command in an established session sets the virtual indicator; an undelivered request has no effect. | normal, lost_request |
| R2 | Retrying the latest ID with the same payload does not execute it twice. Reusing it with a different payload is rejected. A repeated handshake preserves this history. | lost_ack, conflict, handshake |
| R3 | Non-zero session IDs increase within a process lifetime. A command must match the active session. | old_session, session |
| R4 | A command older than the last applied command cannot overwrite it. | reordered |
| R5 | Telemetry starts unknown, becomes fresh on a valid newer sample, and becomes stale at age >= 1,000 virtual ms. Invalid, duplicate, older, or old-session samples cannot refresh it. A new session resets monitoring to unknown. | stale, recovery, telemetry_epoch, sample_validation |
| R6 | Reject malformed/oversized frames, integer overflow, zero command IDs, and levels outside 0–100 without changing controller state. Support whitespace and CRLF framing. | malformed, oversized, bounds, whitespace |
| R7 | The test-fixture clock is monotonic. | clock |
| R8 | Link silence and establishing a new session alone do not change the virtual indicator level. | disconnect |

## Line protocol

One ASCII request per newline, maximum 128 bytes excluding newline. Fields are
separated by spaces/tabs; an optional carriage return is accepted. Decimal
integers are unsigned 64-bit with no sign, fraction, or exponent. The indicator
value is further restricted to 0–100. Every line returns one JSON response.

| Input | Meaning |
| --- | --- |
| `HELLO <session>` | Establish a newer session, or acknowledge the current one without resetting its command history. |
| `SET <session> <id> <level>` | Apply a setting under the session/ordering/duplicate rules. |
| `STATUS` | Return a diagnostic snapshot. |
| `SAMPLE <session> <sequence> <level>` | Fixture delivers telemetry to the monitoring model. Does not change actual indicator output. |
| `CLOCK <absolute_ms>` | Fixture advances deterministic virtual time. Does not sleep. |

The JSON reply includes `outcome`, `time_ms`, `session`, `last_id`, `device_level`,
`executions`, `freshness`, and `observed_level`. `device_level` is instrumented
receiver state; `observed_level` is the possibly stale telemetry value. They are
intentionally separate. `observed_level` is null before receiving a valid sample
in the current session.

The 64-bit fields (`time_ms`, `session`, `last_id`, `executions`) are encoded as
decimal JSON strings, preserving values beyond JavaScript's exact integer range.
Indicator levels remain JSON numbers.

## Lost acknowledgement, step by step

```text
HELLO 1       -> session_opened
SET 1 1 35    -> applied; executions=1 [reply discarded by test link]
SET 1 1 35    -> duplicate; executions=1
```

The test runner captures the discarded reply for its own evidence but withholds it
from the simulated sender. A dropped request is never written into the process.
Delay/reordering is implemented by controlling delivery order. This is functional
transport simulation over OS pipes, not an electrical fault injection rig.

## State and memory

The controller remembers the active session, latest command ID/payload, indicator
level, and execution counter. The monitor remembers its session, latest sequence,
receipt time, last observed level, and whether it has received a sample.
This storage is bounded independently of message count. Native parsing retains at
most 128 input bytes and consumes the rest of an oversized frame up to newline.
The Python runner and browser intentionally retain full test histories.

## Assumptions and untested conditions

- One trusted sender selects monotonically increasing session IDs. No adversarial
  authentication, CRC, packet framing over binary serial, or secure channel.
- A session change clears command history but retains indicator output.
- Process restarts clear all state. No persistent epochs or crash recovery.
- The highest command ID cannot wrap. Establish a newer session to restart IDs.
  Exhausting the session ID space is outside this prototype's supported operation.
- No concurrency/RTOS scheduling, brownouts, real cable disconnects, battery
  switching, motor control, physiological behaviour, or real-time guarantees.
- Receipt-based freshness does not prove a sample was acquired recently.
- These tests do not claim regulatory compliance or exhaustive verification.
