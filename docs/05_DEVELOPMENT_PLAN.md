# Development Plan
## Embedded Watchdog & Fault Recovery Simulator

**Version:** 0.1 (living document — check items off as you go)
**Based on:** PRD, SRS, Architecture, UI/UX docs v0.1

---

## 1. Guiding Principle

Build in this order: **core simulation logic → watchdog/recovery logic → fault injection → dashboard.**
Do NOT start with the dashboard. The dashboard is the "visible" part but the watchdog/recovery logic is the "engineering" part — get that solid and tested first, or you risk a pretty UI wrapped around a fragile core (a common resume-project trap).

---

## 2. Suggested Project Structure

```
watchdog-simulator/
├── README.md
├── requirements.txt
├── config/
│   └── tasks.yaml            # task configs (FR-5)
├── src/
│   ├── task.py                # Task thread logic
│   ├── registry.py            # Heartbeat Registry (thread-safe state)
│   ├── watchdog.py            # Watchdog polling + stall detection
│   ├── recovery.py            # Recovery Manager
│   ├── fault_injector.py      # Fault injection logic
│   ├── event_log.py           # Event Logger
│   └── task_manager.py        # Spawns/kills/restarts task threads
├── dashboard/
│   └── app.py                 # Streamlit dashboard
├── tests/
│   ├── test_watchdog.py
│   ├── test_recovery.py
│   └── test_fault_injection.py
└── docs/                       # your 5 living documents
    ├── 01_PRD.md
    ├── 02_SRS.md
    ├── 03_ARCHITECTURE.md
    ├── 04_UIUX.md
    └── 05_DEVELOPMENT_PLAN.md
```

---

## 3. Milestones & Roadmap

