# Interview Prep — Embedded Watchdog & Fault Recovery Simulator

This is your "know it cold" reference. Not a script to memorize — a map of *why* each piece exists, so you can answer follow-up questions you haven't seen before.

---

## 1. The 30-second pitch (say this first, unprompted)

> "I built a software simulation of an embedded watchdog system — the kind of reliability mechanism real firmware uses to detect and recover from hung tasks. It runs several periodic 'tasks' as threads, each emitting a heartbeat. A watchdog thread independently polls those heartbeats, classifies task health, and triggers automatic recovery when a task stalls — with a rule that recovery only counts as successful once the restarted task proves it's alive again with a fresh heartbeat. I built a live dashboard on top so the whole fault-detect-recover cycle is observable in real time, and backed it with a full test suite plus a soak test for long-run stability."

That last sentence (tests + soak test) is doing real work — it signals you didn't just make something that *looks* like it works.

---

## 2. Walk the architecture (be able to draw this from memory)

```
Task threads --heartbeat--> Registry <--poll-- Watchdog --on_stalled--> RecoveryManager --restart--> TaskManager
                                                    |                         |
                                              FaultInjector <-----------------+ (fault cleared here)
                                                    |
                                              EventLogger <---- everything logs here ----> events.jsonl
                                                    |
                                          Streamlit Dashboard (reads all of the above, read-only except fault controls)
```

**Say the responsibilities out loud until they're automatic:**

- **Task** — a daemon thread; does simulated work, checks if a fault is active on itself, emits a heartbeat if not, sleeps in 0.1s increments (so `stop()` is responsive, not blocking for a full period).
- **Registry** — the *only* shared mutable state task threads touch. A `dict` behind a `threading.Lock`. Every read and write goes through the lock. This is the answer to "where's your concurrency risk and how did you handle it."
- **Watchdog** — its own thread, polls on its *own* interval (independent of task periods — important point, see §4). Classifies each task as INITIALIZING / HEALTHY / LATE / STALLED / RECOVERING.
- **FaultInjector** — holds a dict of `task_id → active fault`. Tasks check this dict themselves each cycle. Guards against double-injection and unknown task IDs.
- **TaskManager** — the *only* component allowed to start/stop/restart task threads. Centralizing this means recovery can never accidentally spawn a duplicate thread for the same task.
- **RecoveryManager** — receives "this task stalled" from the watchdog, clears the fault, asks TaskManager to restart, and — critically — does **not** mark recovery as successful until it separately observes a fresh heartbeat.
- **EventLogger** — thread-safe append-only event history, optionally persisted to `events.jsonl`.
- **Dashboard** — a read-only observer of all of the above, except for the explicit fault-injection/timing controls, which go through the same objects the tests use (not a separate code path).

---

## 3. Data flow — one full fault-recovery cycle, in order

Be ready to narrate this exactly, since it's probably the core "walk me through it" question:

