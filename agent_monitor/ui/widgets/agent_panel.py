"""Agent monitoring panels."""

from textual.widgets import Static
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group
from datetime import datetime
from typing import Optional

from ...monitors.claude_code import ClaudeCodeMonitor
from ...monitors.codex import CodexMonitor


def _bar(value: float, total: float, width: int = 20) -> str:
    """
    Create a simple progress bar.

    Args:
        value: Current value
        total: Maximum value
        width: Bar width in characters

    Returns:
        Progress bar string
    """
    if total == 0:
        return ""

    percent = min(value / total, 1.0)  # Cap at 100%
    filled = int(percent * width)
    empty = width - filled

    # Choose color based on percentage
    if percent >= 0.9:
        bar = f"[red]{'█' * filled}[/red]"
    elif percent >= 0.7:
        bar = f"[yellow]{'█' * filled}[/yellow]"
    else:
        bar = f"[green]{'█' * filled}[/green]"

    bar += f"[dim]{'░' * empty}[/dim]"

    return bar


def _window_label(window_minutes: Optional[int]) -> str:
    if not window_minutes:
        return "5h"
    minutes = max(0, window_minutes)
    if minutes <= 24 * 60:
        hours = max(1, int(round(minutes / 60)))
        return f"{hours}h"
    if minutes <= 7 * 24 * 60:
        return "weekly"
    if minutes <= 30 * 24 * 60:
        return "monthly"
    return "annual"


def _format_reset(resets_at: Optional[datetime]) -> str:
    if not resets_at:
        return ""
    now = datetime.now()
    delta = resets_at - now
    seconds = int(delta.total_seconds())
    if seconds <= 0:
        return "resetting soon"
    minutes = seconds // 60
    if minutes < 60:
        return f"resets in {minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"resets in {hours}h"
    days = hours // 24
    return f"resets in {days}d"


def _format_timestamp(timestamp: Optional[datetime]) -> str:
    if not timestamp:
        return "Unknown"
    return timestamp.strftime("%Y-%m-%d %H:%M")


