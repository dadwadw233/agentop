"""OpenAI Codex specific monitoring."""

from datetime import datetime
from typing import Optional

from ..core.constants import AgentType
from ..core.models import CodexMetrics, TokenUsage
from ..parsers.codex_rate_limits import CodexRateLimitClient
from .process import ProcessMonitor


class CodexMonitor:
    """Monitor OpenAI Codex processes and usage."""

    def __init__(
        self, stats_file: Optional[str] = None, logs_dir: Optional[str] = None
    ) -> None:
        """
        Initialize Codex monitor.

        Args:
            stats_file: Optional custom stats file path
            logs_dir: Optional custom logs directory path
        """
        self.process_monitor = ProcessMonitor()
        self.rate_limit_client = CodexRateLimitClient(cache_ttl_seconds=60)
        self.agent_type = AgentType.CODEX

    def get_metrics(self) -> CodexMetrics:
        """
        Get current metrics for Codex.

        Returns:
            CodexMetrics object with all current data
        """
        # Get process information
        processes = self.process_monitor.find_agent_processes(self.agent_type)
        is_active = len(processes) > 0

        # Codex CLI does not persist local usage statistics.
        today_usage = None
        month_usage = None
        rate_limits = self.rate_limit_client.get_rate_limits()

        tokens_today = today_usage["tokens"] if today_usage else TokenUsage()
        tokens_this_month = month_usage["tokens"] if month_usage else TokenUsage()
        cost_today = today_usage["cost"] if today_usage else None
        cost_this_month = month_usage["cost"] if month_usage else None
        total_sessions_today = today_usage["total_sessions"] if today_usage else 0

        usage_source = None

        rate_limits_source = None
        rate_limits_error = None
        if rate_limits:
            rate_limits_source = "api"
        else:
            rate_limits_error = self.rate_limit_client.last_error

        # Determine active sessions based on running processes
        active_sessions = len(processes) if is_active else 0

        return CodexMetrics(
            agent_type=str(self.agent_type.value),
            processes=processes,
            is_active=is_active,
            last_active=datetime.now() if is_active else None,
            active_sessions=active_sessions,
            total_sessions_today=total_sessions_today,
            tokens_today=tokens_today,
            tokens_this_month=tokens_this_month,
            cost_today=cost_today,
            cost_this_month=cost_this_month,
            usage_source=usage_source,
            rate_limits=rate_limits,
            rate_limits_source=rate_limits_source,
            rate_limits_error=rate_limits_error,
        )

    def get_process_summary(self) -> str:
        """
        Get a human-readable summary of processes.

        Returns:
            Summary string
        """
        processes = self.process_monitor.find_agent_processes(self.agent_type)
        if not processes:
            return "No Codex processes running"

        count = len(processes)
        total_cpu = sum(p.cpu_percent for p in processes)
        total_mem = sum(p.memory_mb for p in processes)

        return f"{count} process{'es' if count > 1 else ''} - {total_cpu:.1f}% CPU, {total_mem:.0f} MB"
