"""Tests for OpenCode stats parser."""

import json
from pathlib import Path

from agentop.parsers.opencode_stats import OpenCodeStatsParser


def test_parse_message_extracts_tokens(tmp_path: Path):
    """Test that parse_message extracts token usage from message JSON."""
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
        "tokens": {
            "input": 10,
            "output": 5,
            "reasoning": 2,
            "cache": {"read": 3, "write": 4},
        },
    }
    message_file = message_dir / "msg.json"
    message_file.write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    message = parser.parse_message(message_file)

    assert message is not None
    assert message.tokens.total_tokens == 24


def test_parse_session_extracts_tokens(tmp_path: Path):
    """Test that parse_session extracts token usage from session JSON."""
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True)
    data = {
        "id": "ses_test",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": 1000, "completed": 3000},
        "tokens": {
            "input": 20,
            "output": 10,
            "reasoning": 5,
            "cache": {"read": 2, "write": 3},
        },
        "messageCount": 5,
    }
    session_file = session_dir / "ses_test.json"
    session_file.write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    session = parser.parse_session(session_file)

    assert session is not None
    assert session.tokens.total_tokens == 40
    assert session.message_count == 5


def test_get_all_messages(tmp_path: Path):
    """Test that get_all_messages finds and parses all message files."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    for i in range(3):
        data = {
            "id": f"msg_{i}",
            "sessionID": "ses_test",
            "role": "assistant",
            "modelID": "glm-4.7",
            "providerID": "zai-coding-plan",
            "agent": "Sisyphus",
            "path": {"root": "/tmp"},
            "time": {"created": 1000 + i, "completed": 2000 + i},
            "tokens": {
                "input": 10 + i,
                "output": 5 + i,
                "reasoning": 0,
                "cache": {"read": 0, "write": 0},
            },
        }
        message_file = message_dir / f"msg_{i}.json"
        message_file.write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()

    assert len(messages) == 3
    assert sum(m.tokens.total_tokens for m in messages) == 51


def test_get_all_messages_handles_millisecond_timestamps(tmp_path: Path):
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    from datetime import datetime

    now_ms = int(datetime.now().timestamp() * 1000)
    data = {
        "id": "msg_ms",
        "sessionID": "ses_test",
        "role": "assistant",
        "modelID": "glm-4.7",
        "providerID": "zai-coding-plan",
        "agent": "Sisyphus",
        "path": {"root": "/tmp"},
        "time": {"created": now_ms, "completed": now_ms + 1000},
        "tokens": {
            "input": 10,
            "output": 5,
            "reasoning": 0,
            "cache": {"read": 0, "write": 0},
        },
    }
    message_file = message_dir / "msg_ms.json"
    message_file.write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages(time_range="today")

    assert len(messages) == 1


def test_get_all_sessions(tmp_path: Path):
    """Test that get_all_sessions finds and parses all session files."""
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True)

    for i in range(2):
        data = {
            "id": f"ses_{i}",
            "modelID": "glm-4.7",
            "providerID": "zai-coding-plan",
            "agent": "Sisyphus",
            "path": {"root": "/tmp"},
            "time": {"created": 1000 + i, "completed": 3000 + i},
            "tokens": {
                "input": 20 + i,
                "output": 10 + i,
                "reasoning": 0,
                "cache": {"read": 0, "write": 0},
            },
            "messageCount": 5 + i,
        }
        session_file = session_dir / f"ses_{i}.json"
        session_file.write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    sessions = parser.get_all_sessions()

    assert len(sessions) == 2
    assert sum(s.tokens.total_tokens for s in sessions) == 62


def test_aggregate_by_agent(tmp_path: Path):
    """Test that aggregate_by_agent groups token usage by agent."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    for i, agent in enumerate(["Sisyphus", "Orchestrator", "Sisyphus"]):
        data = {
            "id": f"msg_{i}",
            "sessionID": "ses_test",
            "role": "assistant",
            "modelID": "glm-4.7",
            "providerID": "zai-coding-plan",
            "agent": agent,
            "path": {"root": "/tmp"},
            "time": {"created": 1000 + i, "completed": 2000 + i},
            "tokens": {
                "input": 10,
                "output": 5,
                "reasoning": 0,
                "cache": {"read": 0, "write": 0},
            },
        }
        message_file = message_dir / f"msg_{i}.json"
        message_file.write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_agent(messages)

    assert "Sisyphus" in aggregates
    assert "Orchestrator" in aggregates
    assert aggregates["Sisyphus"].total_tokens == 30
    assert aggregates["Orchestrator"].total_tokens == 15


