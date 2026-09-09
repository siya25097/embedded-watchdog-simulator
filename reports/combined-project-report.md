# Embedded Watchdog & Fault Recovery Simulator
## Combined Project and Milestone Report

**Project status:** MVP implementation complete  
**Milestones covered:** 0 through 8  
**Implementation language:** Python 3.9+  
**Interface:** Console demos and Streamlit dashboard

---

## 1. Executive summary

The Embedded Watchdog & Fault Recovery Simulator is an educational Python project that models a common embedded-systems reliability pattern:

1. Periodic firmware-style tasks perform work.
2. Each task emits a heartbeat after successful activity.
3. A watchdog monitors heartbeat timing.
4. Faults simulate a hung task or lost communication.
5. The watchdog detects a stall and starts recovery.
6. The recovery manager restarts the task.
7. Recovery is confirmed only after a fresh heartbeat.
8. Structured events are shown in the dashboard and persisted as JSON Lines.

The project demonstrates concurrency, timing supervision, fault injection, automatic recovery, thread safety, structured logging, persistence, dashboard design, automated testing, and long-running stability validation without requiring hardware or an RTOS.

The normal recovery state flow is:

```text
INITIALIZING -> HEALTHY -> LATE -> STALLED -> RECOVERING -> HEALTHY
```

`LATE` can be brief or skipped visually because task execution, watchdog polling, and dashboard refresh run independently.

---

## 2. Milestone completion summary

| Milestone | Focus | Status | Main outcome |
|---|---|---|---|
| 0 | Planning and project setup | Complete | Requirements, architecture, repository structure, and development plan established |
| 1 | Core task simulation | Complete | Periodic task threads and thread-safe heartbeat registry |
| 2 | Watchdog monitoring | Complete | Health classification and stall detection |
| 3 | Fault injection | Complete | Hang and communication-failure simulation |
| 4 | Automatic recovery | Complete | Task restart and fresh-heartbeat recovery confirmation |
| 5 | Event logging | Complete | Thread-safe structured event history |
| 6 | Streamlit dashboard | Complete | Live monitoring and operator controls |
| 7 | Testing and polish | Complete | Validation fixes, regression tests, and soak testing |
| 8 | Documentation and packaging | Complete | Official documentation, JSONL persistence, and demo preparation |

---

## 3. Milestone 0 — Planning and foundation

### Goal

Define the problem, expected behavior, architecture, requirements, and implementation sequence before building the simulator.

### Work completed

- Defined the product purpose: demonstrate watchdog monitoring and fault recovery without physical embedded hardware.
- Defined functional requirements for tasks, heartbeats, watchdog states, faults, recovery, logging, and dashboard behavior.
- Defined software requirements for configuration validation and thread-safe operation.
- Created the repository structure:

```text
config/       YAML task configuration
dashboard/    Streamlit user interface
docs/         Requirements, architecture, UI/UX, and guides
reports/      Milestone and combined reports
scripts/      Console demos and validation tools
src/          Simulator implementation
tests/        Automated regression tests
```

- Chose Python threads to model concurrent periodic tasks.
- Chose a shared Registry for heartbeat state.
- Planned a separate Watchdog, FaultInjector, TaskManager, RecoveryManager, and EventLogger.
- Defined the main acceptance flow:

```text
healthy task -> injected fault -> missing heartbeat -> stall -> restart -> fresh heartbeat
```

### Result

Milestone 0 established the design foundation used by all later milestones.

---

## 4. Milestone 1 — Core task simulation

### Goal

Create periodic task threads that emit heartbeats and store their latest heartbeat safely.

### Main implementation

#### `src/task.py`

The `Task` class extends `threading.Thread`. Each task:

1. Optionally runs a supplied work function.
2. Checks whether a fault is active.
3. Writes a heartbeat to the Registry during normal operation.
4. Optionally records a `HEARTBEAT` event.
5. Sleeps for the configured period in small chunks.

The small sleep chunks allow `stop()` to shut down a task responsively.

#### `src/registry.py`

The Registry stores the last heartbeat timestamp for every task. A lock protects concurrent reads and writes.

