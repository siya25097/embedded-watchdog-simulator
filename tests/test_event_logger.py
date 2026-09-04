import logging

from src.event_logger import EventLogger


def test_event_logger_keeps_chronological_thread_safe_history():
    logger = EventLogger(logging.getLogger("test-event-logger"))
    logger.log("FAULT_INJECTED", "task-a", {"fault": "hang"}, timestamp=2.0)
    logger.log("STALL_DETECTED", "task-a", timestamp=3.0)

    assert [event["event_type"] for event in logger.chronological()] == [
        "FAULT_INJECTED",
        "STALL_DETECTED",
    ]
    assert logger.events()[0]["details"] == {"fault": "hang"}
