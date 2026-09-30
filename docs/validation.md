# Validation record

Verified locally on 30 September 2026, macOS arm64, Apple Clang 17, Python 3.9.6.

| Check | Result |
| --- | --- |
| C++17 build with Wall, Wextra, Wpedantic and Werror | Pass |
| Protected controller | 18/18 scenarios pass |
| Deliberately flawed controller | Exactly four scenarios fail, as required by the suite |
| Assertions across both modes | 250 evaluated |
| UndefinedBehaviorSanitizer build and complete suite | Pass, no diagnostics |
| AddressSanitizer | Not verified locally: runtime hangs even on an empty main() |
| Browser controls | Scenario selection, implementation comparison, trace replay/pause/step/show-all verified |
| Local Run tests button | Verified: compiles/runs C++ and refreshes captured evidence |
| Exports | CSV and JSON files saved; JSON checked for exact 64-bit command IDs |
| Mobile layout | Checked at 390 px; no page-width overflow |
| Browser console | No errors or warnings observed during the tested flows |
| Local runner origin check | Cross-origin POST rejected |
| GitHub Actions | Workflow included; remote execution not yet verified |
| ESP32, RTOS, electrical interface, clinical operation | Not implemented or tested |

`reports/results.json` is the machine-readable evidence for the normal build.
`build/ubsan-results.json` contains the local undefined-behaviour sanitizer run
(the build directory is intentionally ignored by Git).

The AddressSanitizer startup failure was independently reproduced with a program
containing only `int main() { return 0; }`. This isolates the observed startup
problem from the controller logic; its environmental root cause is not established.
The Linux CI workflow is configured to run AddressSanitizer and
UndefinedBehaviorSanitizer once the repository is hosted, but that future run is
not counted as a passed check.

The scenario count is not a coverage percentage or exhaustive safety claim. The
failure scenarios are deterministic and bounded. Hardware timing, reboot
persistence, authentication and source-age telemetry remain outside current scope.
