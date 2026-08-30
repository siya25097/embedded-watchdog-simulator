#!/usr/bin/env python3
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.registry import Registry
from src.task import Task
from src.watchdog import Watchdog


def load_tasks(path="config/tasks.yaml"):
    import yaml
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get("tasks", [])


def main():
    tasks_cfg = load_tasks()
    registry = Registry()
    watchdog = Watchdog(registry, tasks_cfg, poll_interval=0.2, jitter_buffer=0.1)

    active_tasks = []
    for task_cfg in tasks_cfg:
        task = Task(task_cfg["id"], task_cfg["period"], registry)
        task.start()
        active_tasks.append(task)

    watchdog.start()
    print("Started watchdog and tasks. Press Ctrl+C to stop.")

    def shutdown(sig, frame):
        print("\nStopping tasks...")
        watchdog.stop()
        for task in active_tasks:
            task.stop()
        time.sleep(0.2)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)

    try:
        while True:
            snapshot = watchdog.statuses()
            if snapshot:
                print("STATUS:", snapshot)
            time.sleep(1.0)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