Important operations:

- `heartbeat(task_id)` records activity.
- `get(task_id)` returns the raw timestamp.
- `all()` returns a snapshot of timestamps.
- `seconds_since_heartbeat(task_id)` calculates heartbeat age.

#### `config/tasks.yaml`

Defines task IDs and timing values:

- `period`: expected heartbeat interval in seconds.
- `timeout_ms`: stall timeout in milliseconds.
- `missed_heartbeat_threshold`: number of missed periods allowed before stall classification.

#### `scripts/run_tasks.py`

Loads and validates YAML configuration, starts all configured tasks, prints heartbeats, and handles Ctrl+C shutdown.

Validation includes:

- Task entries must be mappings.
- IDs must be present, non-empty, and unique.
- Period must be positive.
- Timeout must be positive and greater than `period * 1000`.
- Missed-heartbeat threshold must be at least 1.

### Tests

- Tasks emit recent heartbeats.
- Configuration fields are loaded and normalized.
- Invalid configuration is rejected.

### Result

The simulator had a working concurrent task foundation for watchdog monitoring.

---

## 5. Milestone 2 — Watchdog and status classification

### Goal

Monitor heartbeat timing independently from task execution and classify task health.

### `src/watchdog.py`

The Watchdog is an independent daemon thread. On each poll it:

1. Reads the latest heartbeat timestamp.
2. Calculates heartbeat age.
3. Compares age with period, timeout, threshold, and jitter buffer.
4. Assigns a status.
5. Records a stall transition once when a task becomes stalled.

Supported statuses:

- `INITIALIZING`: no heartbeat has been received.
- `HEALTHY`: heartbeat is within the expected timing window.
- `LATE`: heartbeat is delayed but has not met the stall condition.
- `STALLED`: enough heartbeat time has been missed.
- `RECOVERING`: recovery is in progress.

The watchdog accepts callbacks for stalled and healthy transitions. These callbacks allow later recovery logic to be connected without coupling the watchdog to task lifecycle code.

### Result

The project could detect missing or delayed heartbeats and distinguish normal timing variation from a real stall.

---

## 6. Milestone 3 — Fault injection

### Goal

Provide controlled, repeatable failures that can be observed by the watchdog.

### `src/fault_injector.py`

The FaultInjector:

- Supports `hang`.
- Supports `comm_failure`.
- Tracks active faults per task.
- Rejects unsupported fault types.
- Rejects unknown task IDs safely.
- Prevents duplicate active faults.
- Clears active faults.
- Records fault-related events.
- Uses locking for concurrent access.

### Fault behavior

#### Hang

The task thread remains alive but stops emitting heartbeats. This models an infinite loop, deadlock, or blocked operation.

#### Communication failure

The task loop continues, but heartbeat delivery is lost. This models a broken communication path between a task and its monitor.

From the watchdog's perspective, both faults appear as missing heartbeats.

### Tests

- Hang suppresses heartbeats.
- Communication failure suppresses heartbeats temporarily.
- Clearing a fault allows heartbeats to resume.
- Duplicate injection is ignored.
- Unknown task handling is safe.
- A hang produces watchdog `STALLED`.

### Result

The simulator could reproduce realistic heartbeat-loss scenarios while keeping the task process alive.

---

## 7. Milestone 4 — Automatic recovery

### Goal

Restart stalled tasks and verify that recovery is real rather than assuming that a restart succeeded.

### `src/task_manager.py`

The TaskManager owns task lifecycle operations:

- Start one task.
- Start all tasks.
- Stop one task.
- Stop all tasks.
- Restart one task.

It centralizes task creation and prevents recovery code from accidentally creating duplicate threads.

### `src/recovery.py`

The RecoveryManager:

- Receives stalled-task callbacks.
- Tracks recovery counts.
- Records the latest recovery timestamp.
- Clears an active fault before restart.
- Restarts the affected task.
- Prevents overlapping recovery attempts.
- Waits for watchdog confirmation of a fresh heartbeat.
- Records recovery lifecycle events.

Recovery events include:

- `RECOVERY_ATTEMPTED`
- `RECOVERY_STARTED`
- `RECOVERY_SUCCEEDED`
- `RECOVERY_FAILED`

### Recovery rule

A task is not considered recovered merely because its thread was restarted. The Watchdog must observe a new heartbeat after recovery begins.

### Result

The complete automatic recovery lifecycle was implemented:

```text
STALLED -> RECOVERING -> fresh heartbeat -> HEALTHY
```

---

## 8. Milestone 5 — Structured event logging

### Goal

Provide one chronological, thread-safe event history for the entire simulator.

### `src/event_logger.py`

Each event contains:

```text
timestamp
event_type
task_id
details
```

The EventLogger:

- Stores events in memory.
- Protects event access with a lock.
- Supports chronological retrieval.
- Uses Python's standard `logging` module for console output.
- Optionally appends events to a JSON Lines file.
- Loads existing JSONL events when started with a persistence path.

### Event sources

Events can be generated by:

- Tasks: `HEARTBEAT`
- FaultInjector: fault injection, clearing, duplicate, and invalid-task events
- Watchdog: `STALL_DETECTED`
- RecoveryManager: recovery lifecycle events

### Result

All important runtime actions can be inspected in one structured history instead of relying on unrelated console messages.

---

## 9. Milestone 6 — Streamlit dashboard

### Goal

Create a live operator interface for monitoring tasks and injecting faults.

### `dashboard/app.py`

The dashboard:

- Starts the simulator runtime once in Streamlit session state.
- Loads validated task configuration.
- Displays task status cards.
- Shows heartbeat age.
- Shows recovery counts.
- Allows selecting a task.
- Allows injecting `Hang` or `Comm Failure`.
- Prevents duplicate fault injection.
- Allows clearing an active fault.
- Displays a reverse-chronological event table.
- Filters event types.
- Refreshes frequently for live status updates.
- Provides built-in usage instructions.
- Persists events to `events.jsonl`.
- Supports editable task timing values.

### Slow-motion timing controls

The sidebar allows editing:

- Period in seconds.
- Timeout in milliseconds.
- Missed-heartbeat threshold.

Applying the changes restarts all tasks with the new configuration. A period of 3–5 seconds is useful when demonstrating the sequence slowly.

### Dashboard usage flow

1. Start the dashboard.
2. Wait until tasks show `HEALTHY`.
3. Select a task and fault type.
4. Click **Inject Fault**.
5. Observe `LATE`, `STALLED`, `RECOVERING`, and `HEALTHY`.
6. Inspect the event log and recovery count.
7. Optionally clear a fault manually.

### Result

The simulator became usable as an interactive local demonstration instead of only a code-level experiment.

---

## 10. Milestone 7 — Testing, stability, and polish

### Goal

Close validation gaps, improve shutdown behavior, and prove stability under repeated faults.

### Improvements

- Added duplicate task-ID validation.
- Corrected threshold validation to require values of at least 1.
- Improved clean thread shutdown and joining.
- Preserved locking around shared state.
- Added regression tests for configuration edge cases.
- Added a repeatable soak-test script.
- Fixed dashboard configuration-shape handling.
- Improved watchdog polling and dashboard refresh responsiveness.

### `scripts/soak_test.py`

The soak test:

1. Loads the validated task configuration.
2. Starts the Registry, FaultInjector, TaskManager, RecoveryManager, Watchdog, and EventLogger.
3. Injects repeated hang faults across tasks.
4. Waits for automatic recovery.
5. Confirms all tasks return to `HEALTHY`.
6. Shuts down the runtime cleanly.
7. Reports duration, injection count, and event count.

### Validation result

The required ten-minute soak test completed successfully:

```text
Soak passed: 600s, 120 injections, 1796 events
```

This demonstrated repeated fault detection and recovery without permanent degradation.

---

## 11. Milestone 8 — Documentation, persistence, and packaging

### Goal

Make the project understandable to beginners and presentable as an official portfolio/resume project.

### Documentation completed

