# Milestone 2 — Watchdog & Status Classification

Date: 2026-08-30

Summary
-------
This document summarizes the Milestone 2 implementation: a watchdog thread that polls the task Registry, checks whether each task is still sending heartbeats within its configured timeout window, and classifies its state as HEALTHY, LATE, STALLED, or INITIALIZING. It also records a STALLED transition event when a task crosses from healthy/stale into the stalled state.

Files added/updated
-------------------
- [src/watchdog.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/watchdog.py) — new watchdog implementation
- [tests/test_watchdog.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/tests/test_watchdog.py) — watchdog tests
- [src/__init__.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/src/__init__.py) — export the watchdog module

What was implemented
---------------------
1. Watchdog thread (src/watchdog.py)
   - The watchdog runs in its own daemon thread and polls the Registry on a fixed interval.
   - It reads each task's last heartbeat timestamp from the Registry and computes time since last heartbeat.
   - It uses the task's configured timeout_ms and missed_heartbeat_threshold to perform health classification.
   - A small jitter buffer ensures normal scheduling variance does not falsely trigger STALLED.

2. Health classification logic
   - If no heartbeat has ever been seen for a task: INITIALIZING
   - If heartbeat age is within a normal tolerance: HEALTHY
   - If heartbeat is stale but not yet beyond stall thresholds: LATE
   - If the stale period is beyond the configured threshold: STALLED
   - RECOVERING is reserved for the future recovery milestone and is not yet used by the main logic.

3. STALLED transition logging
   - The watchdog stores a transition record whenever a task changes from a non-STALLED state into STALLED.
   - The event includes the task_id and timestamp.
   - Output is printed to stdout for easy observation during development and debugging.

4. Test coverage (tests/test_watchdog.py)
   - Starts a watchdog with a task config and a heartbeat age that exceeds its timeout threshold.
   - Verifies the watchdog eventually classifies the task as STALLED.
   - Verifies a STALLED event was emitted.

How it works
------------
The watchdog does the following on each poll cycle:
1. Reads the last heartbeat for each configured task from Registry.
2. Computes age = now - last_heartbeat_ts.
3. Compares age against the task's timeout_ms and grace/jitter logic.
4. Labels the task HEALTHY/LATE/STALLED.
5. If it transitions into STALLED and the previous state was not STALLED, logs the event.

This follows the SRS requirement that the watchdog is independent of task periods and polls on its own interval.

How to run locally
------------------
1. Activate the virtual environment:
   - source .venv/bin/activate
2. Install dependencies (if needed):
   - pip install -r requirements.txt
3. Run the relevant tests:
   - PYTHONPATH=. python3 -m pytest -q tests/test_task_simulation.py tests/test_watchdog.py
4. Observe live states in console:
   - PYTHONPATH=. python3 scripts/watchdog_demo.py
   - This starts the tasks and watchdog together and prints a STATUS snapshot every second so you can watch HEALTHY/LATE/STALLED transitions in real time.
5. Optional manual smoke test:
   - PYTHONPATH=. python3 scripts/run_tasks.py
   - this shows the raw task heartbeats without the watchdog state overlay.

Validation performed
--------------------
The following command was executed successfully:
- python3 -m pytest -q tests/test_task_simulation.py tests/test_watchdog.py -q

Result: all tests passed.

Design notes & rationale
------------------------
- The watchdog keeps the logic separate from the Task runtime to preserve the architecture in the plan: core simulation logic first, watchdog/recovery logic next, then dashboard.
- Classification is intentionally simple but explicit. This keeps the logic easy to test and easy to extend in future milestones.
- The jitter buffer makes the logic more realistic and reduces false positives during thread scheduling jitter.
- The Registry helper seconds_since_heartbeat was added earlier to simplify time calculations and reduce repeated logic in the watchdog.

Limitations and known gaps
--------------------------
- This milestone does not yet implement fault injection or auto-recovery.
- The watchdog currently reports STALLED via stdout only; no formal EventLogger is in place yet.
- The logic is local and synchronous; the next milestone will extend it to inject faults and trigger recovery behavior.

Recommended next steps (Milestone 3 prep)
------------------------------------------
1. Add a FaultInjector that can inject a hang or communication failure into a named task.
2. Log fault injection events with timestamp and task ID.
3. Add tests to validate second-injection edge cases and that a hung task leads to a watchdog STALLED classification.
4. Then implement TaskManager/RecoveryManager to restart stalled tasks and confirm recovery via a fresh heartbeat.

End of report.
