import threading
import time


class RecoveryManager:
    """Restart stalled tasks and track recovery lifecycle events."""

    def __init__(self, task_manager, fault_injector=None, watchdog=None, event_logger=None):
        self.task_manager = task_manager
        self.fault_injector = fault_injector
        self.watchdog = watchdog
        self.event_logger = event_logger
        self._lock = threading.Lock()
        self._counts = {}
        self._last_recovery = {}
        self.events = []
        self._in_progress = set()
        self._awaiting_confirmation = set()

    def recovery_count(self, task_id):
        with self._lock:
            return self._counts.get(task_id, 0)

    def last_recovery(self, task_id):
        with self._lock:
            return self._last_recovery.get(task_id)

    def recovery_events(self):
        with self._lock:
            return list(self.events)

    def confirm_recovery(self, task_id):
        with self._lock:
            if task_id not in self._awaiting_confirmation:
                return False
            self._awaiting_confirmation.remove(task_id)
            self.events.append({
                "timestamp": time.time(),
                "task_id": task_id,
                "event": "RECOVERY_SUCCEEDED",
            })
            if self.event_logger:
                self.event_logger.log("RECOVERY_SUCCEEDED", task_id)
            return True

    def recover(self, task_id):
        with self._lock:
            if task_id in self._in_progress:
                return False
            self._in_progress.add(task_id)
            timestamp = time.time()
            self._counts[task_id] = self._counts.get(task_id, 0) + 1
            self._last_recovery[task_id] = timestamp
            self.events.append({
                "timestamp": timestamp,
                "task_id": task_id,
                "event": "RECOVERY_ATTEMPTED",
            })
            if self.event_logger:
                self.event_logger.log("RECOVERY_ATTEMPTED", task_id, timestamp=timestamp)

        try:
            if self.fault_injector:
                self.fault_injector.clear_fault(task_id)
            self.task_manager.restart_task(task_id)
            with self._lock:
                self._awaiting_confirmation.add(task_id)
                self.events.append({
                    "timestamp": time.time(),
                    "task_id": task_id,
                    "event": "RECOVERY_STARTED",
                })
                if self.event_logger:
                    self.event_logger.log("RECOVERY_STARTED", task_id)
            return True
        except Exception as exc:
            with self._lock:
                self.events.append({
                    "timestamp": time.time(),
                    "task_id": task_id,
                    "event": "RECOVERY_FAILED",
                    "details": str(exc),
                })
                if self.event_logger:
                    self.event_logger.log("RECOVERY_FAILED", task_id, str(exc))
            return False
        finally:
            with self._lock:
                self._in_progress.discard(task_id)
