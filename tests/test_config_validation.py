import pytest
from scripts.run_tasks import load_tasks


def write_config(tmp_path, content):
    config_file = tmp_path / "tasks.yaml"
    config_file.write_text(content)
    return str(config_file)


def test_missing_task_id(tmp_path):
    config = """
tasks:
  - period: 1
    timeout_ms: 3000
    missed_heartbeat_threshold: 2
"""

    path = write_config(tmp_path, config)

    with pytest.raises(ValueError, match="missing 'id'"):
        load_tasks(path)


def test_non_positive_period(tmp_path):
    config = """
tasks:
  - id: task-A
    period: 0
    timeout_ms: 3000
    missed_heartbeat_threshold: 2
"""

    path = write_config(tmp_path, config)

    with pytest.raises(ValueError, match="invalid 'period'"):
        load_tasks(path)


def test_timeout_must_be_greater_than_period(tmp_path):
    config = """
tasks:
  - id: task-A
    period: 2
    timeout_ms: 2000
    missed_heartbeat_threshold: 2
"""

    path = write_config(tmp_path, config)

    with pytest.raises(ValueError, match="timeout_ms"):
        load_tasks(path)


def test_invalid_missed_heartbeat_threshold(tmp_path):
    config = """
tasks:
  - id: task-A
    period: 1
    timeout_ms: 3000
    missed_heartbeat_threshold: -1
"""

    path = write_config(tmp_path, config)

    with pytest.raises(ValueError, match="missed_heartbeat_threshold"):
        load_tasks(path)