class ClaudeCodePanel(Static):
    """Panel for displaying Claude Code metrics."""

    def __init__(self, **kwargs):
        """Initialize panel."""
        super().__init__(**kwargs)
        self.monitor = ClaudeCodeMonitor()

    def on_mount(self) -> None:
        """Set up periodic refresh."""
        self.set_interval(1.0, self.refresh_data)
        self.refresh_data()

    def refresh_data(self) -> None:
        """Refresh the display with current metrics."""
        try:
            metrics = self.monitor.get_metrics()
            rendered = self._render_metrics(metrics)
            self.update(rendered)
        except Exception as e:
            self.update(f"[red]Error: {e}[/red]")

    def _render_metrics(self, metrics) -> Panel:
        """
        Render metrics as a Rich Panel.

        Args:
            metrics: ClaudeCodeMetrics object

        Returns:
            Rich Panel with formatted metrics
        """
        # Status indicator
        if metrics.is_active:
            status_icon = "🟢"
            status_text = "[bold green]Active[/bold green]"
        else:
            status_icon = "⚪"
            status_text = "[dim]Idle[/dim]"

        # Build content
        content_parts = []

        # === PROCESS INFO ===
        proc_table = Table.grid(padding=(0, 2), expand=True)
        proc_table.add_column(style="bold cyan", width=18)
        proc_table.add_column()

        if metrics.processes:
            # Show process details
            proc_info = []
            for i, proc in enumerate(metrics.processes[:3]):  # Show max 3 processes
                proc_info.append(f"PID {proc.pid}")
            if len(metrics.processes) > 3:
                proc_info.append(f"+{len(metrics.processes) - 3} more")

            proc_table.add_row("Processes:", f"{len(metrics.processes)} running")
            proc_table.add_row("", "[dim]" + ", ".join(proc_info) + "[/dim]")
            proc_table.add_row(
                "CPU:", f"{metrics.total_cpu:.1f}% {_bar(metrics.total_cpu, 100, 15)}"
            )
            proc_table.add_row("Memory:", f"{metrics.total_memory_mb:.0f} MB")

            # Uptime for first process
            if metrics.processes:
                uptime_hours = metrics.processes[0].uptime / 3600
                proc_table.add_row("Uptime:", f"{uptime_hours:.1f} hours")
        else:
            proc_table.add_row("Processes:", "[dim]No processes running[/dim]")

        content_parts.append(proc_table)

        # === SESSION INFO ===
        session_table = Table.grid(padding=(0, 2), expand=True)
        session_table.add_column(style="bold cyan", width=18)
        session_table.add_column()

        if metrics.active_sessions > 0:
            session_table.add_row(
                "Sessions:",
                f"[green]{metrics.active_sessions} active[/green]",
            )
        else:
            session_table.add_row("Sessions:", "0 active")

        content_parts.append(Text(""))  # Spacer
        content_parts.append(session_table)

        # === TOKEN USAGE ===
        token_table = Table.grid(padding=(0, 2), expand=True)
        token_table.add_column(style="bold cyan", width=18)
        token_table.add_column()

        # This Month
        month_tokens = metrics.tokens_this_month
        if month_tokens.total_tokens > 0:
            token_table.add_row(
                "Tokens (Month):",
                f"[bold]{month_tokens.total_tokens:,}[/bold] total",
            )

            # Input/Output breakdown
            if month_tokens.input_tokens > 0:
                input_pct = (month_tokens.input_tokens / month_tokens.total_tokens) * 100
                token_table.add_row(
                    "  Input:",
                    f"{month_tokens.input_tokens:,} {_bar(input_pct, 100, 15)} {input_pct:.0f}%",
                )

            if month_tokens.output_tokens > 0:
                output_pct = (month_tokens.output_tokens / month_tokens.total_tokens) * 100
                token_table.add_row(
                    "  Output:",
                    f"{month_tokens.output_tokens:,} {_bar(output_pct, 100, 15)} {output_pct:.0f}%",
                )
        else:
            token_table.add_row("Tokens (Month):", "[dim]No usage this month[/dim]")

        # Today
        today_tokens = metrics.tokens_today
        if today_tokens.total_tokens > 0:
            token_table.add_row("Tokens (Today):", f"{today_tokens.total_tokens:,}")
        else:
            token_table.add_row(
                "Tokens (Today):", "[dim]0 (stats may not be updated yet)[/dim]"
            )

        token_table.add_row(
            "Stats updated:",
            f"[dim]{_format_timestamp(metrics.stats_last_updated)}[/dim]",
        )

        content_parts.append(Text(""))  # Spacer
        content_parts.append(token_table)

        # === COST ===
        cost_table = Table.grid(padding=(0, 2), expand=True)
        cost_table.add_column(style="bold cyan", width=18)
        cost_table.add_column()

        cost_table.add_row(
            "Cost (Today):", f"[bold green]${metrics.cost_today.amount:.2f}[/bold green]"
        )
        cost_table.add_row(
            "Cost (Month):",
            f"[bold yellow]${metrics.cost_this_month.amount:.2f}[/bold yellow]",
        )

        content_parts.append(Text(""))  # Spacer
        content_parts.append(cost_table)

        # === QUOTA ===
        quota_table = Table.grid(padding=(0, 2), expand=True)
        quota_table.add_column(style="bold cyan", width=18)
        quota_table.add_column()

        rate_limits = metrics.rate_limits
        if rate_limits and (rate_limits.primary or rate_limits.secondary):
            for window in [rate_limits.primary, rate_limits.secondary]:
                if not window:
                    continue
                label = _window_label(window.window_minutes)
                percent_left = window.remaining_percent
                bar = _bar(percent_left, 100, 15)
                reset = _format_reset(window.resets_at)
                percent_label = f"{percent_left:>3.0f}% left"
                value = f"{percent_label} {bar}"
                if reset:
                    value += f" • {reset}"
                quota_table.add_row(f"{label} limit:", value)
        else:
            if metrics.rate_limits_error:
                quota_table.add_row("Quota:", "[dim]Unavailable[/dim]")
                reason = metrics.rate_limits_error
                if len(reason) > 64:
                    reason = reason[:61] + "..."
                quota_table.add_row("Reason:", f"[dim]{reason}[/dim]")
            else:
                quota_table.add_row("Quota:", "[dim]Unavailable[/dim]")

        content_parts.append(Text(""))  # Spacer
        content_parts.append(quota_table)

        # Combine all parts
        content = Group(*content_parts)

        # Create panel with title
        title = f"[bold]🤖 CLAUDE CODE[/bold] {status_icon} {status_text}"

        return Panel(
            content,
            title=title,
            border_style="blue" if metrics.is_active else "dim",
            padding=(1, 2),
        )


