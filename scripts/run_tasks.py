#!/usr/bin/env python3
import yaml
import time
import signal
import sys
from src.registry import Registry
from src.task import Task


def load_tasks(path="config/tasks.yaml"):
    """Load and validate tasks config.

    Ensures each task has: id (str), period (float>0), timeout_ms (int),
    missed_heartbeat_threshold (int). If timeout_ms or missed_heartbeat_threshold
    are missing they are defaulted:
      - timeout_ms default: int(period * 2000)  # 2 x period in ms
      - missed_heartbeat_threshold default: 2
    """
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}

    raw_tasks = cfg.get("tasks", [])
    validated = []
    for idx, t in enumerate(raw_tasks):
        if not isinstance(t, dict):
            raise ValueError(f"task entry at index {idx} must be a mapping")
        if "id" not in t:
            raise ValueError(f"task entry at index {idx} missing 'id'")
        if "period" not in t:
            raise ValueError(f"task '{t.get('id')}' missing 'period'")
        try:
            period = float(t["period"])
            if period <= 0:
                raise ValueError()
        except Exception:
            raise ValueError(f"task '{t.get('id')}' has invalid 'period' value: {t.get('period')}")

        timeout_ms = t.get("timeout_ms")
        if timeout_ms is None:
            timeout_ms = int(period * 2000)
        else:
            try:
                timeout_ms = int(timeout_ms)
                if timeout_ms <= 0:
                    raise ValueError()
            except Exception:
                raise ValueError(f"task '{t.get('id')}' has invalid 'timeout_ms': {t.get('timeout_ms')}")

        # SRS V-1: reject configurations where timeout <= period (in ms)
        if timeout_ms <= int(period * 1000):
            raise ValueError(f"task '{t.get('id')}' invalid: timeout_ms ({timeout_ms}) must be greater than period*1000 ({int(period*1000)})")

        missed = t.get("missed_heartbeat_threshold")
        if missed is None:
            missed = 2
        else:
            try:
                missed = int(missed)
                if missed < 0:
                    raise ValueError()
            except Exception:
                raise ValueError(f"task '{t.get('id')}' has invalid 'missed_heartbeat_threshold': {t.get('missed_heartbeat_threshold')}")

        validated.append({
            "id": t["id"],
            "period": period,
            "timeout_ms": timeout_ms,
            "missed_heartbeat_threshold": missed,
        })

    return {"tasks": validated}


def main():
    cfg = load_tasks()
    reg = Registry()
    tasks = []
    for t in cfg.get("tasks", []):
        task = Task(t["id"], t["period"], reg)
        task.start()
        tasks.append(task)
        print(f"Started {t['id']} (period={t['period']})")

    def handle(sig, frame):
        print("Shutting down tasks...")
        for tt in tasks:
            tt.stop()
        time.sleep(0.2)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle(None, None)


if __name__ == "__main__":
    main()
