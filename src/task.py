import threading
import time

class Task(threading.Thread):
    """A simple periodic task that emits a heartbeat to a Registry each period.

    This is intentionally minimal for Milestone 1.
    """
    def __init__(
        self,
        task_id,
        period,
        registry,
        work_fn=None,
        fault_injector=None,
        event_logger=None,
    ):
        super().__init__(daemon=True)
        self.task_id = task_id
        self.period = float(period)
        self.registry = registry
        self.work_fn = work_fn
        self.fault_injector = fault_injector
        self.event_logger = event_logger
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            try:
                if self.work_fn:
                    self.work_fn(self.task_id)
            except Exception:
                # Keep task alive even if work_fn fails in the demo
                pass
            fault = (
                self.fault_injector.get_fault(self.task_id)
                if self.fault_injector
                else None
            )
            if fault is None:
                self.registry.heartbeat(self.task_id)
                if self.event_logger:
                    self.event_logger.log("HEARTBEAT", self.task_id)
                print(f"[{self.task_id}] heartbeat at {time.time():.3f}")
            elif fault["fault_type"] == "hang":
                # A hung task remains alive but stops producing heartbeats.
                pass
            elif fault["fault_type"] == "comm_failure":
                # The task continues running, but heartbeat delivery is lost.
                pass
            # sleep in small increments to be responsive to stop()
            remaining = self.period
            while remaining > 0 and not self._stop_event.is_set():
                sleep_chunk = min(0.1, remaining)
                time.sleep(sleep_chunk)
                remaining -= sleep_chunk
