# Embedded Watchdog & Fault Recovery Simulator

An in-process Python simulator for periodic firmware-style tasks, heartbeat monitoring, fault injection, watchdog detection, and automatic recovery. It demonstrates embedded reliability concepts without requiring hardware or an RTOS.

## Quick start

```bash
git clone <repository-url>
cd embedded-watchdog-simulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python3 -m pytest -q
PYTHONPATH=. python3 -m streamlit run dashboard/app.py
```

Open the local Streamlit URL, wait for tasks to become `HEALTHY`, select a task, and inject a `Hang` or `Comm Failure` fault. Observe:

```text
HEALTHY → LATE → STALLED → RECOVERING → HEALTHY
```

## Console demos and validation

```bash
# Print periodic task heartbeats
PYTHONPATH=. python3 scripts/run_tasks.py

# Print live watchdog states
PYTHONPATH=. python3 scripts/watchdog_demo.py

# Run the complete test suite
PYTHONPATH=. python3 -m pytest -q

# Run a repeated fault/recovery soak test
PYTHONPATH=. python3 scripts/soak_test.py --duration 600 --fault-interval 5
```

The simulator uses `PYTHONPATH=.` because it is currently run directly from the repository rather than installed as a package.

## Architecture

```text
 Task Threads ── heartbeat ──> Thread-safe Registry ──> Watchdog
      ▲                               ▲                    │
      │                               │                    │ stalled
      └──── FaultInjector              │                    ▼
                              EventLogger       RecoveryManager
                                                           │
                                                           ▼
                                                   TaskManager restart
                                                           │
                                                           └─ fresh heartbeat

                                      Streamlit Dashboard reads all runtime state
```

### Components

- `Task`: periodic thread that performs work and emits heartbeats.
- `Registry`: synchronized last-heartbeat state.
- `Watchdog`: independent polling and `HEALTHY`/`LATE`/`STALLED` classification.
- `FaultInjector`: hang and communication-failure simulation.
- `TaskManager`: centralized task lifecycle and restart ownership.
- `RecoveryManager`: restart attempts and fresh-heartbeat confirmation.
- `EventLogger`: synchronized chronological event history with optional JSONL persistence.
- `dashboard/app.py`: single-screen Streamlit operator interface.

## Configuration

Tasks are defined in [config/tasks.yaml](config/tasks.yaml). The sample configuration includes five tasks, and the dashboard sidebar lets you edit each task's period, timeout, and missed-heartbeat threshold at runtime. Applying changes restarts the simulation with the new timing values, which is useful for slow-motion demonstrations.

```yaml
tasks:
  - id: task-A
    period: 1
    timeout_ms: 3000
    missed_heartbeat_threshold: 2
```

The loader validates positive periods, unique IDs, `timeout_ms > period * 1000`, and `missed_heartbeat_threshold >= 1`.

For a slower fault demonstration, set a task period to `3–5` seconds and its timeout to at least twice the period in milliseconds. Then inject a fault and observe the state transitions without rushing.

## Mapping to firmware concepts

| Simulator | Embedded equivalent |
|---|---|
| Periodic task thread | RTOS task with a periodic timer |
| Registry heartbeat | Task kicking a watchdog timer |
| Watchdog polling | Hardware/software watchdog timeout check |
| Hang fault | Infinite loop, deadlock, or blocked firmware I/O |
| Recovery restart | MCU reset or supervised RTOS task restart |
| Event log | Non-volatile fault log for post-mortem analysis |

## Scope and limitations

This is a local educational simulator, not a certified safety system. It intentionally does not include real hardware, networked tasks, authentication, or distributed scaling. The dashboard persists events to the local, gitignored `events.jsonl` file; SQLite persistence is future work.

## Project documentation

- [Product requirements](docs/01_PRD.md)
- [Software requirements](docs/02_SRS.md)
- [Architecture](docs/03_ARCHITECTURE.md)
- [UI/UX](docs/04_UIUX.md)
- [Development plan](docs/05_DEVELOPMENT_PLAN.md)
- [Milestone reports](reports/)
