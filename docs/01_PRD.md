# Product Requirements Document (PRD)
## Embedded Watchdog & Fault Recovery Simulator

**Version:** 0.1 (living document — update as you build)
**Owner:** Khushi
**Status:** Implemented MVP / official project reference

---

## 1. Problem Statement

Real-time embedded systems (automotive ECUs, industrial controllers, IoT devices, medical devices) run multiple periodic tasks that must execute reliably within strict timing windows. When a task hangs, deadlocks, or stops responding — due to a bug, blocked resource, or external fault — the system needs a **watchdog mechanism** to detect the failure and recover, because a silent hang in safety- or mission-critical firmware can cause anything from a frozen dashboard to a real safety hazard.

Most software engineers (including CS freshers) never get hands-on exposure to this pattern because it normally requires real hardware, an RTOS, and a lab setup. There is no easy, safe, visual way to **experiment with watchdog/fault-recovery concepts** without an embedded lab.

**This project solves that** by simulating the core mechanics of a firmware watchdog system in software — periodic tasks, heartbeats, missed-heartbeat detection, fault injection, and automatic recovery — with a live dashboard, so the concepts can be learned, demonstrated, and reasoned about without any real hardware.

---

## 2. Target Users

| User | Why they'd use it |
|---|---|
| **You (primary user)** | Learn embedded/firmware reliability patterns hands-on; build a credible, demoable resume project bridging software engineering and firmware/embedded interest |
| **Recruiters / interviewers** | Quickly see a working, visual demonstration of systems-level thinking (concurrency, fault tolerance, monitoring) — not just another CRUD app |
| **Other students/engineers learning embedded concepts** | Could reuse or fork the simulator to learn watchdog patterns without hardware |

This is a **portfolio/learning project**, not a commercial product — so "users" are mainly you and anyone evaluating your work (interviewers, reviewers on GitHub).

---

## 3. Goals

1. Demonstrate a working simulation of **periodic task execution + heartbeat monitoring** in a concurrent environment.
2. Demonstrate a **watchdog** that detects missed heartbeats/stalls and triggers **recovery** (task restart) with tracked history.
3. Demonstrate **fault injection** (simulated hangs, communication failures) to prove the recovery mechanism actually works, not just exists.
4. Provide a **real-time dashboard** that makes the whole system observable at a glance.
5. Produce something you understand deeply enough to **explain and defend in an interview**, not something copy-pasted.

### Non-goals
- This is not a real RTOS or a certified safety system.
- It does not run on real embedded hardware/MCU in v1 (see "Out of Scope").
- It is not trying to be a general-purpose monitoring product (like Prometheus/Grafana).

---

## 4. Core Features

### F1 — Task Simulation Engine
Simulated firmware "tasks" that run periodically (e.g., every N ms/ticks) on their own thread/process, each representing something a real embedded task might do (sensor read, comms poll, control loop, logging).

### F2 — Heartbeat / Health Monitoring
Each task emits a periodic "heartbeat" (timestamped signal) to a central monitor. The monitor tracks the last-seen heartbeat per task and computes health status (healthy / late / stalled).

### F3 — Watchdog & Missed-Heartbeat Detection
A watchdog component polls task health on its own cycle, compares against a per-task timeout threshold, and flags a task as "stalled" when it misses N consecutive heartbeats (configurable).

### F4 — Fault Injection
A controllable mechanism (CLI flag, config, or dashboard button) to simulate faults on demand:
- Task hang (infinite loop / sleep beyond timeout)
- Communication failure (heartbeat dropped/delayed)
- Crash (task thread dies) — stretch goal

### F5 — Recovery Mechanism
On detecting a stalled/faulted task, the watchdog restarts the task (spawns a fresh thread/process for it), logs the recovery attempt, and tracks how many times each task has been recovered.

### F6 — Real-Time Dashboard
A Python dashboard (Streamlit/Dash/Tkinter — decided in Architecture doc) that shows, live:
- Per-task status (healthy/late/stalled/recovering)
- Heartbeat timeline/history
- Recovery attempt count & history log
- Currently injected faults
- Overall system health summary

### F7 — Event Log / Recovery History
A persistent (in-memory minimum, file/DB stretch) log of every fault, detection, and recovery event with timestamps, for post-hoc review — mirrors how real embedded systems keep fault logs.

---

## 5. MVP Scope

To keep this buildable and demoable without scope creep, the **MVP is F1–F6, minimally**:

