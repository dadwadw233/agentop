"""Tests for OpenCode aggregation functions."""

from agentop.parsers.opencode_stats import OpenCodeStatsParser
from pathlib import Path
import json


def test_aggregate_by_agent(tmp_path: Path):
    """Aggregate token usage by agent correctly computes totals."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg.json").write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_agent(messages)

    assert "Sisyphus" in aggregates
    assert aggregates["Sisyphus"].total_tokens == 15


def test_aggregate_by_agent_multiple_messages(tmp_path: Path):
    """Aggregate token usage by agent correctly sums across multiple messages."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data1 = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg1.json").write_text(json.dumps(data1))

    data2 = {
        "id": "msg_2",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 3000, "completed": 4000},
        "tokens": {"input": 20, "output": 10, "reasoning": 5, "cache": {"read": 2, "write": 1}},
    }
    (message_dir / "msg2.json").write_text(json.dumps(data2))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_agent(messages)

    assert "Sisyphus" in aggregates
    assert aggregates["Sisyphus"].input_tokens == 30
    assert aggregates["Sisyphus"].output_tokens == 15
    assert aggregates["Sisyphus"].reasoning_tokens == 5
    assert aggregates["Sisyphus"].cache_read_tokens == 2
    assert aggregates["Sisyphus"].cache_write_tokens == 1
    assert aggregates["Sisyphus"].total_tokens == 53


def test_aggregate_by_agent_unknown_agent(tmp_path: Path):
    """Aggregate token usage by agent correctly handles missing agent field."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "path": {"root": "/tmp"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg.json").write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_agent(messages)

    assert "unknown" in aggregates
    assert aggregates["unknown"].total_tokens == 15


def test_aggregate_by_agent_multiple_agents(tmp_path: Path):
    """Aggregate token usage by agent correctly separates different agents."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data1 = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg1.json").write_text(json.dumps(data1))

    data2 = {
        "id": "msg_2",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Orion",
        "path": {"root": "/tmp"},
        "time": {"created": 3000, "completed": 4000},
        "tokens": {"input": 20, "output": 10, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg2.json").write_text(json.dumps(data2))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_agent(messages)

    assert "Sisyphus" in aggregates
    assert "Orion" in aggregates
    assert aggregates["Sisyphus"].total_tokens == 15
    assert aggregates["Orion"].total_tokens == 30


def test_aggregate_by_session(tmp_path: Path):
    """Aggregate token usage by session correctly computes totals."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg.json").write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_session(messages)

    assert "ses_test" in aggregates
    assert aggregates["ses_test"].total_tokens == 15


def test_aggregate_by_session_multiple_messages(tmp_path: Path):
    """Aggregate token usage by session correctly sums across multiple messages."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data1 = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg1.json").write_text(json.dumps(data1))

    data2 = {
        "id": "msg_2",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 3000, "completed": 4000},
        "tokens": {"input": 20, "output": 10, "reasoning": 5, "cache": {"read": 2, "write": 1}},
    }
    (message_dir / "msg2.json").write_text(json.dumps(data2))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_session(messages)

    assert "ses_test" in aggregates
    assert aggregates["ses_test"].input_tokens == 30
    assert aggregates["ses_test"].output_tokens == 15
    assert aggregates["ses_test"].reasoning_tokens == 5
    assert aggregates["ses_test"].cache_read_tokens == 2
    assert aggregates["ses_test"].cache_write_tokens == 1
    assert aggregates["ses_test"].total_tokens == 53


def test_aggregate_by_session_multiple_sessions(tmp_path: Path):
    """Aggregate token usage by session correctly separates different sessions."""
    message_dir1 = tmp_path / "message" / "ses_test1"
    message_dir1.mkdir(parents=True)
    message_dir2 = tmp_path / "message" / "ses_test2"
    message_dir2.mkdir(parents=True)

    data1 = {
        "id": "msg_1",
        "sessionID": "ses_test1",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir1 / "msg1.json").write_text(json.dumps(data1))

    data2 = {
        "id": "msg_2",
        "sessionID": "ses_test2",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 3000, "completed": 4000},
        "tokens": {"input": 20, "output": 10, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir2 / "msg2.json").write_text(json.dumps(data2))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_session(messages)

    assert "ses_test1" in aggregates
    assert "ses_test2" in aggregates
    assert aggregates["ses_test1"].total_tokens == 15
    assert aggregates["ses_test2"].total_tokens == 30


