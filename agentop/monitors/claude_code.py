"""Claude Code specific monitoring."""

from datetime import datetime
from typing import Optional
from ..core.models import ClaudeCodeMetrics, CostEstimate, TokenUsage
from ..core.constants import AgentType
from ..parsers.stats_parser import ClaudeStatsParser
from ..parsers.claude_rate_limits import ClaudeRateLimitClient
from .process import ProcessMonitor


class ClaudeCodeMonitor:
    """Monitor Claude Code processes and usage."""

    def __init__(self, stats_file: Optional[str] = None):
        """
        Initialize Claude Code monitor.

        Args:
            stats_file: Optional custom stats file path
        """
        self.process_monitor = ProcessMonitor()
        self.stats_parser = ClaudeStatsParser(stats_file)
        self.rate_limit_client = ClaudeRateLimitClient(cache_ttl_seconds=60)
        self.agent_type = AgentType.CLAUDE_CODE

    def get_metrics(self) -> ClaudeCodeMetrics:
        """
        Get current metrics for Claude Code.

        Returns:
            ClaudeCodeMetrics object with all current data
        """
        # Get process information
        processes = self.process_monitor.find_agent_processes(self.agent_type)
        is_active = len(processes) > 0

        # Get usage data from stats
        today_usage = self.stats_parser.get_today_usage()
        month_usage = self.stats_parser.get_month_usage()
        stats_last_updated = self.stats_parser.get_stats_last_updated()

        # Determine active sessions based on running processes
        # If Claude Code is running, assume at least 1 active session
        active_sessions = len(processes) if is_active else 0

        rate_limits = self.rate_limit_client.get_rate_limits()
        rate_limits_source = None
        rate_limits_error = None
        if rate_limits:
            rate_limits_source = "api"
        else:
            rate_limits_error = self.rate_limit_client.last_error

        # Build metrics object
        metrics = ClaudeCodeMetrics(
            agent_type=str(self.agent_type.value),
            processes=processes,
            is_active=is_active,
            last_active=datetime.now() if is_active else None,
            # Session info (use process-based detection for active sessions)
            active_sessions=active_sessions,
            total_sessions_today=today_usage["total_sessions"],
            # Token usage
            tokens_today=today_usage["tokens"],
            tokens_this_month=month_usage["tokens"],
            # Costs
            cost_today=CostEstimate(today_usage["cost"]),
            cost_this_month=CostEstimate(month_usage["cost"]),
            stats_last_updated=stats_last_updated,
            rate_limits=rate_limits,
            rate_limits_source=rate_limits_source,
            rate_limits_error=rate_limits_error,
        )

        return metrics

    def get_process_summary(self) -> str:
        """
        Get a human-readable summary of processes.

        Returns:
            Summary string
        """
        processes = self.process_monitor.find_agent_processes(self.agent_type)
        if not processes:
            return "No Claude Code processes running"

        count = len(processes)
        total_cpu = sum(p.cpu_percent for p in processes)
        total_mem = sum(p.memory_mb for p in processes)

        return f"{count} process{'es' if count > 1 else ''} - {total_cpu:.1f}% CPU, {total_mem:.0f} MB"
