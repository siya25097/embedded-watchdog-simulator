# Embedded Watchdog & Fault Recovery Simulator

## 1. Purpose

The Embedded Watchdog & Fault Recovery Simulator demonstrates how embedded and firmware systems monitor periodic tasks, detect failures, and recover automatically.

Real embedded systems often run multiple tasks such as sensor polling, control loops, communication handlers, and diagnostics. Each task must execute within an expected timing window. If a task hangs, deadlocks, or stops responding, a watchdog mechanism detects the missing activity and starts a recovery action.

This project models that behavior in Python without requiring a microcontroller, RTOS, or hardware lab.

## 2. Before you start

You need:

- Python 3.9 or newer.
- A terminal.
- Basic familiarity with running Python commands.
- A browser for the Streamlit dashboard.

You do not need:

- An Arduino, Raspberry Pi, or other hardware.
- An RTOS.
- A database server.
- Internet access after the Python dependencies are installed.

The commands in this guide assume you are standing in the project root, the folder containing `requirements.txt`, `src/`, `dashboard/`, and `tests/`.

## 3. First run for beginners

### Step 1: Open the project folder

```bash
cd /Users/khushi_makwana/VSCode/EMBEDDED_PROJECT
```

If your project is in another location, replace the path with your own project path.

### Step 2: Create a virtual environment

A virtual environment keeps this project's packages separate from other Python projects.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, use:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

The main packages are:

- `pytest`: runs automated tests.
- `pyyaml`: reads `config/tasks.yaml`.
- `streamlit`: runs the browser dashboard.

### Step 4: Confirm that the project works

```bash
PYTHONPATH=. python3 -m pytest -q
```

The command should finish with all tests passing.

### Step 5: Start the dashboard

```bash
PYTHONPATH=. python3 -m streamlit run dashboard/app.py
```

Open the local URL printed in the terminal, normally `http://localhost:8501`.

## 4. Dashboard walkthrough

1. Wait a few seconds for all task cards to change from `INITIALIZING` to `HEALTHY`.
2. Read the **System Overview** to see the number of tasks, healthy tasks, stalled tasks, recovering tasks, and active faults.
3. Use **Task Status** to inspect each task's status, heartbeat age, and recovery count.
4. Use **Fault Injection** to select a task and choose `Hang` or `Comm Failure`.
5. Click **Inject Fault** once. The duplicate-injection protection disables the button while the fault is active.
6. Watch the selected task become late or stalled, then recovering, and finally healthy after a fresh heartbeat.
7. Review the **Event Log** for fault, stall, recovery, and heartbeat events.
8. Use **Clear Fault** when you want to remove a fault manually.

For a slower demonstration:

1. Open a task in **Simulation Controls** in the left sidebar.
2. Increase its period to `3–5` seconds.
3. Set its timeout higher than the period converted to milliseconds. For example, a 5-second period needs a timeout greater than `5000`.
4. Keep the missed-heartbeat threshold at `2`.
5. Click **Apply timing changes**.
6. Inject a fault and observe the transition more slowly.

The typical flow is:

```text
HEALTHY → LATE → STALLED → RECOVERING → HEALTHY
```

The `LATE` state can be brief or skipped visually because the watchdog and dashboard refresh independently. This does not necessarily indicate an error.

## 5. What the project demonstrates

- Concurrent periodic task execution using Python threads
- Heartbeat generation after task work
- Thread-safe heartbeat state storage
- Watchdog-based health classification
- Hang and communication-failure injection
- Automatic task restart after a stall
- Recovery confirmation using a fresh heartbeat
- Structured event history and JSON Lines persistence
- Live Streamlit monitoring dashboard
- Automated tests and long-running soak validation

## 6. High-level architecture

