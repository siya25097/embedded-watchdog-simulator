# System Architecture Document
## Embedded Watchdog & Fault Recovery Simulator

**Version:** 0.1 (implemented MVP; official project reference)
**Based on:** PRD v0.1, SRS v0.1

---

## 1. Design Philosophy

Keep it practical, not over-engineered:
- This is a **single-process Python application** simulating concurrency internally. No microservices, no message brokers, no distributed systems infrastructure — that would be solving a problem this project doesn't have.
- Favor Python's standard library (`threading`, `queue`, `logging`, `dataclasses`) over heavy frameworks wherever it's sufficient.
- Keep the "firmware simulation" logic completely decoupled from the "dashboard" logic, so each can be understood, tested, and explained independently — this separation is itself a good thing to point to in an interview.

---

## 2. Recommended Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Core simulation | Python 3.11+, `threading` + `queue` | You already know Python well; threads are enough since tasks are I/O-bound-style simulations (sleeping), not CPU-heavy — no need for multiprocessing |
| Alternative concurrency model | `asyncio` (optional v2 exploration) | Worth trying as a "Phase 2" rewrite to demonstrate async understanding too, but don't start here — threading is more intuitive for modeling independent periodic tasks with real wall-clock timing |
| Watchdog | Plain Python thread with a polling loop | Simplicity > cleverness; a watchdog is conceptually just "check state, act on state" on a timer |
| State storage (runtime) | In-memory Python objects (`dataclasses` + a thread-safe registry, e.g., using `threading.Lock` or a `queue.Queue` for events) | No need for a database for MVP; keep it simple |
| Event log persistence | JSON lines file via the standard library; SQLite remains future work | JSONL preserves the append-only event model without adding a database dependency |
| Config | JSON or YAML file (`pyyaml` if YAML) | Simple, human-editable, matches FR-5 |
| Dashboard | **Streamlit** (recommended) | Fastest path to a real-time, auto-refreshing Python dashboard with almost no frontend code — ideal for a solo learning project on a deadline. Alternative: **Dash (Plotly)** if you want more layout control, or **Tkinter** if you want a desktop-native app with zero web dependency (slightly more manual "real-time refresh" plumbing) |
| Testing | `pytest` | Standard, matches SRS §11 acceptance-criteria format |
| Logging | stdlib `logging` module | No need for a bespoke logging system |

**Recommendation for MVP:** Python stdlib + `threading` for the core, **Streamlit** for the dashboard, JSON config file, in-memory state with an optional JSON-lines event log for persistence. This keeps the dependency list to essentially `streamlit` (+ `pyyaml` if you choose YAML) plus the standard library.

---

## 3. System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Watchdog Simulator App                   │
│                                                               │
│  ┌───────────────┐   heartbeats   ┌─────────────────────┐    │
│  │  Task Manager │───────────────▶│  Heartbeat Registry  │    │
│  │ (spawns/kills │                │ (thread-safe state   │    │
│  │  task threads)│                │  per task_id)        │    │
│  └───────┬───────┘                └──────────┬───────────┘    │
│          │ spawns                            │ read           │
│          ▼                                   ▼                │
│  ┌───────────────┐                 ┌─────────────────────┐    │
│  │  Task Threads  │                 │      Watchdog        │    │
│  │ (Task 1..N,    │                 │  (polls registry,    │    │
│  │  each periodic)│                 │  detects stalls,     │    │
│  └───────┬───────┘                 │  triggers recovery)  │    │
│          │                          └──────────┬───────────┘   │
│          │ faults injected here                │ restart cmd   │
│          ▼                                     ▼               │
│  ┌───────────────┐                 ┌─────────────────────┐    │
│  │ Fault Injector │                 │   Recovery Manager   │    │
│  │ (CLI/dashboard │                 │ (restarts task via   │    │
│  │  triggered)    │                 │  Task Manager, logs) │    │
│  └───────────────┘                 └──────────┬───────────┘    │
│                                                 │ events         │
│                                                 ▼               │
│                                    ┌─────────────────────┐     │
│                                    │     Event Logger      │     │
│                                    │ (in-memory list +     │     │
│                                    │  optional file/SQLite)│     │
│                                    └──────────┬───────────┘     │
│                                                │ reads           │
└────────────────────────────────────────────────┼───────────────┘
                                                  ▼
                                     ┌─────────────────────┐
                                     │   Streamlit Dashboard │
                                     │ (polls registry +     │
                                     │  event log, renders   │
                                     │  live state)          │
                                     └─────────────────────┘
