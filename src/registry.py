import threading
import time

class Registry:
    """Thread-safe registry storing last heartbeat timestamp per task_id.

    Helpers:
      - heartbeat(task_id): record now for task_id
      - get(task_id): return raw timestamp or None
      - all(): return shallow copy of raw timestamps
      - seconds_since_heartbeat(task_id): return seconds since last heartbeat or None

    task_id       last heartbeat
    --------------------------------
    sensor        10:31:04.231
    control       10:31:04.450
    network       10:31:03.981
    """
    def __init__(self):
        self._lock = threading.Lock()#just in case two Tasks send heartbeats at almost exactly the same time
        self._state = {}

    def heartbeat(self, task_id):
        """Record a heartbeat timestamp for task_id."""
        with self._lock:
            self._state[task_id] = time.time()

    def get(self, task_id):
        """Return last heartbeat timestamp for task_id or None."""
        with self._lock:
            return self._state.get(task_id)

    def all(self):
        """Return a shallow copy of the registry state."""
        with self._lock:
            return dict(self._state)

    def seconds_since_heartbeat(self, task_id):
        """Return seconds elapsed since last heartbeat for task_id, or None if no heartbeat."""
        with self._lock:
            ts = self._state.get(task_id)
        if ts is None:
            return None
        return time.time() - ts
