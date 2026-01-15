"""Cursor specific monitoring."""

from datetime import datetime

from ..core.constants import AgentType
from ..core.models import CursorMetrics, CostEstimate
from ..parsers.cursor_dashboard_api import CursorDashboardClient
from .process import ProcessMonitor


class CursorMonitor:
    """Monitor Cursor processes and dashboard usage."""

    def __init__(self) -> None:
        self.process_monitor = ProcessMonitor()
        self.dashboard_client = CursorDashboardClient(cache_ttl_seconds=60)
        self.agent_type = AgentType.CURSOR

    def get_metrics(self) -> CursorMetrics:
        processes = self.process_monitor.find_agent_processes(self.agent_type)
        is_active = len(processes) > 0
        active_sessions = len(processes) if is_active else 0

        snapshot = self.dashboard_client.get_usage_snapshot()
        usage_error = None
        usage_source = None

        if snapshot:
            usage_source = "dashboard"
        else:
            usage_error = self.dashboard_client.last_error

        return CursorMetrics(
            agent_type=str(self.agent_type.value),
            processes=processes,
            is_active=is_active,
            last_active=datetime.now() if is_active else None,
            active_sessions=active_sessions,
            billing_period_start=(
                datetime.fromtimestamp(snapshot.period_start_ms / 1000)
                if snapshot
                else None
            ),
            billing_period_end=(
                datetime.fromtimestamp(snapshot.period_end_ms / 1000)
                if snapshot
                else None
            ),
            total_input_tokens=snapshot.total_input_tokens if snapshot else 0,
            total_output_tokens=snapshot.total_output_tokens if snapshot else 0,
            total_cache_write_tokens=snapshot.total_cache_write_tokens if snapshot else 0,
            total_cache_read_tokens=snapshot.total_cache_read_tokens if snapshot else 0,
            total_cost=CostEstimate((snapshot.total_cost_cents / 100.0) if snapshot else 0.0),
            aggregations=snapshot.aggregations if snapshot else [],
            usage_source=usage_source,
            usage_error=usage_error,
            stats_last_updated=snapshot.captured_at if snapshot else None,
        )
