import time

from src.registry import Registry
from src.watchdog import Watchdog


def _make_watchdog(task_id="task-a", period=0.25, timeout_ms=800, threshold=2):
    registry = Registry()
    registry.heartbeat(task_id)
    config = {
        task_id: {
            "id": task_id,
            "period": period,
            "timeout_ms": timeout_ms,
            "missed_heartbeat_threshold": threshold,
        }
    }
    watchdog = Watchdog(registry, config, poll_interval=0.05, jitter_buffer=0.1)
    return registry, watchdog


def test_watchdog_marks_stalled_after_timeout():
    registry, watchdog = _make_watchdog(period=0.2, timeout_ms=700, threshold=2)
    watchdog.start()

    deadline = time.time() + 3.5
    while time.time() < deadline:
        if watchdog.status("task-a") == "STALLED":
            break
        time.sleep(0.05)

    assert watchdog.status("task-a") == "STALLED", "watchdog should classify stale task as STALLED"
    assert watchdog.stalled_events(), "watchdog should log STALLED transition"

    watchdog.stop()


def test_watchdog_reports_latent_stale_state_before_stall():
    registry, watchdog = _make_watchdog(period=0.2, timeout_ms=900, threshold=2)
    watchdog.start()

    deadline = time.time() + 1.5
    while time.time() < deadline:
        status = watchdog.status("task-a")
        if status in {"LATE", "STALLED"}:
            assert status in {"LATE", "STALLED"}
            break
        time.sleep(0.05)

    # it should be late or stalled at some point before the task is revived; this
    # ensures the watchdog is actually evaluating stale heartbeats instead of staying healthy.
    assert watchdog.status("task-a") in {"LATE", "STALLED"}
    watchdog.stop()