- `README.md`: quick start, architecture, demos, configuration, limitations, and firmware mapping.
- `docs/01_PRD.md`: product requirements.
- `docs/02_SRS.md`: software requirements.
- `docs/03_ARCHITECTURE.md`: component and data-flow design.
- `docs/04_UIUX.md`: dashboard layout and interaction behavior.
- `docs/05_DEVELOPMENT_PLAN.md`: milestone checklist.
- `docs/06_PROJECT_GUIDE.md`: beginner setup, terminology, walkthrough, troubleshooting, and event interpretation.
- Individual milestone reports.
- This combined project report.

### Persistence

The dashboard writes event objects to:

```text
events.jsonl
```

Each line is one JSON event. The file is local and gitignored. It can be reloaded on startup while the in-memory event list is used for fast live rendering.

### Result

The project now includes implementation, validation evidence, operational instructions, and documentation suitable for demonstration and portfolio review.

---

## 12. Script reference

### `scripts/run_tasks.py`

**Purpose:** Basic task-only console runner.

**Uses:** YAML configuration, Registry, and Task.

**Behavior:** Validates configuration, starts all configured tasks, prints heartbeat activity, and stops cleanly on Ctrl+C.

**Command:**

```bash
PYTHONPATH=. python3 scripts/run_tasks.py
```

### `scripts/watchdog_demo.py`

**Purpose:** Console demonstration of watchdog status classification.

**Uses:** YAML configuration, Registry, Task, and Watchdog.

**Behavior:** Starts tasks and watchdog polling, then prints status snapshots periodically.

**Command:**

```bash
PYTHONPATH=. python3 scripts/watchdog_demo.py
```

### `scripts/soak_test.py`

**Purpose:** Long-running reliability and regression validation.

**Uses:** The complete runtime stack.

**Behavior:** Repeatedly injects faults, waits for recovery, verifies all tasks become healthy, and reports event totals.

**Command:**

```bash
PYTHONPATH=. python3 scripts/soak_test.py --duration 600 --fault-interval 5
```

### `dashboard/app.py`

**Purpose:** Interactive operator dashboard.

**Uses:** The complete runtime stack plus Streamlit.

**Command:**

```bash
PYTHONPATH=. python3 -m streamlit run dashboard/app.py
```

---

## 13. Core source-module reference

| Module | Responsibility |
|---|---|
| `src/task.py` | Periodic task execution and heartbeat emission |
| `src/registry.py` | Thread-safe last-heartbeat storage |
| `src/watchdog.py` | Independent polling and health classification |
| `src/fault_injector.py` | Fault state management and fault events |
| `src/task_manager.py` | Task start, stop, and restart lifecycle |
| `src/recovery.py` | Recovery attempts and fresh-heartbeat confirmation |
| `src/event_logger.py` | Structured event history and optional JSONL persistence |
| `scripts/run_tasks.py` | Configuration loading and basic task runner |
| `dashboard/app.py` | Live Streamlit monitoring and controls |

---

## 14. Timing terminology

### Task period — seconds

The expected interval between normal task cycles and heartbeats. A period of `2` means the task normally emits one heartbeat approximately every two seconds.

### Task timeout — milliseconds

The maximum allowed age of a heartbeat before the watchdog can classify the task as stalled. A timeout of `5000` means approximately five seconds.

The configuration requires:

```text
timeout_ms > period * 1000
```

### Missed heartbeat threshold

The number of expected heartbeat periods that may be missed before a task is treated as stalled. The value must be at least `1`.

### Watchdog poll interval

How often the watchdog checks task health. This is independent from the task period.

### Jitter buffer

A small timing tolerance that prevents ordinary thread scheduling variation from causing false stalls.

---

## 15. Fault and recovery event timeline

For a successful fault/recovery cycle, the event order is conceptually:

```text
HEARTBEAT
FAULT_INJECTED
STALL_DETECTED
RECOVERY_ATTEMPTED
FAULT_EVENT (fault_cleared)
RECOVERY_STARTED
HEARTBEAT
RECOVERY_SUCCEEDED
```

