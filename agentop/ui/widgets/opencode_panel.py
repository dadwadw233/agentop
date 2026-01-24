"""OpenCode monitoring panel."""

from textual.widgets import Static
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.table import Table
from datetime import datetime
import math

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
        self.views = ["overview", "projects", "models", "agents", "timeline"]

        # Pagination state
        self.page_index = 0
        self.page_size = 10  # Default fallback

    def on_mount(self) -> None:
        """Set up periodic refresh."""
        self.set_interval(1.0, self.refresh_data)
        self._update_page_size()
        self.refresh_data()

    def refresh_data(self) -> None:
        """Refresh display with current metrics."""
        self._update_page_size()
        try:
            time_range = "today" if self.current_view == "overview" else self.current_time_range

            required_aggregates = None
            if self.current_view == "overview":
                required_aggregates = []
            elif self.current_view == "projects":
                required_aggregates = ["by_project"]
            elif self.current_view == "models":
                required_aggregates = ["by_model"]
            elif self.current_view == "agents":
                required_aggregates = ["by_agent"]
            elif self.current_view == "timeline":
                required_aggregates = ["by_date"]

            metrics = self.monitor.get_metrics(
                time_range=time_range, required_aggregates=required_aggregates
            )
            rendered = self._render_metrics(metrics)
            self.update(rendered)
        except Exception as e:
            self.update(Panel(f"[red]Error: {e}[/red]", title="Error"))

    def next_view(self) -> None:
        """Switch to next subview."""
        current_idx = self.views.index(self.current_view)
        next_idx = (current_idx + 1) % len(self.views)
        self.current_view = self.views[next_idx]
        self.page_index = 0  # Reset pagination
        self.refresh_data()

    def prev_view(self) -> None:
        """Switch to previous subview."""
        current_idx = self.views.index(self.current_view)
        prev_idx = (current_idx - 1) % len(self.views)
        self.current_view = self.views[prev_idx]
        self.page_index = 0  # Reset pagination
        self.refresh_data()

    def set_time_range(self, time_range: str) -> None:
        """Set time range for non-overview views."""
        if time_range in ["today", "week", "month", "all"]:
            self.current_time_range = time_range
            self.refresh_data()

    def _update_page_size(self) -> None:
        """Compute a stable page size from screen height."""
        # Only relevant for list views
        if self.current_view == "overview":
            return

        try:
            app = self.app
        except Exception:
            return

        if not app:
            return

        height = getattr(getattr(app, "size", None), "height", 0) or 0
        if height <= 0:
            return

        # Estimate overhead: Title(1)+Border(2)+Padding(1)+Header(1)+Footer(2) = ~7-8
        # We leave some buffer
        overhead = 8

        available = max(4, height - overhead)
        self.page_size = available

    def _create_bar(self, value: float, total: float, width: int = 15) -> str:
        """Create a simple text-based progress bar."""
        if total == 0:
            return "░" * width

        percentage = min(1.0, max(0.0, value / total))
        filled = int(percentage * width)
        empty = width - filled

        # Color gradient based on usage intensity (heuristic)
        color = "cyan"
        if percentage > 0.8:
            color = "magenta"
        elif percentage > 0.5:
            color = "blue"

        bar = f"[{color}]{'█' * filled}[/{color}][dim]{'░' * empty}[/dim]"
        return bar

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
            border_style = "green"
        else:
            status_icon = "⚪"
            status_text = "[dim]Idle[/dim]"
            border_style = "dim"

        view_label = self.current_view.title()

        # Title construction
        title = f"[bold]🔮 OPENCODE[/bold] {status_icon} {status_text} · [bold cyan]{view_label}[/bold cyan]"

        content_parts = []

        if self.current_view == "overview":
            content_parts.append(self._render_overview(metrics))
        else:
            content_parts.append(self._render_subview(metrics))

        # Footer / Hints
        hint_parts = ["k/l: switch views (1-5)"]

        if self.current_view != "overview":
            time_label = self.current_time_range.title()
            hint_parts.append(f" | Time: {time_label} (t/w/m/a)")

        # Add update time if available
        if metrics.stats_last_updated:
            updated = _format_timestamp(metrics.stats_last_updated)
            hint_parts.append(f" | Updated: {updated}")

        content_parts.append(Text("\n" + " | ".join(hint_parts), justify="center"))

        content = Group(*content_parts)

        return Panel(
            content,
            title=title,
            border_style=border_style,
            padding=(0, 1),
        )

    def _render_overview(self, metrics) -> Group:
        """Render the overview dashboard."""

        # 1. Process Status Section
        proc_grid = Table.grid(padding=(0, 2), expand=True)
        proc_grid.add_column(style="bold blue", width=12)
        proc_grid.add_column()
        proc_grid.add_column(style="bold blue", width=12)
        proc_grid.add_column()

        if metrics.processes:
            p = metrics.processes[0]
            uptime_hours = p.uptime / 3600
            proc_count = len(metrics.processes)

            proc_grid.add_row("STATUS", "[green]Running[/green]", "PROCESSES", f"{proc_count}")
            proc_grid.add_row(
                "CPU", f"{metrics.total_cpu:.1f}%", "MEMORY", f"{metrics.total_memory_mb:.0f} MB"
            )
            proc_grid.add_row("UPTIME", f"{uptime_hours:.1f}h", "", "")
        else:
            proc_grid.add_row("STATUS", "[dim]Stopped[/dim]", "", "")

        # 2. Daily Stats Section
        stats_table = Table(
            show_header=True, header_style="bold magenta", expand=True, box=None, padding=(0, 1)
        )
        stats_table.add_column("Daily Activity")
        stats_table.add_column("Count", justify="right")

        stats_table.add_row("Sessions Active", str(metrics.active_sessions))
        stats_table.add_row("Sessions Total", str(metrics.total_sessions_today))

        # 3. Token Usage Section
        tokens = metrics.tokens_today
        token_grid = Table.grid(padding=(0, 2), expand=True)
        token_grid.add_column(style="dim", width=15)
        token_grid.add_column(justify="right")

        if tokens.total_tokens > 0:
            token_grid.add_row(
                "[bold]Total Tokens[/bold]", f"[bold cyan]{tokens.total_tokens:,}[/bold cyan]"
            )
            if tokens.input_tokens > 0:
                token_grid.add_row("Input", f"{tokens.input_tokens:,}")
            if tokens.output_tokens > 0:
                token_grid.add_row("Output", f"{tokens.output_tokens:,}")
            if tokens.reasoning_tokens > 0:
                token_grid.add_row("Reasoning", f"{tokens.reasoning_tokens:,}")
            if tokens.cache_read_tokens > 0 or tokens.cache_write_tokens > 0:
                token_grid.add_row(
                    "Cache (R/W)", f"{tokens.cache_read_tokens:,} / {tokens.cache_write_tokens:,}"
                )
        else:
            token_grid.add_row("Total Tokens", "[dim]0[/dim]")

        # Combine sections with visual separation
        return Group(
            Text(""),
            proc_grid,
            Text(""),
            Panel(
                stats_table,
                border_style="dim",
                title="[bold]Session Stats[/bold]",
                title_align="left",
            ),
            Panel(
                token_grid,
                border_style="dim",
                title="[bold]Token Usage (Today)[/bold]",
                title_align="left",
            ),
        )

    def _render_subview(self, metrics) -> Table:
        """Render lists for sessions, projects, etc."""

        # Determine data source
        items = []
        name_label = "Name"

        if self.current_view == "projects":
            data = getattr(metrics, "by_project", {})
            items = list(data.items())
            name_label = "Project Path"
        elif self.current_view == "models":
            data = getattr(metrics, "by_model", {})
            items = list(data.items())
            name_label = "Model Name"
        elif self.current_view == "agents":
            data = getattr(metrics, "by_agent", {})
            items = list(data.items())
            name_label = "Agent Type"
        elif self.current_view == "timeline":
            data = getattr(metrics, "by_date", {})
            items = list(data.items())
            name_label = "Date"

        # Sort items
        if self.current_view == "timeline":
            items = sorted(items, key=lambda item: item[0], reverse=True)
        else:
            items = sorted(items, key=lambda item: item[1].total_tokens, reverse=True)

        # Calculate max tokens for progress bars
        max_tokens = 0
        if items and self.current_view != "timeline":
            max_tokens = items[0][1].total_tokens
        elif items and self.current_view == "timeline":
            # For timeline, find max tokens among all dates
            max_tokens = max((item[1].total_tokens for item in items), default=0)

        # Pagination
        total_items = len(items)
        total_pages = max(1, math.ceil(total_items / self.page_size))
        self.page_index = min(self.page_index, total_pages - 1)
        start_idx = self.page_index * self.page_size
        end_idx = start_idx + self.page_size
        page_items = items[start_idx:end_idx]

        # Build Table
        table = Table(box=None, expand=True, padding=(0, 1))
        table.add_column(name_label, style="bold", ratio=2)

        # Add visual bar column
        table.add_column("Usage", justify="left", ratio=2)
        table.add_column("Tokens", justify="right", style="cyan", ratio=1)

        if not page_items:
            table.add_row("[dim]No data available[/dim]", "", "")
            return table

        for key, usage in page_items:
            # Handle key display (truncate if needed)
            display_key = str(key)
            if len(display_key) > 30:
                if "/" in display_key:
                    # Path-like truncation
                    parts = display_key.split("/")
                    if len(parts) > 2:
                        display_key = f".../{parts[-2]}/{parts[-1]}"
                    else:
                        display_key = "..." + display_key[-27:]
                else:
                    display_key = display_key[:27] + "..."

            total = getattr(usage, "total_tokens", 0)

            # For timeline, we also want bars
            bar = self._create_bar(total, max_tokens, width=15)

            table.add_row(display_key, bar, f"{total:,}")

        # Add pagination footer row if needed
        if total_pages > 1:
            table.add_row(f"\n[dim]Page {self.page_index + 1}/{total_pages}[/dim]", "", "")

        return table
