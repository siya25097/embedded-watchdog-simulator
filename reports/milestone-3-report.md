# Milestone 3 — Fault Injection

Date: 2026-09-03

## Goal

Provide a controlled way to inject faults into a named simulated task, observe the resulting heartbeat behavior, and verify that the watchdog detects a hang. The implementation covers hang faults, communication failures, event recording, clearing faults, and duplicate-injection handling.

## Implementation

- [src/fault_injector.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/fault_injector.py)
  - Supports `hang` and `comm_failure`.
  - Tracks active faults by task ID.
  - Records timestamped fault events.
  - Rejects unsupported fault types.
  - Ignores unknown task IDs with a logged event.
  - Ignores a second active fault for the same task and logs `double_injection_ignored`.
  - Supports clearing an active fault.
  - Uses a lock for concurrent fault access.

- [src/task.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/task.py)
  - Accepts an optional `FaultInjector`.
  - A `hang` fault suppresses all future heartbeats while the task thread remains alive.
  - A `comm_failure` fault drops heartbeats while allowing the task loop to continue.
  - Clearing the fault allows heartbeats to resume.
  - Renamed the internal stop event to avoid conflicting with `threading.Thread.join()`.

- [tests/test_fault_injection.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/tests/test_fault_injection.py)
  - Tests hang injection.
  - Tests communication-failure injection.
  - Tests duplicate injection handling.
  - Tests clearing a fault.
  - Tests unknown-task handling.

- [tests/test_fault_integration.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/tests/test_fault_integration.py)
  - Verifies that a hang stops registry updates and leads to watchdog `STALLED`.
  - Verifies that communication failure stops heartbeats temporarily and resumes after clearing.

## Usage

```python
from src.fault_injector import FaultInjector

injector = FaultInjector(["task-a"])
injector.inject_hang("task-a")
injector.clear_fault("task-a")
```

To inject a communication failure:

```python
injector.inject_comm_failure("task-a")
```

## Validation

Run the complete relevant suite from the repository root:

```bash
PYTHONPATH=. python3 -m pytest -q
```

Validation result:

```text
10 passed in 2.60s
```

## Requirement coverage

- FR-13: hang injection is implemented and stops heartbeat emission.
- FR-14: communication-failure injection drops heartbeat delivery without killing the task.
- FR-15: injected faults are recorded with task ID, fault type, action, and timestamp.
- FR-16: faults can be cleared manually.
- E-3: duplicate injection is ignored and logged rather than causing undefined behavior.

## Limitations

- Fault injection is currently a Python API, not yet a standalone CLI or dashboard control.
- Fault events are held in memory and printed to stdout; centralized event logging is planned for Milestone 5.
- Automatic recovery is not implemented until Milestone 4.

## Next milestone

Milestone 4 should add `TaskManager` and `RecoveryManager` so a watchdog `STALLED` event can restart a task and confirm recovery only after a fresh heartbeat.
