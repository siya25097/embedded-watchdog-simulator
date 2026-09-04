from src.fault_injector import FaultInjector


def test_inject_hang_fault():
    injector = FaultInjector(["task-a", "task-b"])
    ok = injector.inject_hang("task-a")

    assert ok is True
    assert injector.has_fault("task-a") is True
    assert injector.get_fault("task-a")["fault_type"] == "hang"


def test_inject_comm_failure_fault():
    injector = FaultInjector(["task-a"]) 
    ok = injector.inject_comm_failure("task-a")

    assert ok is True
    assert injector.has_fault("task-a") is True
    assert injector.get_fault("task-a")["fault_type"] == "comm_failure"


def test_double_injection_is_ignored():
    injector = FaultInjector(["task-a"])
    first = injector.inject_hang("task-a")
    second = injector.inject_hang("task-a")

    assert first is True
    assert second is False
    assert len(injector.get_faults()) == 1
    assert injector.get_fault("task-a")["fault_type"] == "hang"


def test_clear_fault_removes_entry():
    injector = FaultInjector(["task-a"])
    injector.inject_hang("task-a")
    cleared = injector.clear_fault("task-a")

    assert cleared is True
    assert injector.has_fault("task-a") is False


def test_unknown_task_is_ignored():
    injector = FaultInjector(["task-a"])

    assert injector.inject_hang("missing-task") is False
    assert injector.has_fault("missing-task") is False
    assert injector.events[-1]["action"] == "unknown_task_ignored"
