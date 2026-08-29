import time
from src.registry import Registry
from src.task import Task


def test_three_tasks_heartbeat():
    reg = Registry()
    tasks = [Task(f"t{i}", 0.2, reg) for i in range(3)]
    for t in tasks:
        t.start()
    # allow several heartbeat cycles
    time.sleep(0.8)

    now = time.time()
    for i in range(3):
        ts = reg.get(f"t{i}")
        assert ts is not None, f"No heartbeat recorded for t{i}"
        # heartbeat should be recent (less than 1s ago)
        assert now - ts < 1.0, f"Heartbeat for t{i} too old: {now - ts}s"

    for t in tasks:
        t.stop()
