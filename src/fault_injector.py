import threading
import time


class FaultInjector:
    """Record and manage injected faults for simulated tasks.

    Supported fault types:
      - "hang": task stops emitting heartbeats
      - "comm_failure": task has a communication failure / heartbeat drop
    """

    VALID_FAULTS = {"hang", "comm_failure"}

    def __init__(self, task_ids=None):
        self._lock = threading.Lock()
        self.task_ids = set(task_ids or [])
        self.faults = {}
        self.events = []

    def register_task(self, task_id):
        self.task_ids.add(task_id)

    def register_tasks(self, task_ids):
        for task_id in task_ids:
            self.register_task(task_id)

    def _log(self, task_id, fault_type, action):
        event = {
            "timestamp": time.time(),
            "task_id": task_id,
            "fault_type": fault_type,
            "action": action,
        }
        with self._lock:
            self.events.append(event)
        print(f"[FAULT_INJECTOR] {action} task={task_id} fault={fault_type} at {event['timestamp']:.3f}")
        return event

    def inject_fault(self, task_id, fault_type):
        if fault_type not in self.VALID_FAULTS:
            raise ValueError(f"Unsupported fault type: {fault_type}")
        if task_id not in self.task_ids:
            self._log(task_id, fault_type, "unknown_task_ignored")
            return False

        with self._lock:
            existing = self.faults.get(task_id)
            if existing is None:
                self.faults[task_id] = {
                    "fault_type": fault_type,
                    "injected_at": time.time(),
                }
        if existing is not None:
            self._log(task_id, fault_type, "double_injection_ignored")
            return False

        self._log(task_id, fault_type, "fault_injected")
        return True

    def inject_hang(self, task_id):
        return self.inject_fault(task_id, "hang")

    def inject_comm_failure(self, task_id):
        return self.inject_fault(task_id, "comm_failure")

    def clear_fault(self, task_id):
        with self._lock:
            fault = self.faults.pop(task_id, None)
        if fault is None:
            return False
        fault_type = fault["fault_type"]
        self._log(task_id, fault_type, "fault_cleared")
        return True

    def has_fault(self, task_id):
        with self._lock:
            return task_id in self.faults

    def get_fault(self, task_id):
        with self._lock:
            fault = self.faults.get(task_id)
            return dict(fault) if fault else None

    def get_faults(self):
        with self._lock:
            return {task_id: dict(fault) for task_id, fault in self.faults.items()}