**In MVP:**
- 3–5 simulated periodic tasks running concurrently (threads are enough; no need for multi-process)
- Heartbeat monitoring with configurable timeout per task
- Watchdog loop that detects missed heartbeats
- Manual fault injection for at least "task hang" and "heartbeat drop"
- Auto-restart of a stalled task, with a recovery counter
- A live dashboard showing task states, heartbeat freshness, and recovery counts, refreshing in real time (polling is fine — no need for websockets in MVP)
- A basic in-memory event log visible on the dashboard

**Explicitly deferred past MVP:** persistence to disk/DB, multi-process isolation, a "crash" fault type, historical charts/analytics, authentication, remote/networked tasks, config UI (start with a config file).

---

## 6. User Stories

1. *As a developer running the simulator*, I want to start N periodic tasks with one command, so I can see the baseline healthy system running.
2. *As a developer*, I want to inject a "hang" fault into a specific task, so I can observe the watchdog detect it.
3. *As a developer*, I want the watchdog to automatically restart a stalled task, so I can see the recovery flow end-to-end without manual intervention.
4. *As a developer*, I want to see, in real time, which tasks are healthy/late/stalled/recovering, so I don't have to read raw logs to understand system state.
5. *As a developer*, I want to see a history of missed heartbeats and recoveries per task, so I can reason about which tasks are least reliable.
6. *As an interviewer/reviewer*, I want to run the project with clear setup instructions and see a convincing live demo within a couple of minutes, so I can evaluate the work quickly.

---

## 7. Success Metrics

Since this is a learning/portfolio project, "success" is measured differently than a commercial product:

- **Functional correctness:** Injected faults are detected within the configured timeout window, 100% of the time in test runs.
- **Recovery reliability:** A stalled task is restarted and returns to "healthy" heartbeat status within a defined recovery window (e.g., 1 monitoring cycle).
- **Observability:** Dashboard reflects true system state with under ~1s of visible lag.
- **Explainability:** You can walk an interviewer through the architecture and every design decision without hesitation.
- **Portfolio outcome:** Project has a clean GitHub repo (README, demo GIF/video, clear code) suitable for linking on a resume.

---

## 8. Assumptions

- Concurrency will be simulated with Python threads (or asyncio) rather than real hardware/interrupts — this is a **software model** of firmware behavior, not firmware itself.
- "Real-time" here means "responsive on human-observable timescales" (sub-second), not hard real-time guarantees.
- You are building this solo, so scope must stay realistic for one person alongside other commitments.
- Python is an acceptable implementation language for the simulation, even though real firmware would typically use C/C++ — the project is about **demonstrating the pattern**, not shipping to an MCU (v1).

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Scope creep (wanting to add RTOS-level realism, multi-process, networking, etc.) | Lock MVP scope in this doc; treat extras as a clearly labeled "Phase 2" backlog |
| Python's GIL/threading quirks make "hang" simulation behave unexpectedly | Prototype the fault-injection mechanism early (Week 1) before building the full dashboard |
| Dashboard becomes the most polished part while the "engineering" (watchdog logic) is thin | Make sure watchdog/recovery logic + tests are solid before investing further in UI polish |
| Project reads as "just a Python script" rather than "embedded systems knowledge" | Explicitly document the mapping to real firmware concepts (heartbeats, watchdog timers, fault recovery) in the README and architecture doc, and mention it ties to your firmware-learning direction |
| Running out of time/motivation mid-project | Keep MVP small enough to finish in a defined number of weeks (see Development Plan) before adding stretch goals |

---

## 10. Out of Scope (v1)

- Running on real embedded hardware (e.g., an actual MCU, RTOS like FreeRTOS)
- Networked/distributed tasks across machines
- Authentication, multi-user access to the dashboard
- Persistent database storage (file-based logs are enough for v1)
- Historical analytics / trend dashboards beyond the current run
- Automated alerting (email/SMS) on faults

*(These are good "Phase 2 / future work" bullet points for your README — showing you know how to scope, and where the project could grow.)*

---

## 11. Acceptance Criteria (MVP Definition of Done)

The MVP is considered done when:

- [ ] 3–5 simulated tasks run concurrently, each emitting periodic heartbeats
- [ ] The watchdog correctly flags a task as "stalled" after it misses its configured heartbeat threshold
- [ ] At least two fault types (hang, heartbeat drop) can be injected on demand
- [ ] A stalled task is automatically restarted, and the recovery is logged with a timestamp and updated recovery count
- [ ] The dashboard displays live task status, heartbeat freshness, fault state, and recovery history, updating without manual refresh
- [ ] The system runs for at least 10 minutes continuously without crashing, correctly detecting and recovering from repeated injected faults
- [ ] A README explains the concept, architecture, how to run it, and includes a demo screenshot/GIF
