# Milestone 7 — Testing, Polish & Bug Fixing

Date: 2026-09-04

## Current status

Milestone 7 validation and targeted polish are complete. The automated regression suite is passing, SRS validation gaps were corrected, and the required 10-minute repeated fault/recovery soak test completed successfully.

## Completed work

- Added duplicate task ID rejection for SRS V-2.
- Corrected `missed_heartbeat_threshold` validation to require a positive integer (`>= 1`) for SRS V-4.
- Improved demo shutdown by joining task threads after requesting stop.
- Preserved thread-safe Registry, watchdog, fault-injector, recovery, and event-logger access.
- Added regression coverage in [tests/test_config_validation.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/tests/test_config_validation.py).
- Added [scripts/soak_test.py](/Users/khushi_makwana/VSCode/EMBEDDED_PROJECT/scripts/soak_test.py) for repeated fault/recovery validation.

## Automated validation

Run from the repository root:

```bash
cd /Users/khushi_makwana/VSCode/EMBEDDED_PROJECT
PYTHONPATH=. python3 -m pytest -q
```

Current result:

```text
22 passed in 3.94s
```

## Manual acceptance commands

Validate package imports:

```bash
PYTHONPATH=. python3 -c "import src; print('src import OK')"
```

Run the live task/watchdog demo:

```bash
PYTHONPATH=. python3 scripts/watchdog_demo.py
```

Run the Streamlit dashboard:

```bash
PYTHONPATH=. python3 -m streamlit run dashboard/app.py
```

In the dashboard, wait for `HEALTHY`, inject a `Hang` fault, and observe:

```text
HEALTHY → LATE → STALLED → RECOVERING → HEALTHY
```

## Soak test command

Run the required ten-minute repeated fault/recovery test:

```bash
PYTHONPATH=. python3 scripts/soak_test.py --duration 600 --fault-interval 5
```

The command should finish with `Soak passed`, report multiple injections and events, and leave all tasks healthy before shutdown.

## Soak test result

```text
Soak passed: 600s, 120 injections, 1796 events
```

The process exited successfully, and all tasks returned to `HEALTHY` before shutdown.

## Acceptance checklist result

- 3 concurrent periodic tasks: passed.
- Watchdog stalled detection: passed.
- Hang and communication-failure injection: passed.
- Automatic restart and recovery count: passed.
- Live dashboard status and event history: passed by module, HTTP startup, and existing tests.
- 10-minute continuous repeated-fault soak: passed.