```text
                         ┌──────────────────┐
                         │  Streamlit UI    │
                         │  reads state     │
                         └────────┬─────────┘
                                  │
┌──────────────┐ heartbeat ┌──────▼───────┐ poll ┌──────────────┐
│ Task Threads │──────────►│   Registry   │◄────│   Watchdog   │
└──────┬───────┘           └──────────────┘     └──────┬───────┘
       │                                               │ STALLED
       │ fault state                                   ▼
       │                                      ┌──────────────────┐
       └───────────────┐                      │ RecoveryManager  │
                       ▼                      └────────┬─────────┘
                ┌──────────────┐                       │ restart
                │FaultInjector │                       ▼
                └──────────────┘                ┌──────────────┐
                                                │ TaskManager  │
                                                └──────────────┘

                 All components ──► EventLogger ──► events.jsonl
```

## 7. Main components

### Task

Implemented in [src/task.py](../src/task.py).

Each `Task` is a daemon thread that repeatedly:

1. Performs optional simulated work.
2. Checks whether a fault is active.
3. Emits a heartbeat when operating normally.
4. Sleeps for its configured period.

The task can be stopped through a thread-safe stop event.

### Registry

Implemented in [src/registry.py](../src/registry.py).

The Registry stores the timestamp of the most recent heartbeat for every task. Access is protected by a lock because task threads write concurrently while the watchdog and dashboard read.

Important operations:

- `heartbeat(task_id)` records a heartbeat.
- `get(task_id)` returns the raw timestamp.
- `seconds_since_heartbeat(task_id)` returns the heartbeat age.

### Watchdog

Implemented in [src/watchdog.py](../src/watchdog.py).

The Watchdog runs independently from task periods and polls the Registry at a fixed interval. It compares each task's heartbeat age against the configured period, timeout, missed-heartbeat threshold, and jitter buffer.

Possible states:

- `INITIALIZING`: no heartbeat has been received yet.
- `HEALTHY`: heartbeat activity is within the expected timing window.
- `LATE`: the heartbeat is delayed but has not crossed the stall condition.
- `STALLED`: enough heartbeats have been missed to indicate a failure.
- `RECOVERING`: recovery has been initiated and is awaiting a fresh heartbeat.

When a task first enters `STALLED`, the watchdog records an event and invokes the recovery callback.

### FaultInjector

Implemented in [src/fault_injector.py](../src/fault_injector.py).

The FaultInjector controls simulated failures:

- `hang`: the task thread remains alive but stops sending heartbeats.
- `comm_failure`: the task continues its loop, but heartbeat delivery is lost.

Faults are associated with a task ID. Unknown tasks and duplicate active faults are rejected safely and logged.

### TaskManager

Implemented in [src/task_manager.py](../src/task_manager.py).

The TaskManager owns task lifecycle operations:

- Start one task.
- Start all tasks.
- Stop one task.
- Stop all tasks.
- Restart a task.

Centralizing lifecycle ownership ensures that recovery does not create duplicate task threads.

### RecoveryManager

Implemented in [src/recovery.py](../src/recovery.py).

When the watchdog detects a stall, the RecoveryManager:

1. Records a recovery attempt.
2. Clears the active injected fault.
3. Asks the TaskManager to restart the task.
4. Marks the recovery as awaiting confirmation.
5. Records `RECOVERY_SUCCEEDED` only after the restarted task sends a fresh heartbeat.

This follows the project rule that restarting a thread alone is not proof of recovery.

### EventLogger

Implemented in [src/event_logger.py](../src/event_logger.py).

The EventLogger provides:

- Thread-safe in-memory event history.
- Chronological event retrieval.
- Standard-library logging output.
- Optional JSON Lines persistence.

The dashboard uses `events.jsonl`, which is ignored by Git and loaded again when the dashboard starts.

### Dashboard

Implemented in [dashboard/app.py](../dashboard/app.py).

The Streamlit dashboard provides:

- System overview metrics.
- Live task status cards.
- Heartbeat freshness.
- Recovery counts.
- Fault injection controls.
- Timing configuration controls.
- Task details.
- Reverse-chronological event log.

The runtime objects are stored in Streamlit session state so widget reruns do not create duplicate simulations.

## 8. Normal runtime flow

At startup:

