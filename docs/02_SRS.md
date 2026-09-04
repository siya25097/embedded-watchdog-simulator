# Software Requirements Specification (SRS)
## Embedded Watchdog & Fault Recovery Simulator

**Version:** 0.1 (implemented MVP; official project reference)
**Based on:** PRD v0.1

---

## 1. Purpose & Scope

This document specifies the functional and non-functional requirements for the Embedded Watchdog & Fault Recovery Simulator, a single-user, locally-run Python application that simulates periodic firmware tasks, heartbeat-based health monitoring, fault injection, and watchdog-driven recovery, visualized via a real-time dashboard.

---

## 2. User Roles & Permissions

This is a **single-role, single-user, local application** — there is no multi-tenancy or auth in v1.

| Role | Description | Permissions |
|---|---|---|
| **Operator** (the only role) | The person running the simulator (you, or an interviewer/reviewer) | Start/stop simulation, configure tasks, inject faults, view dashboard, view logs |

*Note: if a future version adds a web-hosted multi-user dashboard, roles like "Viewer" (read-only dashboard) vs "Operator" (can inject faults) would be introduced then — out of scope for v1.*

---

## 3. Functional Requirements

Each requirement has an ID for traceability into the Development Plan and testing.

### 3.1 Task Simulation

- **FR-1:** The system shall support running a configurable number of simulated tasks (minimum 3, no hard upper limit) concurrently.
- **FR-2:** Each task shall run on its own thread (or async coroutine) with a configurable period (e.g., 500ms, 1s, 2s).
- **FR-3:** Each task shall perform a trivial simulated "unit of work" per cycle (e.g., sleep + counter increment + optional simulated computation) to represent real firmware work.
- **FR-4:** Each task shall emit a heartbeat (a timestamp + task ID) to the central monitor immediately after completing each cycle.
- **FR-5:** Task configuration (name, period, timeout threshold) shall be defined in a config file (JSON/YAML) or a config module, not hardcoded inline in application logic.

### 3.2 Heartbeat Monitoring

- **FR-6:** The system shall maintain, for every task, the timestamp of its most recently received heartbeat.
- **FR-7:** The system shall classify each task's health status as one of: `HEALTHY`, `LATE`, `STALLED`, `RECOVERING`, based on time elapsed since last heartbeat vs. its configured timeout.
- **FR-8:** Heartbeat records shall be thread-safe to read/write, since multiple task threads write concurrently while the watchdog and dashboard read.

### 3.3 Watchdog & Fault Detection

- **FR-9:** A watchdog process/thread shall poll all task health states on its own fixed interval (e.g., every 250ms), independent of task periods.
- **FR-10:** The watchdog shall mark a task `STALLED` when it has missed N consecutive expected heartbeats (N configurable per task, default 2).
- **FR-11:** The watchdog shall log every transition into `STALLED` state with a timestamp and task ID.
- **FR-12:** The watchdog shall not falsely flag a healthy, on-time task as stalled (i.e., threshold logic must account for normal jitter in scheduling).

### 3.4 Fault Injection

- **FR-13:** The system shall provide a mechanism (CLI command, dashboard control, or both) to inject a "hang" fault into a specified task, causing it to stop emitting heartbeats.
- **FR-14:** The system shall provide a mechanism to inject a "communication failure" fault, causing a task's heartbeat to be dropped or delayed without killing the task itself.
- **FR-15:** Injected faults shall be logged with task ID, fault type, and timestamp at the moment of injection.
- **FR-16:** The system shall allow clearing/resolving a fault manually as well as via automatic recovery.

### 3.5 Recovery Mechanism

- **FR-17:** On detecting a `STALLED` task, the watchdog shall attempt to restart that task's thread/process automatically.
- **FR-18:** The system shall track, per task, the total number of recovery attempts and the timestamp of the most recent recovery.
- **FR-19:** After a successful restart, the task shall resume emitting heartbeats and its status shall return to `HEALTHY` once a fresh heartbeat is received.
- **FR-20:** The system shall log every recovery attempt, including whether it succeeded (task resumed heartbeats within a grace period) or failed.
- **FR-21 (stretch):** The system shall support a configurable max-recovery-attempts limit per task, after which the task is marked `FAILED_PERMANENTLY` instead of retried indefinitely — mirrors real watchdog "give up and alert" behavior.

### 3.6 Dashboard

- **FR-22:** The dashboard shall display, per task: name, current status, last heartbeat time (or "time since last heartbeat"), and recovery count.
- **FR-23:** The dashboard shall visually distinguish task states (e.g., color coding: green=healthy, yellow=late, red=stalled, blue=recovering).
- **FR-24:** The dashboard shall display a chronological event log (faults injected, stalls detected, recoveries performed).
- **FR-25:** The dashboard shall update automatically (polling or push) without requiring a manual page refresh, at a refresh interval of ≤1 second.
- **FR-26:** The dashboard shall expose controls to inject faults into a selected task (may be a stretch goal if CLI-only injection is used for MVP — see PRD).