1. Task thread runs its loop, checks `fault_injector.get_fault(self.task_id)` — sees none — writes a heartbeat to the Registry.
2. Someone (dashboard button or `inject_hang()`) calls `FaultInjector.inject_fault(task_id, "hang")`. This locks, checks no fault already exists, records it, logs `FAULT_INJECTED`.
3. On its next loop iteration, the Task thread checks the injector again, *now* sees a fault, and skips the heartbeat write — but the thread itself is still alive (that's what makes it a "hang" and not a crash).
4. The heartbeat in the Registry gets stale. The Watchdog, on its own poll cycle, computes `age = now - last_heartbeat` and reclassifies the task: HEALTHY → LATE → STALLED, once `age` crosses the configured timeout/threshold.
5. The instant the Watchdog sees the transition *into* STALLED (not just "is STALLED" — it checks `previous != "STALLED"` so this only fires once), it logs `STALL_DETECTED` and calls `on_stalled(task_id)`, which is `RecoveryManager.recover`.
6. `RecoveryManager.recover()`: grabs a lock, checks the task isn't already mid-recovery (`_in_progress` set — prevents double-recovery races), increments the recovery counter, logs `RECOVERY_ATTEMPTED`, then — outside the lock — calls `fault_injector.clear_fault(task_id)` and `task_manager.restart_task(task_id)`.
7. `TaskManager.restart_task()` = `stop_task()` (sets the stop event, joins the thread with a timeout, raises if it won't die) followed by `start_task()` (spawns a brand-new `Task` thread).
8. The new Task thread starts its loop fresh, sees no fault (it was cleared in step 6), and emits a heartbeat.
9. The Watchdog's *next* poll sees a fresh heartbeat → reclassifies as HEALTHY. Because the previous state was RECOVERING, it fires `on_healthy(task_id)` → `RecoveryManager.confirm_recovery()`, which logs `RECOVERY_SUCCEEDED` — only now, with actual evidence.

That last step is the detail most people would skip, and it's the thing worth highlighting: **the system doesn't trust its own repair action — it verifies it.**

---

## 4. The parts most likely to get cross-examined

### "Why threads, not multiprocessing or asyncio?"
Tasks here are I/O-bound-style (they sleep, they don't crunch numbers), so Python's GIL isn't a real bottleneck — threads are the simplest tool that correctly models "independent things happening concurrently with real wall-clock timing." Multiprocessing would add IPC complexity for no benefit at this scale; asyncio would require every "task" to cooperatively yield, which is actually a *worse* model of a firmware task hang (a real hang blocks the whole event loop in asyncio, which isn't the failure mode you're trying to demonstrate).

### "How do you know your Registry doesn't have a race condition?"
Every access — `heartbeat()`, `get()`, `all()`, `seconds_since_heartbeat()` — takes the same `threading.Lock()` before touching `self._state`. There's a dedicated concurrency test (`test_registry_concurrency.py`) that exercises this under real concurrent writes. The lock scope is intentionally tiny (just the dict mutation), so it's not a throughput bottleneck.

### "What stops two recoveries from happening at once for the same task?"
`RecoveryManager._in_progress` — a set guarded by an `RLock` (re-entrant, since `recover()` calls back into itself indirectly through locked helper methods). If a task is already in `_in_progress`, a second `recover()` call is a no-op. This matters because the Watchdog could theoretically see STALLED on two consecutive polls before the RECOVERING state has propagated.

### "Your watchdog's HEALTHY/LATE/STALLED boundary math looks a bit ad hoc — walk me through it."
Be honest here — this is the one place in the codebase that's more heuristic than the SRS's original clean definition. The formula is:
```python
late_threshold = max(period_seconds * 1.5, timeout_seconds * 0.75)
```
The intent: a task should tolerate some scheduling jitter (hence `period * 1.5`) but never wait past the timeout regardless of period (hence the `timeout * 0.75` floor as a second candidate, take whichever is larger... actually whichever the max gives). If asked "how would you improve this," the honest answer is: define STALLED purely in terms of consecutive missed heartbeat cycles (`age // period >= missed_heartbeat_threshold`), which maps more directly to the SRS language and is easier to explain from first principles. Knowing this trade-off and being able to articulate a cleaner alternative is a good sign to an interviewer — better than pretending the code is perfect.

### "How does the dashboard avoid restarting the whole simulation every time you click a button?"
Streamlit reruns the entire script top-to-bottom on every interaction. The fix is storing the live runtime objects (`Registry`, `Watchdog`, `TaskManager`, etc.) in `st.session_state`, and only calling `start_runtime()` if `"runtime" not in st.session_state`. This was actually the single riskiest integration point going in (per the architecture doc), and it's solved correctly here.

### "What happens if you inject a fault into a task that doesn't exist, or inject two faults into the same task?"
Both are handled explicitly, not by accident: `inject_fault()` checks `task_id not in self.task_ids` first (logs `unknown_task_ignored`, returns `False`); and inside the lock, if a fault already exists for that task, it logs `double_injection_ignored` and returns `False` rather than overwriting the existing fault or raising.

### "Why JSON Lines instead of SQLite for persistence?"
Simplicity proportional to the problem — this is a single-process, single-user tool, so an append-only `events.jsonl` (one JSON object per line) gives durability and human-readability without adding a database dependency. If this needed to support queries like "show me all stalls for task-C in the last hour," SQLite would earn its place — but for "replay the event history on dashboard restart," a flat file is the right amount of engineering.

---

## 5. Questions to expect, organized by category

**Concurrency & correctness**
- Where exactly is your shared mutable state, and how is it protected?
- How would you test for a race condition you *don't* already know about?
- What would happen if the Watchdog's poll interval were longer than a task's timeout? *(Answer: detection would systematically lag — this is exactly the SRS's BR-3 rule: watchdog poll interval must be strictly shorter than the shortest task's timeout.)*

**System design / trade-offs**
- Why not just have tasks report their own status instead of a separate Watchdog polling? *(Because a hung task can't be trusted to accurately report itself — that's the whole point of an external supervisor, mirroring why real watchdog timers are hardware-independent of the CPU they're watching.)*
- What's the latency between a real stall and detection? Can you derive it? *(`poll_interval + threshold × period`, roughly — walk through why.)*
- How would this scale to 100 tasks? *(Honestly: it wouldn't gracefully — in-process threading has overhead per thread; you'd want a real scheduler/event-loop model or move tasks to separate processes/workers for real isolation. Say this proactively — it shows you understand the boundary of your own design rather than overclaiming.)*

**Debugging / "tell me about a challenge"**
- Good real answer: the Streamlit rerun-vs-persistent-state problem (§4 above) — genuine, specific, and shows you understood *why* the naive approach breaks, not just that you found a workaround.
- Alternative real answer: getting the "recovery is only confirmed by a fresh heartbeat, not just by successfully restarting the thread" logic right — explain why the naive version (mark recovered as soon as `restart_task()` returns) is a false positive: the thread could restart and still fail immediately.

**Testing**
- What does your test suite actually cover? *(Task heartbeat generation, Registry concurrency, config validation edge cases, Watchdog classification/stall detection, fault injection including duplicate/unknown-task cases, full restart+recovery-confirmation flow, event ordering/persistence.)*
- Why do you have a separate soak test instead of just unit tests? *(Unit tests prove individual mechanisms work in isolation over seconds; the soak test proves the *system* holds up under repeated fault/recovery cycles over minutes, which is what actually matters for a "reliability" claim.)*

**Real-world mapping** (know this table cold — it's what turns this from "a Python threading exercise" into "embedded systems understanding")

| This project | Real embedded equivalent |
|---|---|
| Task thread | RTOS task |
| Heartbeat write | Watchdog timer "kick" |
| Watchdog poll + timeout | Hardware/software Watchdog Timer (WDT) expiring |
| Hang fault | Deadlock / infinite loop / blocked I/O in firmware |
| Recovery Manager restart | WDT-triggered MCU reset or RTOS task supervisor restart |
| Event log | Fault log in non-volatile memory for post-mortem debugging |

**Extension questions** (have 2–3 ready)
- "What would you build next?" → Good answers, in order of how well they build on what exists: (1) tighten the LATE/STALLED classification to the cleaner missed-heartbeat-count formula, (2) a max-recovery-attempts limit that marks a task `FAILED_PERMANENTLY` instead of retrying forever (mirrors real watchdog "give up and alert" behavior — you already scoped this in your SRS as FR-21), (3) a real RTOS port (e.g., FreeRTOS on an actual MCU) as a "Phase 2" to prove the pattern translates to real hardware.

---

## 6. Weaknesses to own, not hide

Interviewers trust people more when they can name the rough edges themselves:
- The HEALTHY/LATE/STALLED boundary formula (§4) is heuristic, not derived cleanly from the spec.
- No `FAILED_PERMANENTLY` state yet — a task that keeps failing will be retried forever (FR-21 in your own SRS was explicitly scoped as a stretch goal, not done).
- Single-process only — no real isolation between "tasks," so a truly catastrophic bug in one task's `work_fn` could theoretically affect the process (mitigated by the `try/except` around `work_fn`, but worth naming as a boundary).
- No authentication/network exposure hardening — fine for a local demo tool, explicitly out of scope, and you should say *why* it's fine rather than pretend it's not a gap.

---

## 7. Two-minute demo script (practice saying this while clicking)

1. "Here's the dashboard — five tasks, all healthy, heartbeats updating live."
2. "I'll inject a hang fault on task-C." *(click)*
3. "Watch the status — LATE, then STALLED once it crosses the missed-heartbeat threshold." *(point at event log)*
4. "The watchdog fires a restart through the RecoveryManager — you can see RECOVERY_ATTEMPTED, then RECOVERY_STARTED in the log."
5. "It won't say RECOVERY_SUCCEEDED until the restarted task actually proves it's alive with a new heartbeat — there it is, and the status flips back to healthy."
6. "Every one of these transitions is covered by an automated test, and there's a soak test that repeats this cycle for ten minutes to confirm it doesn't degrade over time."