### Milestone 0 — Setup (½ day)
- [ ] Init git repo, virtual environment, `requirements.txt` (start with just `pyyaml`, `pytest`, `streamlit`)
- [ ] Create the folder structure above
- [ ] Copy these 5 docs into `docs/`
- **Definition of Done:** `git init` done, empty project runs (`python -c "import src"` doesn't error), docs committed.

### Milestone 1 — Core Task Simulation (FR-1 to FR-5) (1–2 days)
- [ ] Implement `Task` (thread) with configurable period, doing simulated "work" + emitting a heartbeat each cycle
- [ ] Implement `Registry` — thread-safe dict of `task_id → TaskState` (last heartbeat ts, status)
- [ ] Implement config loading from `tasks.yaml` with validation (V-1, V-2, V-4 from SRS)
- [ ] Write a throwaway script that starts 3 tasks and prints heartbeats to console
- **Dependencies:** None — this is the foundation.
- **Definition of Done:** Running the script shows 3 tasks printing heartbeats at their configured periods, no crashes over a 2-minute run.

### Milestone 2 — Watchdog & Status Classification (FR-6 to FR-12) (1–2 days)
- [x] Implement `Watchdog` thread: polls registry on its own interval, classifies each task HEALTHY/LATE/STALLED per BR-3 and E-5 (jitter buffer)
- [x] Log every STALLED transition (FR-11)
- [x] Write `tests/test_watchdog.py`: simulate a task that stops heartbeating (mock/manual) and assert it's flagged STALLED within expected time (per SRS §11 Given/When/Then format)
- **Dependencies:** Milestone 1.
- **Definition of Done:** Automated test passes; manually killing a task thread results in correct STALLED detection within the documented latency formula (SRS P-3).

### Milestone 3 — Fault Injection (FR-13 to FR-16) (1 day)
- [x] Implement `FaultInjector`: programmatic interface to inject "hang" and "comm failure" into a named task
- [x] Ensure fault injection logs an event (FR-15) and handles double-injection edge case (E-3)
- [x] Write `tests/test_fault_injection.py` and integration tests for task/watchdog behavior
- **Dependencies:** Milestones 1–2.
- **Definition of Done:** Can trigger both fault types via a simple script/CLI and see the watchdog correctly detect each.

### Milestone 4 — Recovery Mechanism (FR-17 to FR-21) (1–2 days)
- [x] Implement `TaskManager.restart_task(task_id)` — cleanly stops and respawns a task thread
- [x] Implement `RecoveryManager`: triggered by watchdog on STALLED, calls `TaskManager.restart_task`, tracks recovery count, logs RECOVERY_ATTEMPTED/SUCCEEDED/FAILED
- [x] Confirm recovery only counted as "succeeded" once a fresh heartbeat is observed (BR-1)
- [ ] (Stretch) Implement max-recovery-attempts → `FAILED_PERMANENTLY` (FR-21)
- [x] Write `tests/test_recovery.py`
- **Dependencies:** Milestones 1–3.
- **Definition of Done:** End-to-end: inject fault → see STALLED → see automatic restart → see status return to HEALTHY → recovery count incremented — all observable via logs/tests without the dashboard yet. **This is the core engineering milestone — the project "works" at this point even without a UI.**

### Milestone 5 — Event Logging (FR-27, optionally FR-28) (½–1 day)
- [x] Centralize all event writes (heartbeats optional, faults, stalls, recoveries) into `EventLogger`
- [x] Console/file logging via stdlib `logging`
- [ ] (Stretch) Persist events to SQLite or JSON-lines
- **Dependencies:** Milestones 1–4 (this mostly formalizes logging already added along the way).
- **Definition of Done:** A single run's full event history can be printed/exported chronologically.

### Milestone 6 — Streamlit Dashboard (FR-22 to FR-26) (2–3 days)
- [ ] **Prototype the threading+Streamlit integration FIRST** (Architecture §5 risk) — get one task's live status rendering and refreshing before building the full layout
- [ ] Build Task Status Grid (colored badges, last-heartbeat, recovery count)
- [ ] Build Fault Injection Panel wired to the same `FaultInjector` used by tests
- [ ] Build Event Log table (reverse-chronological)
- [ ] Apply color/typography/spacing choices from the UI/UX doc
- [ ] Handle loading/empty/error states per UI/UX §7
- **Dependencies:** Milestones 1–5 (dashboard is a view over already-working logic — don't build it against unfinished core logic).
- **Definition of Done:** Full demo loop (UI/UX §2 User Journey, steps 1–6) works end-to-end through the dashboard, refreshing live without manual reload.

### Milestone 7 — Testing, Polish & Bug Fixing (1–2 days)
- [ ] Run the full acceptance criteria checklist from the PRD (§11) and SRS (§11 Given/When/Then cases) against the finished build
- [ ] 10-minute continuous soak test with repeated fault injections (PRD acceptance criterion)
- [ ] Fix any race conditions found in the shared registry (double-check lock usage)
- [ ] Clean up code: consistent naming, docstrings, remove dead/experimental code from prototyping
- **Dependencies:** Milestone 6.
- **Definition of Done:** All PRD §11 and SRS §11 checklist items pass.

### Milestone 8 — Documentation & Demo Packaging (1 day)
- [ ] Finalize README: problem statement (from PRD §1), architecture diagram (from Architecture §3), the "mapping to real firmware concepts" table (Architecture §13), setup/run instructions
- [ ] Record a short demo GIF/video showing the fault-injection → detection → recovery loop
- [ ] Update all 5 living docs to reflect what was actually built (close the loop — note any deviations from the original plan and why, which is itself a good interview talking point)
- [ ] Push final version to GitHub with a clean commit history
- **Dependencies:** Milestone 7.
- **Definition of Done:** A stranger can clone the repo, follow the README, and run a working demo within 5 minutes.

---

## 4. Priorities Summary

| Priority | Milestones | Rationale |
|---|---|---|
| **P0 (must-have for resume-ready MVP)** | 0, 1, 2, 3, 4, 6 (core dashboard views), 7, 8 | This is the PRD's MVP scope — without these, there's no demoable project |
| **P1 (should-have, strengthens the project)** | 5 (structured event logging), stretch parts of 4 (max-retry → FAILED_PERMANENTLY), stretch parts of 6 (timeline chart) | Makes the project noticeably more polished and "production-minded" |
| **P2 (nice-to-have / Phase 2, per PRD Out-of-Scope)** | SQLite persistence, Docker packaging, asyncio rewrite, REST API, multi-process isolation | Good "future work" bullets in the README; don't attempt until P0/P1 are solid |

---

## 5. Estimated Timeline

Assuming solo, part-time work (a few hours most days): **roughly 2–3 weeks** for a solid P0+P1 build, working through Milestones 0–8 in order. Don't compress this by skipping Milestone 4's testing or jumping straight to the dashboard — that's the most common way these projects end up looking unfinished or buggy in a live demo.

---

## 6. Definition of Done (Project-Level)

The project as a whole is "resume-ready" when:
- [ ] Every PRD §11 acceptance criterion is met
- [ ] Every SRS functional requirement (FR-1 to FR-27, minimum) is implemented and covered by at least one test or documented manual test case
- [ ] The dashboard matches the UI/UX document's core screen and states
- [ ] README + demo GIF exist and a fresh clone can be run successfully
- [ ] All 5 docs in `docs/` have been updated to match the final implementation (not just the original plan)