The exact order of nearby heartbeat and fault events can vary because multiple threads are running concurrently. The dashboard displays events in timestamp order, and heartbeat entries may make related events appear separated.

`RECOVERY_SUCCEEDED` means the restarted task emitted a fresh heartbeat and the watchdog observed it.

---

## 16. Test and validation strategy

The project validates behavior at multiple levels:

### Unit and integration tests

- Task heartbeat generation.
- Registry timestamp and age calculations.
- Configuration validation.
- Watchdog state classification.
- Stall transition detection.
- Hang and communication-failure behavior.
- Duplicate and unknown fault handling.
- Task restart and recovery confirmation.
- Event ordering and persistence.
- Dashboard import/startup behavior.

### Full suite

Run:

```bash
PYTHONPATH=. python3 -m pytest -q
```

The suite passed during Milestone 7 with:

```text
22 passed
```

Additional persistence coverage was added during Milestone 8; rerun the command in the current checkout for the latest count.

### Compile and smoke checks

```bash
python3 -m py_compile src/*.py dashboard/app.py
PYTHONPATH=. python3 -c "import src; print('src import OK')"
```

### Long-running validation

```bash
PYTHONPATH=. python3 scripts/soak_test.py --duration 600 --fault-interval 5
```

Expected result:

```text
Soak passed
```

---

## 17. End-to-end architecture

```text
                 heartbeat
 Task Threads -----------------> Registry
      ^                              |
      |                              | heartbeat age
      |                              v
 FaultInjector <-------------- Watchdog
      |                              |
      |                              | STALLED
      v                              v
  Task behavior                 RecoveryManager
                                     |
                                     | restart
                                     v
                                TaskManager
                                     |
                                     | fresh heartbeat
                                     v
                                  HEALTHY

 All components ----------------> EventLogger ---> events.jsonl
                                      ^
                                      |
                              Streamlit Dashboard
```

---

## 18. Firmware relevance

| Simulator component | Embedded-system equivalent |
|---|---|
| Periodic Python task | RTOS task or scheduled firmware loop |
| Registry heartbeat | Watchdog kick or task-alive signal |
| Watchdog polling | Hardware/software watchdog supervision |
| Hang fault | Deadlock, infinite loop, blocked I/O, or scheduler failure |
| Communication failure | Lost status message or broken monitoring channel |
| Task restart | Supervised task restart or MCU reset |
| Event log | Persistent diagnostic or non-volatile fault log |
| Dashboard | Local engineering and validation tool |

---

## 19. Known limitations and future enhancements

The current implementation is an educational local simulator, not a certified safety system.

Not currently implemented:

- Physical hardware integration.
- RTOS execution.
- Distributed or networked monitoring.
- Authentication and multi-user access.
- SQLite persistence.
- Maximum recovery-attempt policy.
- `FAILED_PERMANENTLY` state.
- Advanced metrics and timeline analytics.
- Production-grade event retention and rotation.

Possible future milestones could add persistent SQLite storage, event filtering by task, recovery-failure escalation, metrics charts, and hardware-in-the-loop adapters.

---

## 20. Recommended final project commands

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python3 -m pytest -q
PYTHONPATH=. python3 scripts/watchdog_demo.py
PYTHONPATH=. python3 -m streamlit run dashboard/app.py
```

For a portfolio demonstration:

1. Start the dashboard.
2. Show all tasks becoming `HEALTHY`.
3. Increase one task period to 3–5 seconds for slow motion.
4. Inject `Hang`.
5. Show `LATE`, `STALLED`, `RECOVERING`, and `HEALTHY`.
6. Open the event log and explain the recovery sequence.
7. Mention the ten-minute soak result and automated test coverage.

---

## 21. Resume-ready project summary

Built a Python-based embedded watchdog and fault-recovery simulator using concurrent periodic tasks, thread-safe heartbeat monitoring, configurable hang and communication-failure injection, automatic task restart, fresh-heartbeat recovery confirmation, structured JSONL event persistence, and a Streamlit operations dashboard. Added automated unit/integration tests and validated repeated recovery behavior with a ten-minute, 120-injection soak test.
