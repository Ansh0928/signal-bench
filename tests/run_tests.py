#!/usr/bin/env python3
"""Exercise actual C++ subprocesses through a deterministic simulated link."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import select
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


class Case:
    def __init__(self, executable, mode):
        args = [str(executable)] + (["--flawed"] if mode == "flawed" else [])
        self.process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1)
        self.events = []
        self.checks = []

    def send(self, frame, note="", drop_reply=False, **expected):
        self.process.stdin.write(frame + "\n")
        self.process.stdin.flush()
        ready, _, _ = select.select([self.process.stdout], [], [], 3)
        if not ready:
            raise RuntimeError("Controller did not respond within 3 wall-clock seconds")
        response = self.process.stdout.readline()
        if not response:
            raise RuntimeError("Controller exited before returning a response")
        result = json.loads(response)
        index = len(self.events)
        self.events.append({"frame": frame if len(frame) <= 160 else frame[:120] + "… [truncated for display]",
                            "note": note, "response": result,
                            "delivery": "reply_dropped" if drop_reply else "delivered"})
        for field, value in expected.items():
            # Decimal strings preserve uint64 values beyond JavaScript's range.
            if field in ("session", "last_id", "time_ms", "executions"):
                value = str(value)
            self.checks.append({"event": index, "field": field, "expected": value,
                                "actual": result.get(field), "passed": result.get(field) == value})
        # A lost acknowledgement really is withheld from the test's simulated sender.
        # The test instrument retains it as evidence of execution at the receiver.
        return None if drop_reply else result

    def drop(self, frame, note):
        self.events.append({"frame": frame, "note": note, "response": None, "delivery": "request_dropped"})

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
            raise RuntimeError("Controller failed to exit after EOF")
        error = self.process.stderr.read()
        self.process.stdout.close()
        self.process.stderr.close()
        if self.process.returncode != 0 or error:
            raise RuntimeError("Controller failed: " + error)


def baseline(c):
    c.send("HELLO 1", outcome="session_opened")
    c.send("SET 1 1 35", outcome="applied", device_level=35, executions=1)
    c.send("SAMPLE 1 1 35", outcome="sample_accepted", observed_level=35, freshness="fresh")


def lost_ack(c):
    c.send("HELLO 1")
    c.send("SET 1 1 35", "The controller executes; the simulated link discards its acknowledgement.",
           drop_reply=True)
    c.send("SET 1 1 35", "Sender retries the same command ID after receiving no acknowledgement.",
           outcome="duplicate", executions=1, device_level=35)


def old_session(c):
    c.send("HELLO 1")
    c.send("SET 1 1 20")
    c.send("HELLO 2", "Reconnect with a new session; device output is retained.", device_level=20)
    c.send("SET 1 2 80", "A delayed command from the previous connection arrives.",
           outcome="wrong_session", device_level=20, executions=1)


def reordered(c):
    c.send("HELLO 1")
    c.send("SET 1 2 60", outcome="applied")
    c.send("SET 1 1 10", "An earlier command arrives after a newer command.",
           outcome="old_command", device_level=60, executions=1)


def conflicting(c):
    c.send("HELLO 1")
    c.send("SET 1 1 20")
    c.send("SET 1 1 90", "The same ID must never identify two different payloads.",
           outcome="id_conflict", device_level=20, executions=1)


def stale_boundary(c):
    c.send("HELLO 1")
    c.send("SAMPLE 1 1 25")
    c.send("CLOCK 999", "Advance virtual time, without delivering telemetry.", freshness="fresh")
    c.send("CLOCK 1000", "The 1,000 ms limit is an educational requirement.",
           freshness="stale", observed_level=25)


def telemetry_recovery(c):
    c.send("HELLO 1")
    c.send("SAMPLE 1 1 20")
    c.send("CLOCK 1200", freshness="stale")
    c.send("SAMPLE 1 2 30", "A newer sample restores freshness.", freshness="fresh", observed_level=30)
    c.send("CLOCK 1500")
    c.send("SAMPLE 1 1 20", "Delayed telemetry cannot replace the latest sample.",
           outcome="old_sample", observed_level=30)
    c.send("CLOCK 2200", "Rejected telemetry must not refresh the freshness timer.", freshness="stale")


def lost_request(c):
    c.send("HELLO 1")
    c.drop("SET 1 1 75", "This frame never reaches the C++ subprocess.")
    c.send("STATUS", device_level=0, executions=0)
    c.send("SET 1 1 75", "The sender retries after loss.", outcome="applied", executions=1, device_level=75)


def handshake_retry(c):
    c.send("HELLO 1")
    c.send("SET 1 1 45")
    c.send("HELLO 1", "A retried handshake must preserve command history.",
           outcome="session_resumed", last_id=1)
    c.send("SET 1 1 45", outcome="duplicate", executions=1)


def malformed(c):
    c.send("HELLO 1")
    c.send("SET 1 1 40")
    for frame in ["", "SET 1 2", "SET 1 2 50 extra", "SET -1 2 30", "SET 1 2 NaN",
                  "SET 1 2 1.5", "SET 1 2 +5", "SET 1 18446744073709551616 50",
                  "SET 1 2 50\x00", "UNKNOWN"]:
        c.send(frame, outcome="invalid_frame", executions=1, device_level=40)
    for frame in ["SET 1 2 101", "SET 1 2 18446744073709551615", "SET 1 0 10"]:
        c.send(frame, outcome="invalid_argument", executions=1, device_level=40)


def oversized(c):
    c.send("HELLO 1")
    c.send("X" * 4096, "Consume an oversized frame without losing the next frame boundary.",
           outcome="frame_too_long", executions=0)
    c.send("SET 1 1 30", outcome="applied", device_level=30)


def no_session(c):
    c.send("SET 1 1 50", outcome="no_session", executions=0)
    c.send("HELLO 0", outcome="invalid_session", session=0)
    c.send("HELLO 2", outcome="session_opened")
    c.send("HELLO 1", outcome="invalid_session", session=2)


def telemetry_epoch(c):
    c.send("HELLO 1")
    c.send("SAMPLE 1 1 20")
    c.send("HELLO 2", freshness="unknown", observed_level=None)
    c.send("SAMPLE 1 2 80", "Telemetry from an earlier connection must not appear current.",
           outcome="wrong_session", freshness="unknown", observed_level=None)
    c.send("SAMPLE 2 1 20", outcome="sample_accepted", freshness="fresh")


def monotonic_clock(c):
    c.send("CLOCK 500")
    c.send("CLOCK 499", outcome="clock_regression", time_ms=500)


def disconnect(c):
    c.send("HELLO 1")
    c.send("SET 1 1 40")
    c.send("SAMPLE 1 1 40")
    c.send("CLOCK 5000", "Simulated link silence changes freshness, not the virtual indicator output.",
           device_level=40, executions=1, freshness="stale")
    c.send("HELLO 2", device_level=40, executions=1, freshness="unknown")


def bounds(c):
    c.send("HELLO 1")
    c.send("SET 1 1 0", outcome="applied", device_level=0)
    c.send("SET 1 2 100", outcome="applied", device_level=100)
    c.send("SET 1 18446744073709551615 50", outcome="applied", device_level=50,
           last_id=18446744073709551615)
    c.send("SET 1 0 70", "Sequence numbers never wrap silently.", outcome="invalid_argument", device_level=50)
    c.send("HELLO 2")
    c.send("SET 2 1 30", outcome="applied", device_level=30)


def whitespace(c):
    c.send("  HELLO\t1\r", outcome="session_opened")
    c.send("SET\t1  1 50\r", outcome="applied", device_level=50)


def rejected_sample(c):
    c.send("HELLO 1")
    c.send("SAMPLE 1 0 20", outcome="invalid_argument", freshness="unknown")
    c.send("SAMPLE 1 1 101", outcome="invalid_argument", freshness="unknown")
    c.send("SAMPLE 1 1 20", outcome="sample_accepted")
    c.send("CLOCK 900")
    c.send("SAMPLE 1 1 20", "A duplicate sample cannot extend freshness.", outcome="old_sample")
    c.send("CLOCK 1000", freshness="stale")


SCENARIOS = [
    ("normal", "Normal communication", "Establish a session, apply a command, and receive telemetry.", "R1", baseline),
    ("lost_ack", "Lost acknowledgement", "A missing reply must not cause duplicate execution.", "R2", lost_ack),
    ("old_session", "Delayed command after reconnect", "Reject commands belonging to an earlier session.", "R3", old_session),
    ("reordered", "Out-of-order commands", "An older command must not overwrite a newer one.", "R4", reordered),
    ("conflict", "Command ID conflict", "Reject a changed payload reusing the latest command ID.", "R2", conflicting),
    ("stale", "Telemetry freshness boundary", "Mark readings stale at exactly 1,000 ms without a new sample.", "R5", stale_boundary),
    ("recovery", "Telemetry recovery and reordering", "Recover on fresh telemetry without accepting delayed old samples.", "R5", telemetry_recovery),
    ("lost_request", "Lost command", "Dropping a request leaves the device unchanged; a retry can succeed.", "R1", lost_request),
    ("handshake", "Repeated handshake", "A handshake retry must not erase duplicate-command protection.", "R2", handshake_retry),
    ("malformed", "Malformed and invalid input", "Reject malformed frames and out-of-range values without mutations.", "R6", malformed),
    ("oversized", "Oversized input recovery", "Reject a long frame and correctly parse the next frame.", "R6", oversized),
    ("session", "Session establishment", "Require a session and reject zero or decreasing session epochs.", "R3", no_session),
    ("telemetry_epoch", "Old-session telemetry", "A new connection starts with unknown monitoring state.", "R5", telemetry_epoch),
    ("clock", "Monotonic test clock", "The deterministic fixture refuses backward time.", "R7", monotonic_clock),
    ("disconnect", "Link silence and reconnection", "A link interruption alone never changes the indicator setting.", "R8", disconnect),
    ("bounds", "Value and sequence boundaries", "Exercise 0, 100 and the maximum 64-bit command ID.", "R6", bounds),
    ("whitespace", "Serial line formatting", "Accept tabs, spacing, and CRLF-compatible frames.", "R6", whitespace),
    ("sample_validation", "Invalid and duplicate telemetry", "Invalid or duplicate samples cannot make data fresh.", "R5", rejected_sample),
]


def source_digest():
    digest = hashlib.sha256()
    for folder in ("src", "tests"):
        for path in sorted((ROOT / folder).glob("*")):
            if path.is_file() and path.suffix in (".cpp", ".hpp", ".py"):
                digest.update(str(path.relative_to(ROOT)).encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, default=ROOT / "build/controller")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/results.json")
    args = parser.parse_args()
    # Fail fast when an executable or its sanitizer runtime cannot start here.
    try:
        smoke = subprocess.run([str(args.binary.resolve())], input="STATUS\n", text=True,
                               capture_output=True, timeout=5)
        if smoke.returncode != 0 or smoke.stderr or json.loads(smoke.stdout).get("outcome") != "snapshot":
            raise RuntimeError(smoke.stderr or "Unexpected startup response")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("Cannot start controller executable:", exc, file=sys.stderr)
        return 2
    results = []
    for mode in ("flawed", "protected"):
        for key, title, description, requirement, function in SCENARIOS:
            case = Case(args.binary.resolve(), mode)
            error = None
            try:
                function(case)
            except Exception as exc:
                error = str(exc)
            finally:
                try:
                    case.close()
                except Exception as exc:
                    error = str(exc)
            passed = error is None and bool(case.checks) and all(check["passed"] for check in case.checks)
            results.append({"id": key, "title": title, "description": description,
                            "requirement": requirement, "mode": mode, "passed": passed,
                            "error": error, "checks": case.checks, "events": case.events})
            print("{:<10} {:<5} {}".format(mode, "PASS" if passed else "FAIL", title))
    expected_failures = {"lost_ack", "old_session", "conflict", "handshake"}
    actual_failures = {r["id"] for r in results if r["mode"] == "flawed" and not r["passed"]}
    protected_ok = all(r["passed"] for r in results if r["mode"] == "protected")
    no_errors = all(r["error"] is None for r in results)
    verified = protected_ok and actual_failures == expected_failures and no_errors
    document = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": source_digest(),
        "binary_sha256": hashlib.sha256(args.binary.read_bytes()).hexdigest(),
        "environment": "Native C++17 subprocess; stdin/stdout transport; deterministic virtual clock",
        "scope": "Educational simulation. No physical hardware or medical-device integration tested.",
        "verification_passed": verified,
        "scenario_count": len(SCENARIOS),
        "assertion_count": sum(len(r["checks"]) for r in results),
        "expected_flawed_failures": sorted(expected_failures),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + "\n")
    print("\n{} scenarios × 2 implementations; {} assertions".format(len(SCENARIOS), document["assertion_count"]))
    print("Verification:", "PASS (protected mode passes; flawed mode fails the four expected scenarios)" if verified else "FAIL")
    return 0 if verified else 1


if __name__ == "__main__":
    sys.exit(main())