1. The YAML configuration is loaded and validated.
2. The Registry, EventLogger, FaultInjector, TaskManager, RecoveryManager, and Watchdog are created.
3. Configured task threads start.
4. The Watchdog starts polling.
5. Tasks begin emitting heartbeats.
6. The dashboard displays `INITIALIZING`, then `HEALTHY` after the first heartbeat.

## 9. Fault and recovery flow

The normal fault demonstration is:

```text
HEALTHY
   │
   ├── inject hang or communication failure
   ▼
LATE
   ▼
STALLED
   ▼
RECOVERING
   │
   ├── TaskManager restarts task
   ├── fault is cleared
   └── fresh heartbeat is received
   ▼
HEALTHY
```

The `LATE` state is timing-dependent. It may be brief or skipped by a human viewing the dashboard, while the watchdog still correctly detects the eventual `STALLED` condition.

## 10. Reading the event log

The dashboard shows events newest first. Normal `HEARTBEAT` events from all tasks can appear between fault and recovery events, so related entries may not be adjacent.

For a successful recovery, look for this sequence:

```text
FAULT_INJECTED
→ STALL_DETECTED
→ RECOVERY_ATTEMPTED
→ fault_cleared
→ RECOVERY_STARTED
→ fresh HEARTBEAT
→ RECOVERY_SUCCEEDED
```

Example communication-failure recovery:

```text
19:20:39  FAULT_EVENT          comm_failure cleared
19:20:39  RECOVERY_STARTED     recovery_count=1
19:20:40  RECOVERY_SUCCEEDED   recovery_count=1
```

Example hang recovery:

```text
19:21:15  FAULT_INJECTED       hang
19:21:19  STALL_DETECTED       STALLED
19:21:19  RECOVERY_ATTEMPTED
19:21:19  FAULT_EVENT          hang cleared
19:21:19  RECOVERY_STARTED     recovery_count=2
19:21:20  RECOVERY_SUCCEEDED   recovery_count=2
```

The cumulative `recovery_count` means this task had already completed one recovery before the second example. Recovery is successful only after a fresh heartbeat is observed.

## 11. Configuration

Task configuration is stored in [config/tasks.yaml](../config/tasks.yaml):

```yaml
tasks:
  - id: task-A
    period: 1
    timeout_ms: 3000
    missed_heartbeat_threshold: 2
```

Validation rules:

- Task IDs must be non-empty strings.
- Task IDs must be unique.
- Period must be positive.
- `timeout_ms` must be greater than `period * 1000`.
- `missed_heartbeat_threshold` must be at least `1`.

The dashboard can edit timing values in the sidebar. Applying changes restarts all tasks with the edited configuration.

## 12. Running the project

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run automated tests:

```bash
PYTHONPATH=. python3 -m pytest -q
```

Run the live dashboard:

```bash
PYTHONPATH=. python3 -m streamlit run dashboard/app.py
```

Run the console heartbeat demo:

```bash
PYTHONPATH=. python3 scripts/run_tasks.py
```

Run the console watchdog demo:

```bash
PYTHONPATH=. python3 scripts/watchdog_demo.py
```

Run the ten-minute soak test:

```bash
PYTHONPATH=. python3 scripts/soak_test.py --duration 600 --fault-interval 5
```

## 13. Testing strategy

The project tests:

- Task heartbeat generation.
- Registry concurrency and stop behavior.
- Configuration validation.
- Watchdog health classification and stall detection.
- Hang and communication-failure behavior.
- Duplicate and unknown fault handling.
- Automatic restart and recovery confirmation.
- Event ordering and JSONL persistence.
- Dashboard module availability.

The long-running soak test repeatedly injects faults into the configured tasks and confirms that recovery returns every task to `HEALTHY`.

## 14. Beginner glossary

### Task

A small unit of work that runs repeatedly. In this simulator, a task is a Python thread.

### Period

How often a task starts another cycle, measured in seconds. A period of `1` means the task normally produces one heartbeat about every second.

### Heartbeat