class CodexPanel(Static):
    """Panel for displaying OpenAI Codex metrics."""

    def __init__(self, **kwargs):
        """Initialize panel."""
        super().__init__(**kwargs)
        self.monitor = CodexMonitor()

    def on_mount(self) -> None:
        """Set up periodic refresh."""
        self.set_interval(1.0, self.refresh_data)
        self.refresh_data()

    def refresh_data(self) -> None:
        """Refresh the display with current metrics."""
        try:
            metrics = self.monitor.get_metrics()
            rendered = self._render_metrics(metrics)
            self.update(rendered)
        except Exception as e:
            self.update(f"[red]Error: {e}[/red]")

    def _render_metrics(self, metrics) -> Panel:
        """
        Render metrics as a Rich Panel.

        Args:
            metrics: CodexMetrics object

        Returns:
            Rich Panel with formatted metrics
        """
        # Status indicator
        if metrics.is_active:
            status_icon = "🟢"
            status_text = "[bold green]Active[/bold green]"
        else:
            status_icon = "⚪"
            status_text = "[dim]Idle[/dim]"

        # Build content
        content_parts = []

        # === PROCESS INFO ===
        proc_table = Table.grid(padding=(0, 2), expand=True)
        proc_table.add_column(style="bold cyan", width=18)
        proc_table.add_column()

        if metrics.processes:
            # Show process details
            proc_info = []
            for proc in metrics.processes[:3]:  # Show max 3 processes
                proc_info.append(f"PID {proc.pid}")
            if len(metrics.processes) > 3:
                proc_info.append(f"+{len(metrics.processes) - 3} more")

            proc_table.add_row("Processes:", f"{len(metrics.processes)} running")
            proc_table.add_row("", "[dim]" + ", ".join(proc_info) + "[/dim]")
            proc_table.add_row(
                "CPU:", f"{metrics.total_cpu:.1f}% {_bar(metrics.total_cpu, 100, 15)}"
            )
            proc_table.add_row("Memory:", f"{metrics.total_memory_mb:.0f} MB")

            # Uptime for first process
            if metrics.processes:
                uptime_hours = metrics.processes[0].uptime / 3600
                proc_table.add_row("Uptime:", f"{uptime_hours:.1f} hours")
        else:
            proc_table.add_row("Processes:", "[dim]No processes running[/dim]")

        content_parts.append(proc_table)

        # === SESSION INFO ===
        session_table = Table.grid(padding=(0, 2), expand=True)
        session_table.add_column(style="bold cyan", width=18)
        session_table.add_column()

        if metrics.active_sessions > 0:
            session_table.add_row(
                "Sessions:",
                f"[green]{metrics.active_sessions} active[/green]",
            )
        else:
            session_table.add_row("Sessions:", "0 active")

        content_parts.append(Text(""))  # Spacer
        content_parts.append(session_table)

        # === RATE LIMITS ===
        rate_table = Table.grid(padding=(0, 2), expand=True)
        rate_table.add_column(style="bold cyan", width=18)
        rate_table.add_column()

        rate_limits = metrics.rate_limits
        if rate_limits and (rate_limits.primary or rate_limits.secondary):
            for window in [rate_limits.primary, rate_limits.secondary]:
                if not window:
                    continue
                label = _window_label(window.window_minutes)
                percent_left = window.remaining_percent
                bar = _bar(percent_left, 100, 15)
                reset = _format_reset(window.resets_at)
                percent_label = f"{percent_left:>3.0f}% left"
                value = f"{percent_label} {bar}"
                if reset:
                    value += f" • {reset}"
                rate_table.add_row(f"{label} limit:", value)
        else:
            if metrics.rate_limits_error:
                rate_table.add_row("Quota:", "[dim]Unavailable[/dim]")
                reason = metrics.rate_limits_error
                if len(reason) > 64:
                    reason = reason[:61] + "..."
                rate_table.add_row("Reason:", f"[dim]{reason}[/dim]")
            else:
                rate_table.add_row("Quota:", "[dim]Unavailable[/dim]")

        content_parts.append(Text(""))  # Spacer
        content_parts.append(rate_table)

        # Combine all parts
        content = Group(*content_parts)

        # Create panel with title
        title = f"[bold]🤖 OPENAI CODEX[/bold] {status_icon} {status_text}"

        return Panel(
            content,
            title=title,
            border_style="cyan" if metrics.is_active else "dim",
            padding=(1, 2),
        )
