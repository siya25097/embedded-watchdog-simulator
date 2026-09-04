# Milestone 4 — Recovery Mechanism

Date: 2026-09-04

## Goal

Automatically restart a task after the watchdog detects `STALLED`, track recovery attempts, and confirm recovery only after the restarted task emits a fresh heartbeat.

## Implementation

- [src/task_manager.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/task_manager.py)
  - Owns task thread lifecycle.
  - Starts individual tasks or all configured tasks.
  - Stops tasks cleanly and joins their threads.
  - Restarts a task by stopping the existing thread and creating a new one.
  - Keeps task configuration and optional fault injector wiring centralized.

- [src/recovery.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/recovery.py)
  - Receives stalled task notifications through `recover(task_id)`.
  - Tracks per-task recovery count and most recent recovery timestamp.
  - Records `RECOVERY_ATTEMPTED`, `RECOVERY_STARTED`, `RECOVERY_SUCCEEDED`, and `RECOVERY_FAILED` events.
  - Clears an active injected fault before restarting the task.
  - Prevents overlapping recovery attempts for the same task.

- [src/watchdog.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/watchdog.py)
  - Supports an `on_stalled` callback for recovery initiation.
  - Moves the task to `RECOVERING` when recovery accepts the stalled transition.
  - Supports an `on_healthy` callback.
  - Calls the healthy callback only after a fresh heartbeat is observed following `RECOVERING`.

## Recovery lifecycle

```text
HEALTHY
   ↓
fault injected
   ↓
LATE
   ↓
STALLED
   ↓
RECOVERING
   ↓ fresh heartbeat
HEALTHY
```

This satisfies BR-1: a restart alone is not treated as a successful recovery.

## Test coverage

- [tests/test_recovery.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/tests/test_recovery.py)
  - Injects a hang into a running task.
  - Verifies the watchdog reaches `RECOVERING`.
  - Verifies a recovery attempt is recorded.
  - Verifies the task returns to `HEALTHY` only after a fresh heartbeat.
  - Verifies the recovery count increments once.

## Validation

Run from the repository root:

```bash
PYTHONPATH=. python3 -m pytest -q
```

Result:

```text
17 passed in 3.68s
```

## Commands to verify the implementation

Run these commands from the repository root:

1. Run the complete automated suite:

```bash
cd /Users/khushi_makwana/VSCode/EMBEDDED_PROJECT
PYTHONPATH=. python3 -m pytest -q
```

2. Run only the recovery acceptance test:

```bash
PYTHONPATH=. python3 -m pytest -q tests/test_recovery.py -s
```

3. Run the related task, watchdog, fault-injection, and recovery tests:

```bash
PYTHONPATH=. python3 -m pytest -q \
  tests/test_task_simulation.py \
  tests/test_watchdog.py \
  tests/test_fault_injection.py \
  tests/test_fault_integration.py \
  tests/test_recovery.py
```

4. Inspect the implementation files:

```bash
python3 -m py_compile src/task_manager.py src/recovery.py src/watchdog.py src/task.py
git diff -- src/task_manager.py src/recovery.py src/watchdog.py src/task.py
```

5. Verify the recovery lifecycle interactively through the acceptance test output:

```bash
PYTHONPATH=. python3 -m pytest -q tests/test_recovery.py -s
```

The output should show a fault injection, a watchdog `STALLED` transition, recovery events, and fresh task heartbeats. The test should finish with one passing test.

## Limitations

- Maximum recovery attempts and `FAILED_PERMANENTLY` are not implemented; that remains the stretch goal from the development plan.
- Recovery events are stored in memory. Centralized application logging is planned for Milestone 5.
- Recovery is currently wired programmatically; CLI/dashboard controls will be added later.

## Next milestone

Milestone 5 should centralize heartbeats, faults, stalls, and recovery events through an `EventLogger`, with console/file output and optional persistence.