### 3.7 Logging & Persistence

- **FR-27:** All events (heartbeats optionally, stalls, faults, recoveries) shall be written to an application log (console and/or file) with timestamps.
- **FR-28 (stretch):** Event history is persisted to the gitignored local `events.jsonl` file by the dashboard; SQLite remains future work.

---

## 4. Business Rules

- BR-1: A task is never considered "recovered" until it emits at least one fresh heartbeat post-restart — recovery is confirmed by evidence, not assumed on restart alone.
- BR-2: Fault injection targets a specific task by ID; injecting a fault on a non-existent task ID is a no-op with a warning, not a crash.
- BR-3: The watchdog polling interval must be strictly shorter than the shortest task's timeout threshold, or detection will systematically lag (this is a configuration validation rule, not just a note).

---

## 5. Data Requirements

### Core entities

**Task Config**
- `task_id` (string, unique)
- `period_ms` (int)
- `timeout_ms` (int) — must be > period_ms
- `missed_heartbeat_threshold` (int, default 2)

**Task Runtime State**
- `task_id`
- `status` (enum: HEALTHY / LATE / STALLED / RECOVERING / FAILED_PERMANENTLY)
- `last_heartbeat_ts`
- `recovery_count`
- `last_recovery_ts`

**Event Log Entry**
- `timestamp`
- `event_type` (enum: HEARTBEAT, FAULT_INJECTED, STALL_DETECTED, RECOVERY_ATTEMPTED, RECOVERY_SUCCEEDED, RECOVERY_FAILED)
- `task_id`
- `details` (free text/dict, e.g., fault type)

---

## 6. Validations

- V-1: `timeout_ms` must be strictly greater than `period_ms` at config load time; reject/warn on invalid configs.
- V-2: Task IDs must be unique across the config; reject duplicate IDs at startup.
- V-3: Fault injection commands must reference an existing, currently-running task ID.
- V-4: `missed_heartbeat_threshold` must be a positive integer ≥ 1.

---

## 7. Authentication & Authorization

Not applicable in v1 — single local user, no network exposure, no login. If the dashboard is later exposed over a network (stretch goal), basic auth would need to be added at that time; explicitly flagged as a security gap for v1 in the Architecture Document.

---

## 8. Error Handling & Edge Cases

- **E-1:** What happens if a task thread crashes unexpectedly (not just "hangs")? → Should be treated like a stall (no heartbeats) and trigger the same recovery path; document this explicitly since it's a slightly different failure mode than a hang.
- **E-2:** What happens if the watchdog itself fails/crashes? → Out of scope for full self-healing in v1, but should fail loudly (log + exit) rather than silently stop monitoring — document as a known limitation.
- **E-3:** What happens if two faults are injected into the same task before recovery completes? → The second injection should be queued/ignored with a log message, not cause undefined behavior.
- **E-4:** What happens on dashboard startup before any heartbeats have been received? → Tasks should show a distinct `INITIALIZING` (or similar) state, not be misclassified as `STALLED`.
- **E-5:** Clock/timing edge cases — since Python threads have scheduling jitter, define a small grace buffer in the "LATE vs STALLED" threshold so normal jitter doesn't get misclassified as a fault.

---

## 9. Security Considerations

- No sensitive data is handled (this is a simulation with synthetic tasks), so security scope is minimal.
- If the dashboard framework (e.g., Streamlit) binds to `0.0.0.0` by default, document that it should be run bound to `localhost` only unless intentionally shared, to avoid unintentionally exposing it on a network.

---

## 10. Performance Requirements

- **P-1:** The system shall support at least 5 concurrent tasks without missing heartbeat deadlines due to the simulator's own overhead (i.e., the simulation infrastructure should not itself become the bottleneck).
- **P-2:** Dashboard refresh latency (time from a real state change to it being visible) shall be ≤ 1 second under normal load.
- **P-3:** Watchdog detection latency shall be bounded by `watchdog_poll_interval + (missed_heartbeat_threshold × task_period)` — this formula should be documented so detection time is predictable and explainable in an interview.

---

## 11. Acceptance Criteria

Each functional requirement (FR-1 through FR-27) should be verifiable via a manual test script or automated test before being marked complete. Suggested test format per requirement:

> **Given** [task config / system state], **when** [action, e.g., fault injected], **then** [expected observable outcome within X ms].

Example:
> Given a task with period=1000ms, timeout=2500ms, threshold=2; when its thread is killed (hang simulated); then the watchdog shall mark it STALLED within 2500ms and log a recovery attempt within 2750ms.

A simple `tests/` folder with these Given/When/Then cases (as pytest tests where feasible) is part of the Definition of Done in the Development Plan.
