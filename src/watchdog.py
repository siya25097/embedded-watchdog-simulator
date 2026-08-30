import threading
import time

class Watchdog(threading.Thread):
    """Poll registry for stale heartbeats and classify task health.

    States:
      - HEALTHY: task heartbeat is within its normal period / timeout
      - LATE: heartbeat is stale but not yet beyond the stall threshold
      - STALLED: heartbeat is stale beyond timeout and missed threshold
      - RECOVERING: reserved for future recovery flow
    """

    VALID_STATES = {"HEALTHY", "LATE", "STALLED", "RECOVERING", "INITIALIZING"}

    def __init__(self, registry, tasks_config=None, poll_interval=0.25, jitter_buffer=0.1):
        super().__init__(daemon=True)
        self.registry = registry
        self.tasks_config = self._normalize_tasks(tasks_config or {})
        self.poll_interval = float(poll_interval)
        self.jitter_buffer = float(jitter_buffer)
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._statuses = {}
        self._stalled_events = []

    def _normalize_tasks(self, tasks_config):
        """Accept either a dict of id -> config or a list of task dicts."""
        if not tasks_config:
            return {}
        if isinstance(tasks_config, dict):
            normalized = {}
            for task_id, cfg in tasks_config.items():
                if isinstance(cfg, dict):
                    normalized[str(task_id)] = cfg
            return normalized
        normalized = {}
        for cfg in tasks_config:
            if isinstance(cfg, dict) and "id" in cfg:
                normalized[str(cfg["id"])] = cfg
        return normalized

    def status(self, task_id):
        with self._lock:
            return self._statuses.get(task_id, "INITIALIZING")

    def statuses(self):
        with self._lock:
            return dict(self._statuses)

    def stalled_events(self):
        with self._lock:
            return list(self._stalled_events)

    def _log_stalled_transition(self, task_id):
        event = {"task_id": task_id, "event": "STALLED", "timestamp": time.time()}
        self._stalled_events.append(event)
        print(f"[WATCHDOG] {task_id} transitioned to STALLED at {event['timestamp']:.3f}")

    def _classify(self, task_id, cfg):
        last_ts = self.registry.get(task_id) # When did task-A last send a heartbeat?
        if last_ts is None:
            return "INITIALIZING"

        age = time.time() - last_ts # How long has it been since the last heartbeat?
        period_seconds = float(cfg.get("period", 0.0) or 0.0) # How often should the task send a heartbeat?
        timeout_seconds = float(cfg.get("timeout_ms", 0) or 0) / 1000.0 # How long before we consider the task to be stalled?
        threshold = int(cfg.get("missed_heartbeat_threshold", 1) or 1) # How many missed heartbeats before we consider the task to be stalled?

        if timeout_seconds <= 0:
            return "HEALTHY"

        # A slight jitter buffer differentiates the normal schedule variance from a real stall.
        late_threshold = max(period_seconds * 1.5, timeout_seconds * 0.75)
        if age < late_threshold - self.jitter_buffer:
            return "HEALTHY"
        if age < timeout_seconds:
            return "LATE"

        # translated as: if the task has missed enough heartbeats, consider it stalled.
        missed = max(1, int(age / max(period_seconds, 0.001)))
        if missed >= threshold:
            return "STALLED"
        return "LATE"

    def _poll_once(self):
        """
        So after polling you might have:
        {
            "task-A": "HEALTHY",
            "task-B": "HEALTHY",
            "task-C": "LATE"
        }
        """
        if not self.tasks_config:
            return

        for task_id, cfg in self.tasks_config.items():
            new_state = self._classify(task_id, cfg)
            with self._lock:
                previous = self._statuses.get(task_id)
                self._statuses[task_id] = new_state
            if new_state == "STALLED" and previous != "STALLED":
                self._log_stalled_transition(task_id)

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            self._poll_once()
            time.sleep(self.poll_interval)
