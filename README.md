# Embedded Watchdog & Fault Recovery Simulator

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-24%20passing-2ea44f)
![License](https://img.shields.io/badge/license-educational-lightgrey)

An educational Python simulator that demonstrates how embedded systems monitor periodic tasks, detect failures, and recover automatically.

The project models:

- Periodic firmware-style tasks
- Thread-safe heartbeat monitoring
- Watchdog health classification
- Hang and communication-failure injection
- Automatic task restart
- Fresh-heartbeat recovery confirmation
- Structured event logging and JSONL persistence
- A live Streamlit operations dashboard

It runs locally without a microcontroller, RTOS, or external database.

## Table of contents

- [Why this project](#why-this-project)
- [System behavior](#system-behavior)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Interactive dashboard](#interactive-dashboard)
- [Console scripts](#console-scripts)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Testing and validation](#testing-and-validation)
- [Embedded-systems mapping](#embedded-systems-mapping)
- [Limitations](#limitations)
- [Documentation](#documentation)

## Why this project

In a real embedded system, a task may stop making progress because of an infinite loop, deadlock, blocked I/O, or a communication failure. A watchdog detects that missing activity and initiates a recovery action.

This simulator makes that behavior observable and testable:

```text
Task emits heartbeat
        ↓
Registry stores latest heartbeat
        ↓
Watchdog checks heartbeat age
        ↓
Fault causes missing heartbeat
        ↓
Task becomes STALLED
        ↓
Recovery restarts the task
        ↓
Fresh heartbeat confirms HEALTHY
```

## System behavior

The normal fault-recovery lifecycle is:

```text
INITIALIZING → HEALTHY → LATE → STALLED → RECOVERING → HEALTHY
```

The `LATE` state may be brief or skipped visually because task execution, watchdog polling, and dashboard refresh run independently.

### Fault types

| Fault | Simulated behavior |
|---|---|
| `hang` | The task thread remains alive but stops sending heartbeats |
| `comm_failure` | The task continues running, but heartbeat delivery is lost |

Both faults appear to the watchdog as missing heartbeats.

### Recovery guarantee

Recovery is not marked successful merely because a task thread was restarted. The watchdog must observe a fresh heartbeat from the restarted task before the status returns to `HEALTHY`.

## Architecture

```text
                         heartbeat
 ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
 │ Task threads │ ───► │   Registry   │ ◄─── │   Watchdog   │
 └──────┬───────┘      └──────────────┘      └──────┬───────┘
        │                                           │ STALLED
        │ fault state                               ▼
        │                                  ┌──────────────────┐
        └──────────────► FaultInjector     │ RecoveryManager  │
                                           └────────┬─────────┘
                                                    │ restart
                                                    ▼
                                           ┌──────────────────┐
                                           │   TaskManager    │
                                           └────────┬─────────┘
                                                    │
                                                    ▼
                                             fresh heartbeat

 All components ───────────────► EventLogger ───────────────► events.jsonl
                                      ▲
                                      │
                              Streamlit dashboard
```

### Core components

| Component | Responsibility |
|---|---|
| `Task` | Runs periodic work and emits heartbeats |
| `Registry` | Stores the latest heartbeat timestamp per task |
| `Watchdog` | Polls independently and classifies task health |
| `FaultInjector` | Manages simulated failures |
| `TaskManager` | Starts, stops, and restarts task threads |
| `RecoveryManager` | Coordinates recovery and confirms fresh heartbeats |
| `EventLogger` | Stores structured events and optionally persists JSONL |
| Streamlit dashboard | Displays status and provides operator controls |

## Quick start

### Prerequisites

- Python 3.9 or newer
- A terminal
- A browser for the dashboard

### Installation

```bash
git clone https://github.com/siya25097/embedded-watchdog-simulator.git
cd embedded-watchdog-simulator

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Run the automated tests

```bash
PYTHONPATH=. python3 -m pytest -q
```

Expected result in the current project version:

```text
24 passed
```

### Start the dashboard

```bash
PYTHONPATH=. python3 -m streamlit run dashboard/app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

The `PYTHONPATH=.` prefix is required because the project is currently run directly from the repository rather than installed as a package.

## Interactive dashboard

1. Wait until the task cards show `HEALTHY`.
2. Select a task in **Fault Injection**.
3. Select `Hang` or `Comm Failure`.
4. Click **Inject Fault**.
5. Observe the task move through `LATE`, `STALLED`, `RECOVERING`, and `HEALTHY`.
6. Review the recovery count and event log.
7. Use **Clear Fault** to remove an active fault manually.

### Slow-motion demonstration

Use **Simulation Controls** in the sidebar:

1. Increase a task period to 3–5 seconds.
2. Set its timeout above the period converted to milliseconds.
3. Keep the missed-heartbeat threshold at 2.
4. Click **Apply timing changes**.
5. Inject a fault and observe the transitions more slowly.

Events are persisted locally to `events.jsonl`. The file is intentionally ignored by Git.

## Console scripts

### Basic task runner

Prints periodic task heartbeats:

```bash
PYTHONPATH=. python3 scripts/run_tasks.py
```

Stop with `Ctrl+C`.

### Watchdog demo

Prints live task health states:

```bash
PYTHONPATH=. python3 scripts/watchdog_demo.py
```

### Soak test

Runs repeated fault/recovery cycles to validate long-running stability:

```bash
PYTHONPATH=. python3 scripts/soak_test.py --duration 600 --fault-interval 5
```

The validated run completed with:

```text
Soak passed: 600s, 120 injections, 1796 events
```

## Configuration

Tasks are configured in [`config/tasks.yaml`](config/tasks.yaml):

```yaml
tasks:
  - id: task-A
    period: 1
    timeout_ms: 3000
    missed_heartbeat_threshold: 2
```

### Timing parameters

| Parameter | Unit | Meaning |
|---|---|---|
| `period` | seconds | Expected interval between task cycles and heartbeats |
| `timeout_ms` | milliseconds | Maximum heartbeat age before stall evaluation |
| `missed_heartbeat_threshold` | count | Missed periods allowed before declaring a stall |

Configuration validation requires:

- Positive task periods
- Unique, non-empty task IDs
- `timeout_ms > period * 1000`
- `missed_heartbeat_threshold >= 1`

The dashboard currently loads five sample tasks. Timing values can also be edited at runtime.

## Project structure

```text
.
├── config/
│   └── tasks.yaml
├── dashboard/
│   └── app.py
├── docs/
│   ├── 01_PRD.md
│   ├── 02_SRS.md
│   ├── 03_ARCHITECTURE.md
│   ├── 04_UIUX.md
│   ├── 05_DEVELOPMENT_PLAN.md
│   └── 06_PROJECT_GUIDE.md
├── reports/
│   ├── combined-project-report.md
│   └── milestone-*-report.md
├── scripts/
│   ├── run_tasks.py
│   ├── watchdog_demo.py
│   └── soak_test.py
├── src/
│   ├── event_logger.py
│   ├── fault_injector.py
│   ├── recovery.py
│   ├── registry.py
│   ├── task.py
│   ├── task_manager.py
│   └── watchdog.py
├── tests/
├── requirements.txt
└── README.md
```

## Testing and validation

The test suite covers:

- Periodic heartbeat generation
- Registry timestamp and age calculations
- Configuration validation
- Watchdog classification and stall detection
- Hang and communication-failure behavior
- Duplicate and unknown fault handling
- Task restart and recovery confirmation
- Event ordering and JSONL persistence
- Dashboard import and startup behavior

Run the full suite:

```bash
PYTHONPATH=. python3 -m pytest -q
```

Run targeted tests:

```bash
PYTHONPATH=. python3 -m pytest -q tests/test_recovery.py
PYTHONPATH=. python3 -m pytest -q tests/test_fault_integration.py
PYTHONPATH=. python3 -m pytest -q tests/test_event_logger.py
```

Compile the Python modules:

```bash
python3 -m py_compile src/*.py dashboard/app.py
```

## Embedded-systems mapping

| Simulator | Embedded equivalent |
|---|---|
| Periodic task thread | RTOS task or scheduled firmware loop |
| Registry heartbeat | Task liveness signal or watchdog kick |
| Watchdog polling | Hardware/software watchdog supervision |
| Hang fault | Infinite loop, deadlock, or blocked I/O |
| Communication failure | Lost status message or monitoring-channel failure |
| Task restart | Supervised task restart or MCU reset |
| Event log | Diagnostic or non-volatile fault log |
| Dashboard | Local engineering and validation tool |

## Limitations

This is a local educational simulator, not a certified safety system. It does not currently provide:

- Physical hardware or RTOS integration
- Distributed or networked monitoring
- Authentication or multi-user access
- SQLite persistence
- Maximum recovery-attempt policy
- `FAILED_PERMANENTLY` escalation
- Production-grade event retention and rotation

Potential future enhancements include SQLite storage, recovery backoff, richer metrics, timeline analytics, hardware-in-the-loop adapters, and additional fault models.

## Documentation

- [Beginner project guide](docs/06_PROJECT_GUIDE.md)
- [Product requirements](docs/01_PRD.md)
- [Software requirements](docs/02_SRS.md)
- [Architecture](docs/03_ARCHITECTURE.md)
- [UI/UX specification](docs/04_UIUX.md)
- [Development plan](docs/05_DEVELOPMENT_PLAN.md)
- [Combined project and milestone report](reports/combined-project-report.md)
- [Individual milestone reports](reports/)

## Resume-ready summary

Built a Python-based embedded watchdog and fault-recovery simulator using concurrent periodic tasks, thread-safe heartbeat monitoring, configurable failure injection, automatic task restart, fresh-heartbeat recovery confirmation, structured JSONL event persistence, and a Streamlit operations dashboard. Added automated unit/integration tests and validated repeated recovery behavior with a ten-minute, 120-injection soak test.

## License

This repository is intended for educational and portfolio use.