A signal that means, “I am alive and making progress.” Here, it is a timestamp written by a task to the Registry.

### Registry

The shared in-memory record of the latest heartbeat from every task. It is protected by a lock so multiple threads can safely use it.

### Watchdog

A supervisor that checks whether tasks are still sending heartbeats on time. This is software modeled after a hardware watchdog timer.

### Timeout

The maximum heartbeat age allowed before the task is considered unhealthy. The configuration stores this value in milliseconds as `timeout_ms`.

### Missed-heartbeat threshold

The number of expected heartbeat cycles that may be missed before the watchdog declares a task `STALLED`.

### Jitter

Small timing variation caused by thread scheduling and operating-system activity. The watchdog uses a grace buffer so normal jitter is not immediately treated as a failure.

### Fault injection

Deliberately creating a failure so the monitoring and recovery behavior can be tested. This project supports `hang` and `comm_failure`.

### Hang

A simulated task failure where the task thread remains alive but stops producing heartbeats.

### Communication failure

A simulated monitoring-channel failure where the task loop continues but its heartbeat does not reach the Registry.

### Recovery

The action taken after a stall is detected. The RecoveryManager asks the TaskManager to stop and restart the task.

### Fresh heartbeat

A heartbeat produced after a restart. The project only considers recovery successful after observing this evidence.

### Event Logger

The component that records important runtime events such as faults, stalls, recoveries, and heartbeats.

### JSON Lines

A simple persistence format where each line in `events.jsonl` is one JSON event object. It is easy to append to and reload.

## 15. Troubleshooting

### `ModuleNotFoundError: No module named 'src'`

Run commands from the project root with `PYTHONPATH=.`:

```bash
PYTHONPATH=. python3 -m pytest -q
PYTHONPATH=. python3 -m streamlit run dashboard/app.py
```

### The dashboard says `Unable to start simulator`

Check the terminal for the full error, then validate the YAML configuration:

```bash
PYTHONPATH=. python3 -c "from scripts.run_tasks import load_tasks; print(load_tasks())"
```

Check that every task has a unique ID, a positive period, a timeout greater than `period * 1000`, and a threshold of at least `1`.

### A task stays `INITIALIZING`

Check that:

- The task appears in `config/tasks.yaml`.
- The task period is positive.
- The dashboard was restarted after changing configuration.
- No Python traceback appears in the terminal.

### I cannot see `LATE`

`LATE` may be shorter than the dashboard refresh interval or may be skipped between two visible refreshes. Increase the task period and timeout in the sidebar for a slower demonstration.

### The event log is very large

Heartbeats are intentionally logged for observability. Stop the dashboard, remove the local `events.jsonl` file if you want a clean session, and start the dashboard again. The file is ignored by Git.

### How do I stop the application?

Press `Ctrl+C` in the terminal running Streamlit or the console demo. The task manager requests task shutdown and joins the threads.

## 16. Firmware concept mapping

| Simulator component | Real embedded equivalent |
|---|---|
| Python task thread | RTOS task |
| Periodic task loop | Timer-driven firmware routine |
| Heartbeat write | Watchdog kick or alive signal |
| Thread-safe Registry | Shared diagnostic/runtime state |
| Watchdog poller | Hardware/software watchdog supervisor |
| Hang fault | Deadlock, infinite loop, blocked I/O |
| Communication failure | Lost status message or broken monitoring channel |
| Task restart | RTOS task restart or MCU reset |
| Recovery confirmation | Post-reset health check |
| EventLogger | Persistent diagnostic/fault log |
| Streamlit dashboard | Engineering monitoring console |

## 17. Scope and limitations

This is an educational simulator, not a production safety mechanism. It does not provide:

- Real MCU or RTOS execution.
- Hard real-time guarantees.
- Multi-process isolation.
- Networked task supervision.
- Authentication or multi-user access.
- SQLite persistence.
- Automatic external alerting.

The current simulator uses in-process Python threads and local JSON Lines persistence to keep the architecture understandable and easy to demonstrate.
