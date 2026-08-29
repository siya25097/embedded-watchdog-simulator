# Milestone 1 — Core Task Simulation

Date: 2026-08-29

Summary
-------
This document summarizes the Milestone 1 implementation: a small, testable core that simulates periodic "tasks" (threads) emitting heartbeats and records them in a thread-safe registry. The goal was to implement FR-1..FR-5 from the SRS: Task threads with configurable period and heartbeats, a Registry for last-heartbeat state, config loading, a throwaway runner script, and a pytest that verifies basic heartbeat behavior.

Files added/updated
-------------------
- [requirements.txt](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/requirements.txt)
- [src/__init__.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/__init__.py)
- [src/task.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/task.py) — Task thread implementation
- [src/registry.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/registry.py) — thread-safe Registry with helper
- [config/tasks.yaml](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/config/tasks.yaml) — sample tasks with period, timeout_ms, missed_heartbeat_threshold
- [scripts/run_tasks.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/scripts/run_tasks.py) — demo runner and config loader with validation
- [tests/test_task_simulation.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/tests/test_task_simulation.py) — pytest verifying 3 tasks emit recent heartbeats

What was implemented
---------------------
1. Task (src/task.py)
   - Subclass of threading.Thread, runs as a daemon.
   - Configurable period (seconds) and optional work_fn.
   - Emits a heartbeat to Registry every cycle and prints a heartbeat line to stdout.
   - stop() method to request clean shutdown; sleeps in small chunks to be responsive.

2. Registry (src/registry.py)
   - Thread-safe storage of last-heartbeat timestamps per task_id using a Lock.
   - Methods: heartbeat(task_id), get(task_id) → raw timestamp, all() → shallow copy, seconds_since_heartbeat(task_id) → seconds or None.
   - The seconds_since_heartbeat helper centralizes time math for later Watchdog use.

3. Config loader & validation (scripts/run_tasks.py)
   - Loads config/tasks.yaml and validates required fields.
   - Enforces: id present, period > 0, timeout_ms positive, missed_heartbeat_threshold non-negative.
   - Defaults: timeout_ms → int(period * 2000) (2× period, ms), missed_heartbeat_threshold → 2
   - SRS V-1 check added: rejects any task where timeout_ms <= period*1000 to avoid misconfiguration where timeout is too short.

4. Demo runner (scripts/run_tasks.py)
   - Starts all configured tasks, prints start messages and heartbeats to console, traps SIGINT to stop tasks cleanly.

5. Test (tests/test_task_simulation.py)
   - Starts 3 short-period tasks and asserts Registry recorded recent heartbeats.
   - Verified by running pytest after installing requirements.

How to run locally
------------------
1. Create & activate virtualenv (recommended):
   - python3 -m venv .venv
   - source .venv/bin/activate
2. Install dependencies:
   - pip install -r requirements.txt
3. Run the demo script (prints heartbeats):
   - python3 scripts/run_tasks.py OR PYTHONPATH=. python3 scripts/run_tasks.py
   - Stop: Ctrl+C
4. Run unit tests:
   - python3 -m pytest (Use my current Python 3 environment to run all pytest tests in the project and show me a short summary.)
   - To run just the milestone test: python3 -m pytest -q tests/test_task_simulation.py
   - 

Verification performed
----------------------
- `python3 -m pytest tests/test_task_simulation.py` passed in the current environment after pip installing from requirements.txt.
- Manual inspection run: running scripts/run_tasks.py prints heartbeat lines for each configured task at their expected intervals.

Design notes & rationale
------------------------
- Simplicity: Task prints heartbeats and calls Registry. This is purposefully minimal for a foundation that will be built upon by the Watchdog and Recovery components.
- Config defaults: timeout_ms defaulted to 2× period (ms) as a conservative starting tolerance; miss threshold default=2 to avoid classifying transient jitter as STALLED.
- SRS V-1 validation: rejecting timeout <= period avoids an obvious configuration footgun and will reduce confusing behavior when the Watchdog is implemented.
- Registry.seconds_since_heartbeat added to centralize time math for health checks and reduce duplication in downstream code.

Limitations and known gaps
--------------------------
- No Watchdog yet (Milestone 2) — health classification and STALLED detection not implemented.
- Logging: print() used for heartbeats; no structured logging or EventLogger yet (Milestone 5).
- No persistence or dashboard.
- Tests are intentionally minimal; more unit tests are needed for config validation, registry concurrency, task stop behavior, and edge cases.

Suggested next steps (Milestone 2 prep)
--------------------------------------
1. Implement Watchdog (watchdog.py) that:
   - Polls Registry periodically, uses seconds_since_heartbeat and configured timeout_ms/missed_heartbeat_threshold to classify HEALTHY/LATE/STALLED.
   - Emits STALLED transitions to an EventLogger and triggers RecoveryManager (later milestone).
2. Add unit tests for Watchdog: simulate a task stopping heartbeats and assert STALLED within expected time.
3. Add tests for config validation (e.g., ensure ValueError when timeout_ms <= period*1000).
4. Replace print() with python logging and integrate EventLogger in a later milestone.

Recommended tests to add now
---------------------------
- test_config_validation.py
  - Provide invalid task entries (missing id, non-positive period, timeout <= period*1000) and assert load_tasks raises ValueError with helpful messages.
- test_registry_concurrency.py
  - Spawn many Tasks or threads calling heartbeat concurrently and assert .all() contains expected keys and no exceptions/race conditions.
- test_task_stop.py
  - Start a Task, stop it, wait > period and assert seconds_since_heartbeat does not update further.

Contact / next actions
----------------------
If desired, next actions that can be performed now:
- Implement the Watchdog module + tests for Milestone 2 (I can create watchdog.py and tests/test_watchdog.py).
- Add the recommended extra tests for Milestone 1 (config validation, concurrency, stop behavior).
- Replace print() with logging and add a simple EventLogger skeleton.

End of report.
