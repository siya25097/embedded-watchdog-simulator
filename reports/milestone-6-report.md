# Milestone 6 — Streamlit Dashboard

Date: 2026-09-04

## Goal

Provide a single-screen operator dashboard that shows live task health, allows fault injection, and exposes the chronological event history from the existing simulator components.

## Implementation

- [dashboard/app.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/dashboard/app.py)
  - Starts the configured tasks, watchdog, fault injector, recovery manager, and event logger once in Streamlit session state.
  - Reuses the validated YAML loader from `scripts/run_tasks.py`.
  - Refreshes automatically every 250 ms, making short `LATE` windows easier to observe.
  - Displays a task status grid with accessible text labels and status icons.
  - Shows last-heartbeat age and per-task recovery count.
  - Provides task and fault-type selectors.
  - Disables duplicate fault injection and enables clearing active faults.
  - Displays a reverse-chronological event table.
  - Shows clear startup errors and an empty-event-log message.

## Run the dashboard

From the repository root:

```bash
PYTHONPATH=. python3 -m streamlit run dashboard/app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

Demo flow:

1. Wait for all tasks to display `HEALTHY`.
2. Select a task and choose `Hang`.
3. Click `Inject Fault`.
4. Observe `LATE`, `STALLED`, `RECOVERING`, then `HEALTHY`.
5. Review the event log and recovery count.

## Validation

Automated suite:

```bash
PYTHONPATH=. python3 -m pytest -q
```

Result:

```text
20 passed in 4.32s
```

Dashboard module compilation:

```bash
python3 -m py_compile dashboard/app.py
```

Streamlit startup smoke test also returned a successful HTTP response from the local server.

## Limitations

- The dashboard runtime is stored per Streamlit session, so it is intended for one local operator.
- Event persistence is not implemented; the event history is in memory.
- A dedicated reset button and timeline chart remain future improvements.
