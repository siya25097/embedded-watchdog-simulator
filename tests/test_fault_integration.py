import time

from src.fault_injector import FaultInjector
from src.registry import Registry
from src.task import Task
from src.watchdog import Watchdog


def wait_for(predicate, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def test_hang_fault_stops_heartbeats_and_watchdog_detects_stall():
    registry = Registry()
    injector = FaultInjector(["task-a"])
    task = Task("task-a", 0.05, registry, fault_injector=injector)
    watchdog = Watchdog(
        registry,
        {"task-a": {"period": 0.05, "timeout_ms": 180, "missed_heartbeat_threshold": 2}},
        poll_interval=0.02,
        jitter_buffer=0.01,
    )
    task.start()
    watchdog.start()
    try:
        assert wait_for(lambda: registry.get("task-a") is not None)
        assert injector.inject_hang("task-a") is True
        previous = registry.get("task-a")
        assert wait_for(lambda: watchdog.status("task-a") == "STALLED")
        assert registry.get("task-a") == previous
    finally:
        injector.clear_fault("task-a")
        task.stop()
        watchdog.stop()
        task.join(timeout=1)
        watchdog.join(timeout=1)


def test_comm_failure_drops_heartbeats_until_cleared():
    registry = Registry()
    injector = FaultInjector(["task-a"])
    task = Task("task-a", 0.05, registry, fault_injector=injector)
    task.start()
    try:
        assert wait_for(lambda: registry.get("task-a") is not None)
        assert injector.inject_comm_failure("task-a") is True
        previous = registry.get("task-a")
        time.sleep(0.15)
        assert registry.get("task-a") == previous
        assert injector.clear_fault("task-a") is True
        assert wait_for(lambda: registry.get("task-a") > previous)
    finally:
        task.stop()
        task.join(timeout=1)
