"""OpenCode monitoring panel."""

from textual.widgets import Static
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from datetime import datetime

from ...monitors.opencode import OpenCodeMonitor


def _format_timestamp(timestamp: datetime) -> str:
    """Format timestamp for display."""
    return timestamp.strftime("%Y-%m-%d %H:%M") if timestamp else "Unknown"


class OpenCodePanel(Static):
    """Panel for displaying OpenCode metrics."""

    def __init__(self, **kwargs):
        """Initialize panel."""
        super().__init__(**kwargs)
        self.monitor = OpenCodeMonitor()
        self.current_view = "overview"
        self.current_time_range = "all"
        self.views = ["overview", "sessions", "projects", "models", "agents", "timeline"]

    def on_mount(self) -> None:
        """Set up periodic refresh."""
        self.set_interval(1.0, self.refresh_data)
        self.refresh_data()

    def refresh_data(self) -> None:
        """Refresh display with current metrics."""
        try:
            time_range = "today" if self.current_view == "overview" else self.current_time_range

            if self.current_view == "overview":
                required_aggregates = []
            elif self.current_view == "sessions":
                required_aggregates = ["by_session"]
            elif self.current_view == "projects":
                required_aggregates = ["by_project"]
            elif self.current_view == "models":
                required_aggregates = ["by_model"]
            elif self.current_view == "agents":
                required_aggregates = ["by_agent"]
            elif self.current_view == "timeline":
                required_aggregates = ["by_date"]
            else:
                required_aggregates = None

            metrics = self.monitor.get_metrics(
                time_range=time_range, required_aggregates=required_aggregates
            )
            rendered = self._render_metrics(metrics)
            self.update(rendered)
        except Exception as e:
            self.update(f"[red]Error: {e}[/red]")

    def next_view(self) -> None:
        """Switch to next subview."""
        current_idx = self.views.index(self.current_view)
        next_idx = (current_idx + 1) % len(self.views)
        self.current_view = self.views[next_idx]
        self.refresh_data()

    def prev_view(self) -> None:
        """Switch to previous subview."""
        current_idx = self.views.index(self.current_view)
        prev_idx = (current_idx - 1) % len(self.views)
        self.current_view = self.views[prev_idx]
        self.refresh_data()

    def set_time_range(self, time_range: str) -> None:
        """Set time range for non-overview views."""
        if time_range in ["today", "week", "month", "all"]:
            self.current_time_range = time_range
            self.refresh_data()

    def _render_metrics(self, metrics) -> Panel:
        """
        Render metrics as a Rich Panel.

        Args:
            metrics: OpenCodeMetrics object

        Returns:
            Rich Panel with formatted metrics
        """
        if metrics.is_active:
            status_icon = "🟢"
            status_text = "[bold green]Active[/bold green]"
        else:
            status_icon = "⚪"
            status_text = "[dim]Idle[/dim]"

        view_label = self.current_view.title()
        content_parts = []

        from rich.table import Table

        def build_table(title_text, items):
            table = Table(show_header=True, header_style="bold magenta", title=title_text)
            table.add_column("Name", overflow="fold")
            table.add_column("Tokens", justify="right")
            if not items:
                table.add_row("No data", "0")
                return table
            for name, usage in items[:10]:
                total_tokens = getattr(usage, "total_tokens", 0)
                table.add_row(str(name), f"{total_tokens:,}")
            return table

        if self.current_view == "overview":
            proc_table = Table.grid(padding=(0, 2), expand=True)
            proc_table.add_column(style="bold cyan", width=18)
            proc_table.add_column()

            if metrics.processes:
                proc_table.add_row("Processes:", f"{len(metrics.processes)} running")
                if metrics.processes:
                    uptime_hours = metrics.processes[0].uptime / 3600
                    proc_table.add_row("Uptime:", f"{uptime_hours:.1f} hours")
                proc_table.add_row("CPU:", f"{metrics.total_cpu:.1f}%")
                proc_table.add_row("Memory:", f"{metrics.total_memory_mb:.0f} MB")
            else:
                proc_table.add_row("Processes:", "[dim]No processes running[/dim]")

            session_table = Table.grid(padding=(0, 2), expand=True)
            session_table.add_column(style="bold cyan", width=18)
            session_table.add_column()

            session_table.add_row("Sessions:", f"{metrics.active_sessions} active")
            session_table.add_row("Total Today:", f"{metrics.total_sessions_today}")

            token_table = Table.grid(padding=(0, 2), expand=True)
            token_table.add_column(style="bold cyan", width=18)
            token_table.add_column()

            tokens = metrics.tokens_today
            if tokens.total_tokens > 0:
                token_table.add_row("Tokens (Today):", f"[bold]{tokens.total_tokens:,}[/bold]")
                if tokens.input_tokens > 0:
                    token_table.add_row("  Input:", f"{tokens.input_tokens:,}")
                if tokens.output_tokens > 0:
                    token_table.add_row("  Output:", f"{tokens.output_tokens:,}")
                if tokens.reasoning_tokens > 0:
                    token_table.add_row("  Reasoning:", f"{tokens.reasoning_tokens:,}")
                if tokens.cache_read_tokens > 0 or tokens.cache_write_tokens > 0:
                    token_table.add_row(
                        "  Cache:",
                        f"{tokens.cache_read_tokens:,} R / {tokens.cache_write_tokens:,} W",
                    )
            else:
                token_table.add_row("Tokens (Today):", "[dim]No usage today[/dim]")

            if metrics.stats_last_updated:
                token_table.add_row(
                    "Updated:", f"[dim]{_format_timestamp(metrics.stats_last_updated)}[/dim]"
                )

            content_parts.extend([proc_table, Text(""), session_table, Text(""), token_table])
        else:
            if self.current_view == "sessions":
                items = list(getattr(metrics, "by_session", {}).items())
                items = sorted(items, key=lambda item: item[1].total_tokens, reverse=True)
                table = build_table("Sessions", items)
            elif self.current_view == "projects":
                items = list(getattr(metrics, "by_project", {}).items())
                items = sorted(items, key=lambda item: item[1].total_tokens, reverse=True)
                table = build_table("Projects", items)
            elif self.current_view == "models":
                items = list(getattr(metrics, "by_model", {}).items())
                items = sorted(items, key=lambda item: item[1].total_tokens, reverse=True)
                table = build_table("Models", items)
            elif self.current_view == "agents":
                items = list(getattr(metrics, "by_agent", {}).items())
                items = sorted(items, key=lambda item: item[1].total_tokens, reverse=True)
                table = build_table("Agents", items)
            else:
                items = list(getattr(metrics, "by_date", {}).items())
                items = sorted(items, key=lambda item: item[0], reverse=True)
                table = build_table("Timeline", items)

            content_parts.append(table)

        hint_text = "[dim]k/l: switch view[/dim]"
        if self.current_view != "overview":
            time_label = self.current_time_range.title()
            hint_text += f" | [dim]Time: {time_label} (t/w/m/a)[/dim]"
        content_parts.append(Text(hint_text))
        content = Group(*content_parts)

        title = f"[bold]🔮 OPENCODE[/bold] {status_icon} {status_text} · {view_label}"

        return Panel(
            content,
            title=title,
            border_style="magenta" if metrics.is_active else "dim",
            padding=(1, 2),
        )
