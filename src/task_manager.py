import threading

from src.task import Task


class TaskManager:
    """Own the lifecycle of configured task threads."""

    def __init__(self, registry, tasks_config, fault_injector=None, event_logger=None):
        self.registry = registry
        self.fault_injector = fault_injector
        self.event_logger = event_logger
        self._configs = self._normalize(tasks_config)
        self._tasks = {}
        self._lock = threading.RLock()

        if self.fault_injector:
            self.fault_injector.register_tasks(self._configs)

    @staticmethod
    def _normalize(tasks_config):
        if isinstance(tasks_config, dict):
            return {
                str(task_id): dict(config)
                for task_id, config in tasks_config.items()
                if isinstance(config, dict)
            }
        return {
            str(config["id"]): dict(config)
            for config in tasks_config
            if isinstance(config, dict) and "id" in config
        }

    def task_ids(self):
        with self._lock:
            return list(self._configs)

    def start_task(self, task_id):
        with self._lock:
            if task_id not in self._configs:
                raise KeyError(f"Unknown task: {task_id}")
            current = self._tasks.get(task_id)
            if current is not None and current.is_alive():
                return current

            config = self._configs[task_id]
            task = Task(
                task_id,
                config["period"],
                self.registry,
                fault_injector=self.fault_injector,
                event_logger=self.event_logger,
            )
            task.start()
            self._tasks[task_id] = task
            return task

    def start_all(self):
        return [self.start_task(task_id) for task_id in self.task_ids()]

    def stop_task(self, task_id):
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.stop()
        task.join(timeout=2)
        if task.is_alive():
            raise RuntimeError(f"Task '{task_id}' did not stop within timeout")
        return True

    def stop_all(self):
        for task_id in self.task_ids():
            self.stop_task(task_id)

    def restart_task(self, task_id):
        self.stop_task(task_id)
        return self.start_task(task_id)

    def get_task(self, task_id):
        with self._lock:
            return self._tasks.get(task_id)
