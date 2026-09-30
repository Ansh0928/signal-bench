# Understand the project before your interview

## Start with a ten-minute experiment

Run `make demo`, open `reports/index.html`, and select **Lost acknowledgement**.
Read all three messages. Compare the execution counter in flawed and protected
modes. Both may display the same final indicator level, but only one avoids
executing the duplicate command.

## Talk to the C++ program yourself

```sh
make build
./build/controller
```

Type each line, followed by Enter:

```text
HELLO 1
SET 1 1 35
SET 1 1 35
HELLO 2
SET 1 2 80
STATUS
```

The second SET should return `duplicate`. The SET after HELLO 2 should return
`wrong_session`. Press Ctrl+D to close input. Run `./build/controller --flawed`
and repeat to see why the tests fail.

## Read the code in this order

1. `src/controller.hpp`: `Controller::set`. The early `return` statements reject
   commands before the output changes. `std::uint64_t` is an unsigned 64-bit
   integer. `std::string_view` references a string without allocating a new one.
2. `Controller::hello`. The same session is a retry; a larger session is a new
   connection. A new session does not change the virtual indicator level.
3. `Monitor::observe` and `freshness`. Explain why retaining an old number and
   marking it stale is different from treating it as a current measurement.
4. `tests/run_tests.py`: `lost_ack` and `old_session`. These send real bytes into a
   compiled subprocess. The expected outcomes are asserted independently.
5. `src/main.cpp`. This is the adapter between text messages and the small core.

## Make three changes yourself

### A. Add a negative test

Add a scenario that sends `SET 1 3 80` before `HELLO 1`. Expect `no_session` and
zero executions. Run the suite. Then explain why a valid-looking command can
still be invalid in the current state.

### B. Test a new timeout

Change the stale threshold to 1,500 ms. First run the existing tests and observe
the failures. Update the stated requirement and its boundary checks together.
Do not simply change every expected result to match the implementation: decide
the intended behaviour first.

### C. Document a remaining limitation

Restart the process and observe that it has forgotten the session. Write a short
design note proposing how boot identifiers could distinguish old messages from
messages sent after a restart. Do not claim it is solved until implemented and
tested.

## Questions you should be able to answer

- Why can a lost reply make the sender unsure whether its command executed?
- Why use a command ID as well as a session ID?
- Why does the flawed example increment the counter twice even when the level
  looks unchanged?
- Why do we reject an old command instead of applying it in arrival order?
- What makes this a simulation rather than a hardware test?
- What are virtual time and receipt-based freshness? What do they fail to measure?
- What code would need to change when moving to an ESP32?
- What did AI help create, and what have you personally reviewed, changed, and tested?

## Hardware step, when ready

Use a board's serial interface and an LED as the output. Port the fixed-size
core first, retain its tests, then add board-specific serial and GPIO code. RTOS
tasks/queues and measured timing can follow. No board or firmware port is included
in this version, so do not list those as completed experience yet.

## Practise Git while learning

The initial project is on the local branch `codex/signal-bench`. After completing
an exercise, inspect `git diff`, run `make demo`, and commit the specific files
you changed with a message explaining the behaviour. Use `git log --oneline`
to review that history. No public remote has been created by this setup.
