import json
import logging
import threading
import time
from pathlib import Path


class EventLogger:
    """Thread-safe in-memory event history with optional stdlib logging."""

    def __init__(self, logger=None, persistence_path=None):
        self._lock = threading.Lock()
        self._events = []
        self._logger = logger or logging.getLogger("watchdog_simulator")
        self._persistence_path = (
            Path(persistence_path) if persistence_path is not None else None
        )
        if self._persistence_path is not None and self._persistence_path.exists():
            with self._persistence_path.open(encoding="utf-8") as event_file:
                self._events = [
                    json.loads(line)
                    for line in event_file
                    if line.strip()
                ]

    def log(self, event_type, task_id=None, details=None, timestamp=None):
        event = {
            "timestamp": time.time() if timestamp is None else timestamp,
            "event_type": event_type,
            "task_id": task_id,
            "details": details,
        }
        with self._lock:
            self._events.append(event)
            if self._persistence_path is not None:
                self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
                with self._persistence_path.open("a", encoding="utf-8") as event_file:
                    event_file.write(json.dumps(event) + "\n")
        self._logger.info(
            "%s task=%s details=%s",
            event_type,
            task_id if task_id is not None else "-",
            details if details is not None else "-",
        )
        return dict(event)

    def events(self):
        with self._lock:
            return [dict(event) for event in self._events]

    def chronological(self):
        return sorted(self.events(), key=lambda event: event["timestamp"])
