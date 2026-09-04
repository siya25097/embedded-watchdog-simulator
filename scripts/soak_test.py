#!/usr/bin/env python3
"""Run repeated fault/recovery cycles to validate long-running stability."""

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_tasks import load_tasks
from src.event_logger import EventLogger
from src.fault_injector import FaultInjector
from src.recovery import RecoveryManager
from src.registry import Registry
from src.task_manager import TaskManager
from src.watchdog import Watchdog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=600, help="duration in seconds")
    parser.add_argument("--fault-interval", type=float, default=5, help="seconds between fault injections")
    args = parser.parse_args()

    tasks_config = load_tasks(str(ROOT / "config" / "tasks.yaml"))["tasks"]
    task_map = {task["id"]: task for task in tasks_config}
    logger = EventLogger(logging.getLogger("watchdog_soak"))
    registry = Registry()
    injector = FaultInjector(task_map, event_logger=logger)
    manager = TaskManager(registry, task_map, injector, event_logger=logger)
    recovery = RecoveryManager(manager, injector, event_logger=logger)
    watchdog = Watchdog(
        registry,
        task_map,
        poll_interval=0.1,
        on_stalled=recovery.recover,
        on_healthy=recovery.confirm_recovery,
        event_logger=logger,
    )

    manager.start_all()
    watchdog.start()
    task_ids = list(task_map)
    start = time.monotonic()
    injections = 0
    try:
        while time.monotonic() - start < args.duration:
            task_id = task_ids[injections % len(task_ids)]
            if injector.inject_hang(task_id):
                injections += 1
            time.sleep(args.fault_interval)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and any(
            watchdog.status(task_id) != "HEALTHY" for task_id in task_ids
        ):
            time.sleep(0.1)
        if any(watchdog.status(task_id) != "HEALTHY" for task_id in task_ids):
            raise RuntimeError(f"tasks did not return healthy: {watchdog.statuses()}")
        print(
            f"Soak passed: {args.duration:.0f}s, "
            f"{injections} injections, "
            f"{len(logger.events())} events"
        )
    finally:
        watchdog.stop()
        manager.stop_all()
        watchdog.join(timeout=2)


if __name__ == "__main__":
    main()
