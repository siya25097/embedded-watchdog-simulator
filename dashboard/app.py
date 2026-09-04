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


def start_runtime(tasks_config=None):
    tasks_config = load_tasks() if tasks_config is None else tasks_config
    task_map = {task["id"]: task for task in tasks_config}
    event_logger = EventLogger(
        logging.getLogger("watchdog_dashboard"),
        persistence_path=ROOT / "events.jsonl",
    )
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
            st.session_state.dashboard_notice = (
                f"{fault_type.replace('_', ' ').title()} injected into {task_id}."
            )
            st.rerun()
    with clear:
        if st.button("Clear Fault", disabled=not active_fault, use_container_width=True):
            runtime["fault_injector"].clear_fault(task_id)
            st.session_state.dashboard_notice = f"Fault cleared for {task_id}."
            st.rerun()
    if active_fault:
        st.warning(f"{task_id} has an active fault.")


def render_timing_controls(runtime):
    st.sidebar.header("Simulation Controls")
    st.sidebar.caption("Edit timing values, then apply to restart all tasks.")
    edited = {}
    for task_id, config in runtime["tasks_config"].items():
        with st.sidebar.expander(task_id):
            period = st.number_input(
                f"{task_id} period (seconds)",
                min_value=0.1,
                value=float(config["period"]),
                step=0.1,
                key=f"period-{task_id}",
            )
            timeout = st.number_input(
                f"{task_id} timeout (ms)",
                min_value=101,
                value=max(int(config["timeout_ms"]), int(period * 1000) + 1),
                step=100,
                key=f"timeout-{task_id}",
            )
            threshold = st.number_input(
                f"{task_id} missed HB threshold",
                min_value=1,
                value=int(config["missed_heartbeat_threshold"]),
                step=1,
                key=f"threshold-{task_id}",
            )
            edited[task_id] = {
                **config,
                "period": period,
                "timeout_ms": max(int(timeout), int(period * 1000) + 1),
                "missed_heartbeat_threshold": threshold,
            }
    if st.sidebar.button("Apply timing changes", use_container_width=True):
        stop_runtime(runtime)
        st.session_state.runtime = start_runtime(list(edited.values()))
        st.session_state.dashboard_notice = (
            "Timing changes applied; all tasks were restarted."
        )
        st.rerun()


def render_event_log(runtime):
    st.header("Event Log")
    event_types = sorted(
        {event["event_type"] for event in runtime["event_logger"].events()}
    )
    selected_types = st.multiselect(
        "Show event types",
        event_types,
        default=[event_type for event_type in event_types if event_type != "HEARTBEAT"],
    )
    events = [
        event
        for event in runtime["event_logger"].chronological()
        if event["event_type"] in selected_types
    ]
    events = list(reversed(events))
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

    with st.expander("How to use this dashboard", expanded=True):
        st.markdown(
            """
            **Quick demo**
            1. Wait until the tasks show `HEALTHY`.
            2. Choose a task and fault type in **Fault Injection**.
            3. Click **Inject Fault**.
            4. Observe the task move through `LATE`, `STALLED`, `RECOVERING`,
               and back to `HEALTHY`.
            5. Review the event log and recovery count.

            **Slow-motion demo**
            - Open a task in **Simulation Controls** in the sidebar.
            - Increase its period to `3–5` seconds.
            - Set its timeout higher than the period in milliseconds.
            - Click **Apply timing changes** before injecting a fault.

            **Controls**
            - **Inject Fault** stops heartbeat delivery for the selected task.
            - **Clear Fault** removes an active fault without changing other tasks.
            - Editing timing values restarts all tasks with the new configuration.
            - The event log is persisted locally in `events.jsonl`.
            """
        )

    if "runtime" not in st.session_state:
        try:
            st.session_state.runtime = start_runtime()
        except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
            st.error(f"Unable to start simulator: {exc}")
            st.stop()

    runtime = st.session_state.runtime
    if notice := st.session_state.pop("dashboard_notice", None):
        st.success(notice)
    render_timing_controls(runtime)
    statuses = runtime["watchdog"].statuses()
    healthy = sum(status == "HEALTHY" for status in statuses.values())
    stalled = sum(status == "STALLED" for status in statuses.values())
    recovering = sum(status == "RECOVERING" for status in statuses.values())
    active_faults = len(runtime["fault_injector"].get_faults())
    st.header("System Overview")
    overview = st.columns(5)
    overview[0].metric("Tasks", len(runtime["tasks_config"]))
    overview[1].metric("Healthy", healthy)
    overview[2].metric("Stalled", stalled)
    overview[3].metric("Recovering", recovering)
    overview[4].metric("Active faults", active_faults)
    st.caption(
        f"{healthy}/{len(runtime['tasks_config'])} tasks healthy · "
        "updates every 250 ms"
    )

    render_status_grid(runtime)
    st.divider()
    render_controls(runtime)
    st.divider()
    selected = st.selectbox(
        "Task details",
        list(runtime["tasks_config"]),
        key="details-task",
    )
    selected_config = runtime["tasks_config"][selected]
    selected_status = statuses.get(selected, "INITIALIZING")
    selected_age = runtime["registry"].seconds_since_heartbeat(selected)
    st.write({
        "task": selected,
        "status": selected_status,
        "period_seconds": selected_config["period"],
        "timeout_ms": selected_config["timeout_ms"],
        "missed_heartbeat_threshold": selected_config["missed_heartbeat_threshold"],
        "heartbeat_age_seconds": selected_age,
        "recovery_count": runtime["recovery"].recovery_count(selected),
    })
    st.divider()
    render_event_log(runtime)

    time.sleep(0.25)
    st.rerun()


if __name__ == "__main__":
    main()
