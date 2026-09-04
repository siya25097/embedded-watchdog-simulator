import logging
import sys
import time
from pathlib import Path

import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.event_logger import EventLogger
from src.fault_injector import FaultInjector
from src.recovery import RecoveryManager
from src.registry import Registry
from src.task_manager import TaskManager
from src.watchdog import Watchdog
from scripts.run_tasks import load_tasks as load_validated_tasks


STATUS_ICONS = {
    "HEALTHY": "🟢",
    "LATE": "🟡",
    "STALLED": "🔴",
    "RECOVERING": "🔵",
    "INITIALIZING": "⚪",
    "FAILED_PERMANENTLY": "⚫",
}


def load_tasks():
    return load_validated_tasks(str(ROOT / "config" / "tasks.yaml"))["tasks"]


def start_runtime():
    tasks_config = load_tasks()
    task_map = {task["id"]: task for task in tasks_config}
    event_logger = EventLogger(logging.getLogger("watchdog_dashboard"))
    registry = Registry()
    fault_injector = FaultInjector(task_map, event_logger=event_logger)
    task_manager = TaskManager(
        registry,
        task_map,
        fault_injector=fault_injector,
        event_logger=event_logger,
    )
    recovery = RecoveryManager(
        task_manager,
        fault_injector=fault_injector,
        event_logger=event_logger,
    )
    watchdog = Watchdog(
        registry,
        task_map,
        poll_interval=0.1,
        on_stalled=recovery.recover,
        on_healthy=recovery.confirm_recovery,
        event_logger=event_logger,
    )
    task_manager.start_all()
    watchdog.start()
    return {
        "tasks_config": task_map,
        "event_logger": event_logger,
        "registry": registry,
        "fault_injector": fault_injector,
        "task_manager": task_manager,
        "recovery": recovery,
        "watchdog": watchdog,
    }


def stop_runtime(runtime):
    runtime["watchdog"].stop()
    runtime["task_manager"].stop_all()


def render_status_grid(runtime):
    st.header("Task Status")
    statuses = runtime["watchdog"].statuses()
    task_ids = list(runtime["tasks_config"])
    columns = st.columns(max(1, len(task_ids)))
    for column, task_id in zip(columns, task_ids):
        status = statuses.get(task_id, "INITIALIZING")
        age = runtime["registry"].seconds_since_heartbeat(task_id)
        age_text = "never" if age is None else f"{age:.2f}s ago"
        with column:
            st.subheader(task_id)
            st.markdown(f"### {STATUS_ICONS.get(status, '⚪')} {status}")
            st.caption(f"Last heartbeat: {age_text}")
            st.caption(
                f"Recoveries: {runtime['recovery'].recovery_count(task_id)}"
            )


def render_controls(runtime):
    st.header("Fault Injection")
    task_ids = list(runtime["tasks_config"])
    if not task_ids:
        st.info("No tasks configured.")
        return

    task_id = st.selectbox("Task", task_ids)
    fault_type = st.radio(
        "Fault type",
        ["hang", "comm_failure"],
        format_func=lambda value: "Hang" if value == "hang" else "Comm Failure",
        horizontal=True,
    )
    active_fault = runtime["fault_injector"].has_fault(task_id)
    inject, clear = st.columns(2)
    with inject:
        if st.button("Inject Fault", disabled=active_fault, use_container_width=True):
            runtime["fault_injector"].inject_fault(task_id, fault_type)
            st.rerun()
    with clear:
        if st.button("Clear Fault", disabled=not active_fault, use_container_width=True):
            runtime["fault_injector"].clear_fault(task_id)
            st.rerun()
    if active_fault:
        st.warning(f"{task_id} has an active fault.")


def render_event_log(runtime):
    st.header("Event Log")
    events = list(reversed(runtime["event_logger"].chronological()))
    if not events:
        st.info("No events yet — inject a fault to see the watchdog in action.")
        return
    rows = [
        {
            "timestamp": time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(event["timestamp"])
            ),
            "task": event["task_id"] or "-",
            "event": event["event_type"],
            "details": str(event["details"] or ""),
        }
        for event in events
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def main():
    st.set_page_config(page_title="Embedded Watchdog Simulator", layout="wide")
    st.title("Embedded Watchdog & Fault Recovery Simulator")

    if "runtime" not in st.session_state:
        try:
            st.session_state.runtime = start_runtime()
        except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
            st.error(f"Unable to start simulator: {exc}")
            st.stop()

    runtime = st.session_state.runtime
    statuses = runtime["watchdog"].statuses()
    healthy = sum(status == "HEALTHY" for status in statuses.values())
    st.caption(
        f"{healthy}/{len(runtime['tasks_config'])} tasks healthy · "
        "updates every 250 ms"
    )

    render_status_grid(runtime)
    st.divider()
    render_controls(runtime)
    st.divider()
    render_event_log(runtime)

    time.sleep(0.25)
    st.rerun()


if __name__ == "__main__":
    main()