```

### Component responsibilities

- **Task Manager** — owns the lifecycle of task threads: start, stop, restart. This is the *only* component allowed to spawn/kill task threads (keeps restart logic centralized and testable).
- **Task Threads** — the simulated firmware tasks. Each runs a loop: do work → emit heartbeat → sleep for period. Susceptible to fault injection (e.g., a hang fault makes it skip the heartbeat emission or sleep indefinitely).
- **Heartbeat Registry** — a thread-safe shared structure (`dict[task_id, TaskState]`) protected by a lock, updated by task threads and read by the watchdog and dashboard.
- **Watchdog** — its own thread; on a fixed poll interval, evaluates every task's last-heartbeat age against its timeout/threshold, updates status, and calls the Recovery Manager when a task crosses into `STALLED`.
- **Fault Injector** — a thin interface (CLI command and/or Streamlit button) that flips a flag or sends a signal a task thread checks, or directly manipulates a task thread to simulate hang/comm-failure.
- **Recovery Manager** — receives "this task is stalled" from the watchdog, asks the Task Manager to restart that task's thread, updates recovery counters, and writes a `RECOVERY_ATTEMPTED`/`SUCCEEDED`/`FAILED` event.
- **Event Logger** — append-only thread-safe event store; the dashboard also writes JSON Lines to `events.jsonl` for local persistence.
- **Streamlit Dashboard** — a separate process/script that reads from the same shared state (see §5 on process model) and renders it, refreshing on an interval using `st.rerun()`/fragments or `streamlit-autorefresh`.

---

## 4. Data Flow

1. Each Task Thread executes its cycle → writes a heartbeat (timestamp) into the Heartbeat Registry.
2. The Watchdog polls the Heartbeat Registry on its own interval → compares "now − last heartbeat" to the configured timeout/threshold → updates each task's status.
3. If a task crosses the stall threshold → Watchdog emits an event to the Event Logger and calls the Recovery Manager.
4. Recovery Manager asks the Task Manager to kill and respawn that task's thread → logs `RECOVERY_ATTEMPTED`.
5. Once the respawned task emits a fresh heartbeat, the Watchdog (on its next poll) sees status return to `HEALTHY` → Recovery Manager/Watchdog logs `RECOVERY_SUCCEEDED`.
6. The Fault Injector, on command, directly manipulates a target task thread's behavior (e.g., sets a `hang=True` flag the task loop checks, or delays/drops its heartbeat write) → logs `FAULT_INJECTED`.
7. The Dashboard, independently, polls the Heartbeat Registry + Event Logger on its own refresh cycle and renders current state — it is a **read-only observer** and never mutates simulation state directly (except via explicit fault-injection controls, which go through the same Fault Injector interface as the CLI).

---

## 5. Process/Threading Model

**Recommended for MVP (simplest correct option):** run everything — task threads, watchdog thread, and the Streamlit dashboard — **inside the same Python process**, using Streamlit's own execution model (Streamlit reruns your script on each interaction/refresh, so the simulation should be started once and kept alive via `st.session_state` plus a background thread, not restarted on every rerun).

Key implementation note to research early (this is the trickiest integration point): Streamlit apps rerun the whole script on each refresh, so the task/watchdog threads must be started **once** and stored somewhere that survives reruns (e.g., a module-level singleton or `st.session_state` guarded by a "already started" check). Prototype this in Week 1 (see Development Plan) before building the rest of the dashboard, since it's the highest-risk integration point.

*(If this proves awkward, an acceptable fallback architecture is: simulation engine runs as a separate standalone script/process that writes state to a small SQLite file or JSON file, and the Streamlit dashboard is a separate process that just reads that file on a timer. This decouples them completely at the cost of slightly higher latency — document whichever you choose and why.)*

---

## 6. Storage

- **Runtime state:** in-memory only (Python objects), MVP.
- **Event history (stretch):** SQLite file (`watchdog_events.db`) with a single `events` table matching the Event Log Entry schema from the SRS, or a simpler append-only JSON-lines file (`events.jsonl`) if you want to avoid SQL entirely — pick SQLite if you want to showcase SQL skills (you already list SQL as a skill), since a resume project that touches Python + concurrency + SQL is a stronger combination.

---

## 7. APIs

No external/network APIs in v1 — this is a self-contained local application. If a "Phase 2" adds a REST API (e.g., FastAPI) to expose task state for external tooling, document it there rather than in v1 scope.

---

## 8. Authentication

Not applicable (see SRS §7) — local, single-user, no login screen.

---

## 9. Security

- No secrets, credentials, or sensitive data involved.
- If running the Streamlit dashboard, bind to `localhost` (Streamlit's default) rather than `0.0.0.0` unless you deliberately want to demo it over a network.
- Input validation on config file loading (SRS §6) to avoid crashes from malformed configs — this is the main "security-adjacent" concern here (robustness, not attack surface).

---

## 10. Deployment

- **Local run only** for v1: `pip install -r requirements.txt` → `streamlit run app.py` (or `python main.py` if you go the two-process fallback route).
- Package as a proper Python project (`pyproject.toml` or `requirements.txt`, a clear folder structure — see Development Plan) so it's trivial for a reviewer to clone and run.
- **Stretch:** containerize with a simple Dockerfile so reviewers with no Python environment can run `docker run` — nice resume-visible detail, but not required for MVP.

---

## 11. Monitoring (of the simulator itself)

- Application-level logging via Python's `logging` module (console output at minimum) so you can debug the simulator itself during development — separate from the *simulated* watchdog/heartbeat logic, but just as important for your own development process.
- Optional: log rotation isn't needed for a project this size — a single log file per run is fine.

---

## 12. Scalability

Explicitly **not a goal** — this simulates a small embedded system (a handful of tasks), not a distributed fleet. If asked in an interview "how would this scale," the honest and correct answer is: this specific in-process threading model wouldn't scale past dozens of tasks, and a real large-scale version would move to a proper message bus and multi-process/distributed workers — but that's intentionally out of scope here, since the point is to demonstrate the *watchdog/fault-recovery pattern* clearly, not to build infrastructure for scale. Having this answer ready is more impressive than pretending the toy project scales.

---

## 13. Mapping to Real Firmware Concepts (for your own understanding + interview talking points)

| This project | Real embedded equivalent |
|---|---|
| Task thread + periodic loop | RTOS task / FreeRTOS task with a periodic timer |
| Heartbeat write to registry | Task "kicking" a watchdog timer register |
| Watchdog poll + timeout check | Hardware/software Watchdog Timer (WDT) expiring |
| Fault injection (hang) | A real bug: infinite loop, deadlock, blocked I/O in firmware |
| Recovery Manager restart | WDT-triggered MCU reset / task supervisor restart (like an RTOS task supervisor or a Linux systemd restart policy) |
| Event log | Fault log stored in non-volatile memory for post-mortem debugging on real hardware |

Keep this table (or your own version of it) in the README — it's what turns this from "a Python threading exercise" into "a demonstrated understanding of embedded reliability patterns," which is the whole point per your PRD goals.