def test_aggregate_by_project(tmp_path: Path):
    """Aggregate token usage by project correctly computes totals."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/home/user/project1"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg.json").write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_project(messages)

    assert "/home/user/project1" in aggregates
    assert aggregates["/home/user/project1"].total_tokens == 15


def test_aggregate_by_project_unknown_project(tmp_path: Path):
    """Aggregate token usage by project correctly handles missing project field."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg.json").write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_project(messages)

    assert "unknown" in aggregates
    assert aggregates["unknown"].total_tokens == 15


def test_aggregate_by_project_multiple_projects(tmp_path: Path):
    """Aggregate token usage by project correctly separates different projects."""
    message_dir1 = tmp_path / "message" / "ses_test1"
    message_dir1.mkdir(parents=True)
    message_dir2 = tmp_path / "message" / "ses_test2"
    message_dir2.mkdir(parents=True)

    data1 = {
        "id": "msg_1",
        "sessionID": "ses_test1",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/home/user/project1"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir1 / "msg1.json").write_text(json.dumps(data1))

    data2 = {
        "id": "msg_2",
        "sessionID": "ses_test2",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/home/user/project2"},
        "time": {"created": 3000, "completed": 4000},
        "tokens": {"input": 20, "output": 10, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir2 / "msg2.json").write_text(json.dumps(data2))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_project(messages)

    assert "/home/user/project1" in aggregates
    assert "/home/user/project2" in aggregates
    assert aggregates["/home/user/project1"].total_tokens == 15
    assert aggregates["/home/user/project2"].total_tokens == 30


def test_aggregate_by_model(tmp_path: Path):
    """Aggregate token usage by model correctly computes totals."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg.json").write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_model(messages)

    assert "glm-4.7" in aggregates
    assert aggregates["glm-4.7"].total_tokens == 15


def test_aggregate_by_model_unknown_model(tmp_path: Path):
    """Aggregate token usage by model correctly handles missing model field."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg.json").write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_model(messages)

    assert "unknown" in aggregates
    assert aggregates["unknown"].total_tokens == 15


def test_aggregate_by_model_multiple_models(tmp_path: Path):
    """Aggregate token usage by model correctly separates different models."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data1 = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1000, "completed": 2000},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg1.json").write_text(json.dumps(data1))

    data2 = {
        "id": "msg_2",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "gpt-4",
        "providerID": "openai",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 3000, "completed": 4000},
        "tokens": {"input": 20, "output": 10, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg2.json").write_text(json.dumps(data2))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_model(messages)

    assert "glm-4.7" in aggregates
    assert "gpt-4" in aggregates
    assert aggregates["glm-4.7"].total_tokens == 15
    assert aggregates["gpt-4"].total_tokens == 30


def test_aggregate_by_date(tmp_path: Path):
    """Aggregate token usage by date correctly computes totals."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1737350400, "completed": 1737350500},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg.json").write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_date(messages)

    assert "2025-01-20" in aggregates
    assert aggregates["2025-01-20"].total_tokens == 15


def test_aggregate_by_date_multiple_dates(tmp_path: Path):
    """Aggregate token usage by date correctly separates different dates."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    data1 = {
        "id": "msg_1",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1737350400, "completed": 1737350500},
        "tokens": {"input": 10, "output": 5, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg1.json").write_text(json.dumps(data1))

    data2 = {
        "id": "msg_2",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1737436800, "completed": 1737436900},
        "tokens": {"input": 20, "output": 10, "reasoning": 0, "cache": {"read": 0, "write": 0}},
    }
    (message_dir / "msg2.json").write_text(json.dumps(data2))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_date(messages)

    assert "2025-01-20" in aggregates
    assert "2025-01-21" in aggregates
    assert aggregates["2025-01-20"].total_tokens == 15
    assert aggregates["2025-01-21"].total_tokens == 30
