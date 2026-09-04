from src.event_logger import EventLogger


def test_event_logger_persists_and_reloads_jsonl_history(tmp_path):
    path = tmp_path / "events.jsonl"
    logger = EventLogger(persistence_path=path)
    original = logger.log("FAULT_INJECTED", "task-a", {"fault_type": "hang"})

    reloaded = EventLogger(persistence_path=path)

    assert reloaded.events() == [original]
