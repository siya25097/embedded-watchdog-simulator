import logging
import threading
import time


class EventLogger:
    """Thread-safe in-memory event history with optional stdlib logging."""

    def __init__(self, logger=None):
        self._lock = threading.Lock()
        self._events = []
        self._logger = logger or logging.getLogger("watchdog_simulator")

    def log(self, event_type, task_id=None, details=None, timestamp=None):
        event = {
            "timestamp": time.time() if timestamp is None else timestamp,
            "event_type": event_type,
            "task_id": task_id,
            "details": details,
        }
        with self._lock:
            self._events.append(event)
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
