# Milestone 5 — Event Logging

Date: 2026-09-04

## Goal

Provide one thread-safe event history for the simulator so heartbeats, injected faults, stall detection, and recovery activity can be inspected chronologically.

## Implementation

- [src/event_logger.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/event_logger.py)
  - Adds `EventLogger.log()` for structured events.
  - Stores events in a thread-safe in-memory list.
  - Supports chronological event retrieval.
  - Uses Python's standard-library `logging` module for console/configured-handler output.

- [src/task.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/task.py)
  - Optionally records `HEARTBEAT` events.

- [src/fault_injector.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/fault_injector.py)
  - Optionally forwards fault injection, duplicate-injection, clear, and unknown-task events.

- [src/watchdog.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/watchdog.py)
  - Optionally forwards `STALL_DETECTED` events.

- [src/recovery.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/recovery.py)
  - Optionally forwards recovery attempted, started, succeeded, and failed events.

- [src/task_manager.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/task_manager.py)
  - Passes the shared logger into newly created task threads.

## Usage

```python
import logging

from src.event_logger import EventLogger

logging.basicConfig(level=logging.INFO)
event_logger = EventLogger()
event_logger.log("FAULT_INJECTED", "task-a", {"fault_type": "hang"})

print(event_logger.chronological())
```

The logger is optional, so existing Milestone 1–4 callers continue to work without modification.

## Validation

Run from the repository root:

```bash
PYTHONPATH=. python3 -m pytest -q
```

Result:

```text
19 passed in 3.68s
```

The event logger test verifies structured event storage and chronological ordering. Existing task, watchdog, fault-injection, and recovery tests also remain passing.

## Event format

Each event contains:

```text
timestamp
event_type
task_id
details
```

## Limitations

- Event history is currently in memory only.
- File/JSON-lines or SQLite persistence remains optional future work.
- The dashboard has not yet been built; Milestone 6 will consume the event history.
