"""OpenCode specific monitoring."""

from datetime import datetime
from typing import Optional, List
from ..core.models import OpenCodeMetrics, OpenCodeTokenUsage
from ..core.constants import AgentType
from ..parsers.opencode_stats import OpenCodeStatsParser
from .process import ProcessMonitor


class OpenCodeMonitor:
    """Monitor OpenCode processes and usage."""

    def __init__(
        self,
        storage_path: Optional[str] = None,
        process_monitor: Optional[ProcessMonitor] = None,
        stats_parser: Optional[OpenCodeStatsParser] = None,
    ):
        """
        Initialize OpenCode monitor.

        Args:
            storage_path: Optional custom storage path
            process_monitor: Optional process monitor (for testing)
            stats_parser: Optional stats parser (for testing)
        """
        self.process_monitor = process_monitor or ProcessMonitor()
        self.stats_parser = stats_parser or OpenCodeStatsParser(storage_path)
        self.agent_type = AgentType.OPENCODE

    def get_metrics(
        self, time_range: str = "today", required_aggregates: Optional[List[str]] = None
    ) -> OpenCodeMetrics:
        """
        Get current metrics for OpenCode.

        Args:
            time_range: Time range for token aggregation (today, week, month, all)
            required_aggregates: Optional list of aggregates to compute. If None, compute all.

        Returns:
            OpenCodeMetrics object with all current data
        """
        processes = self.process_monitor.find_agent_processes(self.agent_type)
        is_active = len(processes) > 0

        messages = self.stats_parser.get_all_messages(time_range)
        sessions = self.stats_parser.get_all_sessions()

        total_tokens = OpenCodeTokenUsage()
        for msg in messages:
            total_tokens.input_tokens += msg.tokens.input_tokens
            total_tokens.output_tokens += msg.tokens.output_tokens
            total_tokens.reasoning_tokens += msg.tokens.reasoning_tokens
            total_tokens.cache_read_tokens += msg.tokens.cache_read_tokens
            total_tokens.cache_write_tokens += msg.tokens.cache_write_tokens

        if required_aggregates is None:
            required_aggregates = ["by_session", "by_agent", "by_model", "by_project", "by_date"]

        by_session = {}
        by_agent = {}
        by_model = {}
        by_project = {}
        by_date = {}

        if "by_session" in required_aggregates:
            by_session = self.stats_parser.aggregate_by_session(messages)
        if "by_agent" in required_aggregates:
            by_agent = self.stats_parser.aggregate_by_agent(messages)
        if "by_model" in required_aggregates:
            by_model = self.stats_parser.aggregate_by_model(messages)
        if "by_project" in required_aggregates:
            by_project = self.stats_parser.aggregate_by_project(messages)
        if "by_date" in required_aggregates:
            by_date = self.stats_parser.aggregate_by_date(messages)

        metrics = OpenCodeMetrics(
            agent_type=str(self.agent_type.value),
            processes=processes,
            is_active=is_active,
            last_active=datetime.now() if is_active else None,
            total_tokens=total_tokens,
            tokens_today=total_tokens,
            active_sessions=len(processes) if is_active else 0,
            total_sessions_today=len(sessions),
            by_session=by_session,
            by_agent=by_agent,
            by_model=by_model,
            by_provider={},
            by_project=by_project,
            by_date=by_date,
            stats_last_updated=None,
        )

        return metrics