def test_aggregate_by_model(tmp_path: Path):
    """Test that aggregate_by_model groups token usage by model."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    for i, model in enumerate(["glm-4.7", "claude-sonnet-4", "glm-4.7"]):
        data = {
            "id": f"msg_{i}",
            "sessionID": "ses_test",
            "role": "assistant",
            "modelID": model,
            "providerID": "zai-coding-plan",
            "agent": "Sisyphus",
            "path": {"root": "/tmp"},
            "time": {"created": 1000 + i, "completed": 2000 + i},
            "tokens": {
                "input": 10,
                "output": 5,
                "reasoning": 0,
                "cache": {"read": 0, "write": 0},
            },
        }
        message_file = message_dir / f"msg_{i}.json"
        message_file.write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_model(messages)

    assert "glm-4.7" in aggregates
    assert "claude-sonnet-4" in aggregates
    assert aggregates["glm-4.7"].total_tokens == 30
    assert aggregates["claude-sonnet-4"].total_tokens == 15


def test_aggregate_by_project(tmp_path: Path):
    """Test that aggregate_by_project groups token usage by project path."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    for i, project in enumerate(["/tmp", "/home/project", "/tmp"]):
        data = {
            "id": f"msg_{i}",
            "sessionID": "ses_test",
            "role": "assistant",
            "modelID": "glm-4.7",
            "providerID": "zai-coding-plan",
            "agent": "Sisyphus",
            "path": {"root": project},
            "time": {"created": 1000 + i, "completed": 2000 + i},
            "tokens": {
                "input": 10,
                "output": 5,
                "reasoning": 0,
                "cache": {"read": 0, "write": 0},
            },
        }
        message_file = message_dir / f"msg_{i}.json"
        message_file.write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_project(messages)

    assert "/tmp" in aggregates
    assert "/home/project" in aggregates
    assert aggregates["/tmp"].total_tokens == 30
    assert aggregates["/home/project"].total_tokens == 15


def test_aggregate_by_date(tmp_path: Path):
    """Test that aggregate_by_date groups token usage by date."""
    message_dir = tmp_path / "message" / "ses_test"
    message_dir.mkdir(parents=True)

    from datetime import datetime, timedelta

    today = datetime.now()
    yesterday = today - timedelta(days=1)

    for i, timestamp in enumerate([yesterday.timestamp(), today.timestamp(), today.timestamp()]):
        data = {
            "id": f"msg_{i}",
            "sessionID": "ses_test",
            "role": "assistant",
            "modelID": "glm-4.7",
            "providerID": "zai-coding-plan",
            "agent": "Sisyphus",
            "path": {"root": "/tmp"},
            "time": {"created": int(timestamp), "completed": int(timestamp) + 1000},
            "tokens": {
                "input": 10,
                "output": 5,
                "reasoning": 0,
                "cache": {"read": 0, "write": 0},
            },
        }
        message_file = message_dir / f"msg_{i}.json"
        message_file.write_text(json.dumps(data))

    parser = OpenCodeStatsParser(storage_path=str(tmp_path))
    messages = parser.get_all_messages()
    aggregates = parser.aggregate_by_date(messages)

    assert yesterday.date().isoformat() in aggregates
    assert today.date().isoformat() in aggregates
    assert aggregates[yesterday.date().isoformat()].total_tokens == 15
    assert aggregates[today.date().isoformat()].total_tokens == 30
