import time

from src.fault_injector import FaultInjector
from src.recovery import RecoveryManager
from src.registry import Registry
from src.task_manager import TaskManager
from src.watchdog import Watchdog


def wait_for(predicate, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def test_stalled_task_is_restarted_and_recovery_requires_fresh_heartbeat():
    registry = Registry()
    injector = FaultInjector(["task-a"])
    config = {
        "task-a": {
            "period": 0.05,
            "timeout_ms": 180,
            "missed_heartbeat_threshold": 2,
        }
    }
    manager = TaskManager(registry, config, injector)
    manager.start_all()
    recovery = RecoveryManager(manager, injector)
    watchdog = Watchdog(
        registry,
        config,
        poll_interval=0.02,
        jitter_buffer=0.01,
        on_stalled=recovery.recover,
        on_healthy=recovery.confirm_recovery,
    )
    watchdog.start()
    try:
        assert wait_for(lambda: registry.get("task-a") is not None)
        assert injector.inject_hang("task-a") is True
        assert wait_for(lambda: watchdog.status("task-a") == "RECOVERING")
        assert any(
            event["event"] == "RECOVERY_ATTEMPTED"
            for event in recovery.recovery_events()
        )
        assert wait_for(
            lambda: watchdog.status("task-a") == "HEALTHY"
            and any(
                event["event"] == "RECOVERY_SUCCEEDED"
                for event in recovery.recovery_events()
            )
        )
        assert recovery.recovery_count("task-a") == 1
    finally:
        watchdog.stop()
        manager.stop_all()
        watchdog.join(timeout=1)


def test_recovery_success_requires_an_active_confirmation():
    registry = Registry()
    manager = TaskManager(
        registry,
        {"task-a": {"period": 0.05, "timeout_ms": 180, "missed_heartbeat_threshold": 2}},
    )
    recovery = RecoveryManager(manager)

    assert recovery.confirm_recovery("task-a") is False


def test_confirm_recovery_records_success_without_deadlocking():
    registry = Registry()
    manager = TaskManager(
        registry,
        {"task-a": {"period": 0.05, "timeout_ms": 180, "missed_heartbeat_threshold": 2}},
    )
    recovery = RecoveryManager(manager)

    with recovery._lock:
        recovery._counts["task-a"] = 1
        recovery._awaiting_confirmation.add("task-a")

    assert recovery.confirm_recovery("task-a") is True
    assert any(
        event["event"] == "RECOVERY_SUCCEEDED"
        for event in recovery.recovery_events()
    )
