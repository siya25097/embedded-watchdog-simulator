import threading
from src.registry import Registry


def test_registry_handles_concurrent_heartbeats():
    registry = Registry()

    task_ids = [f"task-{i}" for i in range(20)]

    def send_heartbeat(task_id):
        for _ in range(100):
            registry.heartbeat(task_id)

    threads = [
        threading.Thread(target=send_heartbeat, args=(task_id,))
        for task_id in task_ids
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    state = registry.all()

    # Every task should have a heartbeat recorded.
    assert set(state.keys()) == set(task_ids)

    # Every heartbeat should have a valid timestamp.
    for task_id in task_ids:
        assert state[task_id] is not None