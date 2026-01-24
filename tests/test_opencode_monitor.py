"""Tests for OpenCode monitor."""

from agentop.monitors.opencode import OpenCodeMonitor
from agentop.core.models import OpenCodeTokenUsage


class FakeParser:
    """Fake parser for testing."""

    def get_all_messages(self, time_range="today"):
        return []

    def get_all_sessions(self):
        return []

    def aggregate_by_session(self, messages):
        return {}

    def aggregate_by_project(self, messages):
        return {}

    def aggregate_by_model(self, messages):
        return {}

    def aggregate_by_agent(self, messages):
        return {}

    def aggregate_by_date(self, messages):
        return {}


class FakeProcessMonitor:
    """Fake process monitor for testing."""

    def find_agent_processes(self, agent_type):
        return []


def test_monitor_returns_metrics():
    monitor = OpenCodeMonitor(
        process_monitor=FakeProcessMonitor(),
        stats_parser=FakeParser(),
    )
    metrics = monitor.get_metrics(time_range="today")
    assert metrics.total_tokens.total_tokens == 0
