import time
from src.registry import Registry
from src.task import Task


def test_task_stops_sending_heartbeats():
    registry = Registry()

    task = Task("task-stop", 0.2, registry)

    task.start()

    # Allow the task to produce at least one heartbeat.
    time.sleep(0.3)

    first_timestamp = registry.get("task-stop")

    assert first_timestamp is not None

    # Stop the task.
    task.stop()

    # Give the thread enough time to finish.
    time.sleep(0.4)

    second_timestamp = registry.get("task-stop")

    # The heartbeat timestamp should not have changed after stopping.
    assert second_timestamp == first_timestamp