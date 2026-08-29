import threading
import time

class Task(threading.Thread):
    """A simple periodic task that emits a heartbeat to a Registry each period.

    This is intentionally minimal for Milestone 1.
    """
    def __init__(self, task_id, period, registry, work_fn=None):
        super().__init__(daemon=True)
        self.task_id = task_id
        self.period = float(period)
        self.registry = registry
        self.work_fn = work_fn
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        #Keep running while the stop signal has NOT been set.
        while not self._stop.is_set():
            try:
                if self.work_fn:
                    self.work_fn(self.task_id)
            except Exception:
                # Keep task alive even if work_fn fails in the demo
                pass
            # emit heartbeat
            self.registry.heartbeat(self.task_id)
            print(f"[{self.task_id}] heartbeat at {time.time():.3f}")
            # sleep in small increments to be responsive to stop()
            remaining = self.period
            while remaining > 0 and not self._stop.is_set():
                sleep_chunk = min(0.1, remaining)
                time.sleep(sleep_chunk)
                remaining -= sleep_chunk
